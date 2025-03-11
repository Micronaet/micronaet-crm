#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
# Developer: Nicola Riolini @thebrush (<https://it.linkedin.com/in/thebrush>)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################


import os
import sys
import logging
import openerp
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)


_logger = logging.getLogger(__name__)

axis_group = [
    ('year', 'Year'),
    ('period', 'Season'),
    ('agent', 'Agent'),
    ('family', 'Family'),
    ]


class CrmExcelExtractReportWizard(orm.TransientModel):
    """ Wizard for extract data from sale, invoice
    """
    _name = 'crm.excel.extract.report.wizard'
    _description = 'CRM Excel export'

    def get_season_period(self, date):
        """ Get season (period from 09 to 08
        """
        year = date[:4]
        month = date[5:7]
        if month >= '09':
            return '%s-%02d' % (
                year[-2:],
                int(year[-2:]) + 1,
                )
        else:
            return '%02d-%s' % (
                int(year[-2:]) - 1,
                year[-2:],
                )

    def coordinate_data(self, olap_data, mode, line):
        """ Extract coordinate data from line
        """
        group = olap_data[mode]
        if group == 'year':
            value = line.order_id.date_order[:4]
        elif group == 'period': # Season
            value = self.get_season_period(
                line.order_id.date_order)
        elif group == 'agent':
            value = line.order_id.partner_id.agent_id.name or ''
        elif group == 'family':
            value = line.product_id.family_id.name or ''
        else:
            _logger.error('No group value: %s' % mode)
            value = ''

        # Add header value if not present:
        if value not in olap_data['%s_header' % mode]:
            olap_data['%s_header' % mode].append(value)
        return value

    def collect_data_olap(self, olap_data, line):
        """ Collect data for OLAP Page
        """
        if not olap_data['active']:
            return

        # Get X data:
        x_value = self.coordinate_data(olap_data, 'x', line)
        y_value = self.coordinate_data(olap_data, 'y', line)

        # Insert data in table:
        key = (x_value, y_value)
        qty = line.product_uom_qty
        if key in olap_data['data']:
            i = 0
            if olap_data['field_show']['number']:
                olap_data['data'][key][i] += qty
                i += 1
            if olap_data['field_show']['real']:
                olap_data['data'][key][i] += qty * line.price_unit
                i += 1
            if olap_data['field_show']['total']:
                olap_data['data'][key][i] += line.price_subtotal
        else:
            olap_data['data'][key] = []
            if olap_data['field_show']['number']:
                olap_data['data'][key].append(qty)
            if olap_data['field_show']['real']:
                olap_data['data'][key].append(qty * line.price_unit)
            if olap_data['field_show']['total']:
                olap_data['data'][key].append(line.price_subtotal)

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------
    def action_sale_report(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}

        line_pool = self.pool.get('sale.order.line')
        excel_pool = self.pool.get('excel.writer')

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]

        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        from_date = wiz_browse.from_date
        to_date = wiz_browse.to_date

        # Browsable:
        partner = wiz_browse.partner_id
        fiscal = wiz_browse.fiscal_position_id
        agent = wiz_browse.agent_id
        product = wiz_browse.product_id
        family = wiz_browse.family_id
        country = wiz_browse.country_id
        state = wiz_browse.state_id
        region = wiz_browse.region_id

        sort = wiz_browse.sorted

        # OLAP:
        x_axis = wiz_browse.x_axis
        y_axis = wiz_browse.y_axis

        # Field to total:
        field_show = {
            'number': wiz_browse.field_number,
            'real': wiz_browse.field_real,
            'total': wiz_browse.field_total,
            }

        empty_header = []
        empty = []
        if field_show['number']:
            empty_header.append('Q')
            empty.append('')
        if field_show['real']:
            empty_header.append('Calcolato')
            empty.append('')
        if field_show['total']:
            empty_header.append('Fatturato')
            empty.append('')

        # ---------------------------------------------------------------------
        # Setup domain filter:
        # ---------------------------------------------------------------------
        domain = []
        filter_text = 'Ordini cliente: '

        # Period:
        if from_date:
            domain.append(
                ('order_id.date_order', '>=', from_date))
            filter_text += u'Dalla data %s, ' % from_date
        if to_date:
            domain.append(
                ('order_id.date_order', '<=', to_date))
            filter_text += u'Alla data %s, ' % to_date

        # Many2one
        if partner:
            domain.append(
                ('order_id.partner_id', '=', partner.id))
            filter_text += u'Cliente %s, ' % partner.name
        if fiscal:
            domain.append(
                ('order_id.partner_id.property_account_position', '=',
                 fiscal.id))
            filter_text += u'Pos. fiscale %s, ' % fiscal.name
        if agent:
            domain.append(
                ('order_id.partner_id.agent_id', '=', agent.id))
            filter_text += u'Agente %s, ' % agent.name
        if product:
            domain.append(
                ('product_id', '=', product.id))
            filter_text += u'Prodotto %s, ' % product.default_code
        if family:
            domain.append(
                ('product_id.family_id', '=', family.id))
            filter_text += u'Famiglia %s, ' % family.name

        if country:
            domain.append(
                ('order_id.partner_id.country_id', '=', country.id))
            filter_text += u'Nazione %s, ' % country.name
        if state:
            domain.append(
                ('order_id.partner_id.state_id', '=', state.id))
            filter_text += u'Stato %s, ' % state.name
        if region:
            domain.append(
                ('order_id.partner_id.state_id.region_id', '=', region.id))
            filter_text += u'Regione %s, ' % region.name

        # todo
        # Char

        # ---------------------------------------------------------------------
        #                               Excel:
        # ---------------------------------------------------------------------
        # Search and open line:
        line_ids = line_pool.search(cr, uid, domain, context=context)
        line_proxy = line_pool.browse(cr, uid, line_ids, context=context)

        # ---------------------------------------------------------------------
        # Collect data (for other pages):
        # ---------------------------------------------------------------------
        olap_data = {
            'active': x_axis and y_axis,
            'empty': empty,
            'empty_header': empty_header,

            # OLAP configuration:
            'x': x_axis,
            'y': y_axis,
            'field_show': field_show,

            # Report data:
            'data': {},
            'x_header': [],
            'y_header': [],
            }

        group_data = {
            # TODO
            }

        # ---------------------------------------------------------------------
        # Detail Page:
        # ---------------------------------------------------------------------
        ws_name = 'Ordini'
        excel_pool.create_worksheet(ws_name)

        # Format list:
        excel_pool.set_format()
        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_number = excel_pool.get_format('number')

        excel_pool.column_width(ws_name, [
            20, 20, 35,
            20, 15, 15, 35, 22, 35,
            30, 30, 30,
            10, 10, 10, 10, 15,
            ])

        # Title:
        row = 0
        excel_pool.write_xls_line(ws_name, row, [
            filter_text,
            ], default_format=f_title)

        # Header:
        row += 1
        excel_pool.write_xls_line(ws_name, row, [
            'Prodotto', 'Famiglia', 'Descrizione',
            'Documento', 'Data', 'Stagione', 'Partner', 'Pos. fiscale',
            'Agente', 'Via', 'Paese', 'Regione',
            'Q.', 'Listino', 'Sconto %', 'Prezzo Netto', 'Subtotale',
            ], default_format=f_header)

        # Sorted mode:
        if sort == 'partner':
            key = lambda x: x.partner_id.name
        elif sort == 'product':
            key = lambda x: x.product_id.default_code
        elif sort == 'agent':
            key = lambda x: (
                x.order_id.partner_id.agent_id.name,
                x.order_id.partner_id.name,
                )
        elif sort == 'family':
            key = lambda x: (
                x.product_id.family_id.name,
                x.product_id.default_code,
                )
        elif sort == 'region':
            key = lambda x: (
                x.order_id.partner_id.state_id.region_id,
                x.order_id.partner_id.name,
                )
        elif sort == 'country':
            key = lambda x: (
                x.order_id.partner_id.country_id.name,
                x.partner_id.name,
                )

        # Line:
        for line in sorted(line_proxy, key=key):
            # Collect data:
            self.collect_data_olap(olap_data, line)

            row += 1
            product = line.product_id
            order = line.order_id
            partner = order.partner_id
            # agent = partner.agent_id

            qty = line.product_uom_qty
            subtotal = line.price_subtotal
            net = (subtotal / qty) if qty else 0.0

            excel_pool.write_xls_line(ws_name, row, [
                product.default_code or '',
                product.family_id.name or '',
                product.name,

                order.name,
                order.date_order,
                self.get_season_period(order.date_order),
                partner.name,
                partner.property_account_position.name or '',
                partner.agent_id.name,

                partner.street,
                partner.city,
                partner.state_id.region_id.name,

                (qty, f_number),
                (line.price_unit, f_number),
                (line.discount, f_number),
                (net, f_number),
                (subtotal, f_number),
                ], default_format=f_text)

        # ---------------------------------------------------------------------
        # OLAP Page:
        # ---------------------------------------------------------------------
        if olap_data['active']:
            ws_name = 'OLAP'
            excel_pool.create_worksheet(ws_name)

            # -----------------------------------------------------------------
            # Header:
            # -----------------------------------------------------------------
            row = 0
            header_col_title = ['Dettaglio']
            header_col = ['Dettaglio']

            empty_header = olap_data['empty_header']
            empty_header_title = ['' for item in range(1, len(empty_header))]
            gap_col = len(empty_header)
            col = 1
            for y in sorted(olap_data['y_header']):
                # Master title (y axis):
                header_col_title.append(y or 'NON PRESENTE')
                header_col_title.extend(empty_header_title)
                # Merge cell for header first line:
                excel_pool.merge_cell(ws_name, [0, col, 0, col + gap_col - 1])
                col += gap_col

                # Header title (number total)
                header_col.extend(empty_header)

            excel_pool.column_width(ws_name, [
                40, ])  # TODO add other
            excel_pool.write_xls_line(
                ws_name, row, header_col_title, default_format=f_header)
            row += 1
            excel_pool.write_xls_line(
                ws_name, row, header_col, default_format=f_header)
            excel_pool.merge_cell(ws_name, [row -1, 0, row, 0])

            for x in sorted(olap_data['x_header']): # XXX Sort!
                row += 1
                excel_pool.write_xls_line(
                    ws_name, row, [
                        x or 'NON PRESENTE',
                        ], default_format=f_text)

                col = 1  # Reset colume every loop
                for y in sorted(olap_data['y_header']): # XXX Sort!
                    key = (x, y)
                    record = olap_data['data'].get(
                        key, olap_data['empty'])
                    excel_pool.write_xls_line(
                        ws_name, row, record, default_format=f_number, col=col)
                    col += len(record)

        # ---------------------------------------------------------------------
        # Detail Page:
        # ---------------------------------------------------------------------
        # TODO

        return excel_pool.return_attachment(cr, uid, 'CRM Report')

    # todo Also DDT
    def action_ddt_report(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        return True

    def action_invoice_report(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        return True

    def action_extract_oc_comparative(self, cr, uid, ids, context=None):
        """ OC for comparative operation
        """
        if context is None:
            context = {}

        order_pool = self.pool.get('sale.order.line')

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]

        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        from_date = wiz_browse.from_date
        to_date = wiz_browse.to_date
        reference_date = (
            wiz_browse.reference_date or
            datetime.now().strftime(DATE_FORMAT))
        reference_year = reference_date[:4]

        # ---------------------------------------------------------------------
        # Collect data:
        # ---------------------------------------------------------------------
        domain_sale = [
            ('state', 'not in', ('draft', 'sent', 'cancel')),
        ]

        if from_date:
            domain_sale.append(
                ('date_order', '>=', from_date))
            domain_ddt.append(
                ('date', '>=', from_date))
            domain_invoice.append(
                ('date_invoice', '>=', from_date))

        if to_date:
            domain_sale.append(
                ('date_order', '<=', to_date))
            domain_ddt.append(
                ('date', '<=', to_date))
            domain_invoice.append(
                ('date_invoice', '<=', to_date))

        ws_name = 'Dettaglio ordini'
        excel_pool.create_worksheet(ws_name)

        excel_pool.set_format()
        excel_format = {
            'title': excel_pool.get_format('title'),
            'header': excel_pool.get_format('header'),
            'white': {
                'text': excel_pool.get_format('text'),
                'number': excel_pool.get_format('number'),
            },
            'red': {
                'text': excel_pool.get_format('bg_red'),
                'number': excel_pool.get_format('bg_red_number'),
            },

        }

        excel_pool.column_width(ws_name, [
            8, 10, 8, 15,
            35, 20, 20, 20, 15,
            15, 10,
            10, 10,
            10, 10, 10, 15, 3, 5
        ])

        # -----------------------------------------------------------------
        # Title:
        # -----------------------------------------------------------------
        row = 0
        excel_pool.write_xls_line(
            ws_name, row, [filter_text], default_format=excel_format['title'])
        row += 1

        # -----------------------------------------------------------------
        # Header:
        # -----------------------------------------------------------------
        header = [
            'Documento', 'Stagione', 'Data', 'Origine',
            'Partner', 'Pos. fiscale', 'Regione', 'Nazione', 'Cat. Stat.',
            'Famiglia', 'Prodotto',
            'Scala', 'Sconto',
            'Q.', 'Prezzo', 'Netto', 'Totale', 'Rif.',
            'Usato',
        ]
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=excel_format['header'])
        excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)

        summary_db = {}
        for line in order_pool.browse(cr, uid, order_ids, context=context):
            # Readability:
            product = line.product_id
            order = line.order_id
            order_date = order.date_order[:10]
            order_date_reference = '{}{}'.format(  # Moved to this year
                reference_year,
                order_date[4:],
            )

            season = self.get_season_period(order.date_order)
            if season not in summary_db:
                summary_db[season] = 0.0

            # -------------------------------------------------------------
            # Data for partial / full order:
            # -------------------------------------------------------------
            qty = line.product_uom_qty
            subtotal = line.price_subtotal
            if order_date_reference <= reference_date:
                used = True
                summary_db[season] += subtotal
                format_color = excel_format['white']

            else:
                used = False
                format_color = excel_format['red']

            row += 1
            excel_pool.write_xls_line(
                ws_name, row, (
                _('OC'),
                season,
                date_order,
                order.name,
                order.partner_id.name,
                order.partner_id.property_account_position.name,
                order.partner_id.state_id.region_id.name or '',
                order.partner_id.country_id.name or '',
                order.partner_id.statistic_category_id.name or '',

                product.family_id.name or '',
                product.default_code or '',

                line.multi_discount_rates,
                line.discount,
                qty,
                line.price_unit,
                (subtotal / qty) if qty else 0.0,
                subtotal,
                product,
                'X' if used else '',
                ), default_format=format_color['text'])

        return excel_pool.return_attachment(cr, uid, 'CRM Report all')

    def action_extract_all(self, cr, uid, ids, context=None):
        """ All in one report:
        """
        if context is None:
            context = {}

        order_pool = self.pool.get('sale.order.line')
        ddt_pool = self.pool.get('stock.move')  # use stock move
        invoice_pool = self.pool.get('account.invoice.line')
        excel_pool = self.pool.get('excel.writer')

        # Document:
        sale_order_pool = self.pool.get('sale.order')
        stock_ddt_pool = self.pool.get('stock.ddt')
        account_invoice_pool = self.pool.get('account.invoice')

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]

        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        from_date = wiz_browse.from_date
        to_date = wiz_browse.to_date
        reference_date = wiz_browse.reference_date
        with_previsional = wiz_browse.with_previsional

        # Browseable:
        search_fiscal = wiz_browse.fiscal_position_id
        search_partner = wiz_browse.partner_id
        search_product = wiz_browse.product_id
        search_family = wiz_browse.family_id
        search_agent = wiz_browse.agent_id

        search_region = wiz_browse.region_id
        search_country = wiz_browse.country_id
        search_statistic = wiz_browse.statistic_category_id

        data_order = wiz_browse.data_order
        order_full = wiz_browse.order_full
        data_ddt = wiz_browse.data_ddt
        data_invoice = wiz_browse.data_invoice

        page_detail = True  # todo wiz_browse.page_detail
        page_price = wiz_browse.page_price
        page_comparison = wiz_browse.page_comparison
        page_comparison_family = wiz_browse.page_comparison_family

        # Filter comment:
        filter_text = 'Documenti: %s%s%s' % (
            '[OC] ' if data_order else '',
            '[DDT] ' if data_ddt else '',
            '[FT] ' if data_invoice else '',
            )

        # ---------------------------------------------------------------------
        # Total document of period
        # ---------------------------------------------------------------------
        domain_sale = [
            ('state', 'not in', ('draft', 'sent', 'cancel')),
            ]
        domain_ddt = [
            ('state', '=', 'confirmed'),
            ]
        domain_invoice = [
            ('state', '=', 'open'),
            ]

        if from_date:
            domain_sale.append(
                ('date_order', '>=', from_date))
            domain_ddt.append(
                ('date', '>=', from_date))
            domain_invoice.append(
                ('date_invoice', '>=', from_date))

        if to_date:
            domain_sale.append(
                ('date_order', '<=', to_date))
            domain_ddt.append(
                ('date', '<=', to_date))
            domain_invoice.append(
                ('date_invoice', '<=', to_date))

        if search_fiscal:
            domain_sale.append(
                ('partner_id.property_account_position', '=',
                 search_fiscal.id))
            domain_ddt.append(
                ('partner_id.property_account_position', '=',
                 search_fiscal.id))
            domain_invoice.append(
                ('partner_id.property_account_position', '=',
                 search_fiscal.id))
        if search_partner:
            domain_sale.append(
                ('partner_id', '=', search_partner.id))
            domain_ddt.append(
                ('partner_id', '=', search_partner.id))
            domain_invoice.append(
                ('partner_id', '=', search_partner.id))

        # Note: Used for filter agent linked with partner (not saved)
        if search_agent:
            domain_sale.append(
                ('partner_id.agent_id', '=', search_agent.id))
            domain_ddt.append(
                ('partner_id.agent_id', '=', search_agent.id))
            domain_invoice.append(
                ('partner_id.agent_id', '=', search_agent.id))

        if search_region:
            domain_sale.append(
                ('partner_id.state_id.region_id', '=', search_region.id))
            domain_ddt.append(
                ('partner_id.state_id.region_id', '=', search_region.id))
            domain_invoice.append(
                ('partner_id.state_id.region_id', '=', search_region.id))

        if search_country:
            domain_sale.append(
                ('partner_id.country_id', '=', search_country.id))
            domain_ddt.append(
                ('partner_id.country_id', '=', search_country.id))
            domain_invoice.append(
                ('partner_id.country_id', '=', search_country.id))

        # Total:
        sale_order_ids = sale_order_pool.search(
            cr, uid, domain_sale, context=context)
        stock_ddt_ids = stock_ddt_pool.search(
            cr, uid, domain_ddt, context=context)
        account_invoice_ids = account_invoice_pool.search(
            cr, uid, domain_invoice, context=context)

        # ---------------------------------------------------------------------
        #                           COLLECT DATA:
        # ---------------------------------------------------------------------
        master_data = []

        filter_text_total = \
            'Totali documenti del periodo: OC %s, DDT %s, Fatture: %s' % (
                len(sale_order_ids),
                len(stock_ddt_ids),
                len(account_invoice_ids),
                )
        filter_assigned = False

        # ---------------------------------------------------------------------
        # Load order:
        # ---------------------------------------------------------------------
        if data_order:
            domain = []
            filter_assigned = True

            # Open order
            if order_full:
                filter_text += u'Ordini tutti, '
            else:
                domain.append(
                    ('order_id.state', 'not in', ('draft', 'sent', 'cancel')))
                domain.append(('order_id.mx_closed', '=', False))
                filter_text += u'Ordini aperti, '

            # With previsional order:
            if with_previsional:
                filter_text += u'Con ordini previsionali, '
            else:
                domain.append(
                    ('order_id.previsional', '=', False))
                filter_text += u'Senza ordini previsionali, '

            # Period:
            if from_date:
                domain.append(
                    ('order_id.date_order', '>=', from_date))
                filter_text += u'Dalla data %s, ' % from_date
            if to_date:
                domain.append(
                    ('order_id.date_order', '<=', to_date))
                filter_text += u'Alla data %s, ' % to_date

            # Many2one
            if search_fiscal:
                domain.append(
                    ('order_id.partner_id.property_account_position', '=',
                     search_fiscal.id))
                filter_text += u'Pos. fiscale %s, ' % search_fiscal.name
            if search_partner:
                domain.append(
                    ('order_id.partner_id', '=', search_partner.id))
                filter_text += u'Cliente %s, ' % search_partner.name
            if search_family:
                domain.append(
                    ('product_id.family_id', '=', search_family.id))
                filter_text += u'Famiglia %s, ' % search_family.name
            if search_product:
                domain.append(
                    ('product_id', '=', search_product.id))
                filter_text += u'Prodotto %s, ' % search_product.default_code
            if search_agent:
                domain.append(
                    ('order_id.partner_id.agent_id', '=', search_agent.id))
                filter_text += u'Agente %s, ' % search_agent.name
            if search_region:
                domain.append(
                    ('order_id.partner_id.state_id.region_id', '=',
                     search_region.id))
                filter_text += u'OC Regione %s, ' % search_region.name
            if search_country:
                domain.append(
                    ('order_id.partner_id.country_id', '=', search_country.id))
                filter_text += u'OC Nazione %s, ' % search_country.name

            if search_statistic:
                domain.append(
                    ('order_id.partner_id.statistic_category_id', '=',
                     search_statistic.id))
                filter_text += u'OC Cat. statistica %s, ' % \
                               search_statistic.name

            # Search and open line:
            order_ids = order_pool.search(cr, uid, domain, context=context)
            _logger.warning('OC total lines: %s' % len(order_ids))
            for line in order_pool.browse(cr, uid, order_ids, context=context):
                # Readability:
                product = line.product_id
                order = line.order_id
                season = self.get_season_period(order.date_order)

                # -------------------------------------------------------------
                # Data for partial / full order:
                # -------------------------------------------------------------
                if order_full:
                    qty = line.product_uom_qty
                    subtotal = line.price_subtotal
                else:  # partial order
                    qty_full = line.product_uom_qty
                    qty = qty_full - line.delivered_qty  # remain
                    if qty <= 0.0:
                        continue  # Jump line

                    if qty_full: # division by zero
                        subtotal = qty * line.price_subtotal / qty_full
                    else:
                        subtotal = 0.0

                master_data.append((
                    _('OC'),
                    season,
                    order.date_order[:10],
                    order.name,
                    order.partner_id.name,
                    order.partner_id.property_account_position.name,
                    order.partner_id.state_id.region_id.name or '',
                    order.partner_id.country_id.name or '',
                    order.partner_id.statistic_category_id.name or '',

                    product.family_id.name or '',
                    product.default_code or '',

                    line.multi_discount_rates,
                    line.discount,
                    qty,
                    line.price_unit,
                    (subtotal / qty) if qty else 0.0,
                    subtotal,
                    product,
                    ))

        # ---------------------------------------------------------------------
        # Load DDT:
        # ---------------------------------------------------------------------
        if data_ddt:
            domain = [('picking_id.invoice_id', '=', False)] # Not yet invoiced
            filter_assigned = True

            # Period:
            if from_date:
                domain.append(
                    ('picking_id.ddt_id.date', '>=', from_date))
                if not filter_assigned:
                    filter_text += u'Dalla data %s, ' % from_date
            if to_date:
                domain.append(
                    ('picking_id.ddt_id.date', '<=', to_date))
                if not filter_assigned:
                    filter_text += u'Alla data %s, ' % to_date

            # Many2one
            if search_fiscal:
                domain.append(
                    ('picking_id.partner_id.property_account_position', '=',
                     search_fiscal.id))
                if not filter_assigned:
                    filter_text += u'Pos. fiscale %s, ' % search_fiscal.name
            if search_partner:
                domain.append(
                    ('picking_id.partner_id', '=', search_partner.id))
                if not filter_assigned:
                    filter_text += u'Cliente %s, ' % search_partner.name
            if search_family:
                domain.append(
                    ('product_id.family_id', '=', search_family.id))
                if not filter_assigned:
                    filter_text += u'Famiglia %s, ' % search_family.name
            if search_product:
                domain.append(
                    ('product_id', '=', search_product.id))
                if not filter_assigned:
                    filter_text += \
                        u'Prodotto %s, ' % search_product.default_code
            if search_agent:
                domain.append(
                    ('picking_id.partner_id.agent_id', '=', search_agent.id))
                filter_text += u'Agente %s, ' % search_agent.name
            if search_region:
                domain.append(
                    ('picking_id.partner_id.state_id.region_id', '=',
                     search_region.id))
                filter_text += u'PICK Regione %s, ' % search_region.name
            if search_country:
                domain.append(
                    ('picking_id.partner_id.country_id', '=',
                     search_country.id))
                filter_text += u'PICK Nazione %s, ' % search_country.name

            if search_statistic:
                domain.append(
                    ('picking_id.partner_id.statistic_category_id', '=',
                     search_statistic.id))
                filter_text += u'PICK Cat. statistica %s, ' % \
                               search_statistic.name

            # Search and open line:
            ddt_ids = ddt_pool.search(cr, uid, domain, context=context)
            _logger.warning('DDT total lines: %s' % len(ddt_ids))
            for line in ddt_pool.browse(
                    cr, uid, ddt_ids, context=context):
                # Readability:
                product = line.product_id
                ddt = line.picking_id.ddt_id
                sale_line = line.sale_line_id
                if sale_line:
                    qty = line.product_uom_qty
                    price_unit = sale_line.price_unit
                    price_unit_discount = \
                        (sale_line.price_subtotal / sale_line.product_uom_qty
                            ) if sale_line.product_uom_qty else 0.0
                    subtotal = price_unit * qty
                    subtotal_discount = price_unit * qty
                else:
                    qty = price_unit = price_unit_discount = subtotal = \
                        subtotal_discount = 0.0
                season = self.get_season_period(ddt.date)

                master_data.append((
                    _('DDT'),
                    season,
                    ddt.date[:10],
                    ddt.name,
                    ddt.partner_id.name,
                    ddt.partner_id.property_account_position.name,
                    ddt.partner_id.state_id.region_id.name or '',
                    ddt.partner_id.country_id.name or '',
                    ddt.partner_id.statistic_category_id.name or '',

                    product.family_id.name or '',
                    product.default_code or '',

                    sale_line.multi_discount_rates,
                    sale_line.discount,

                    qty,
                    price_unit,
                    price_unit_discount,
                    subtotal_discount,
                    product,
                    ))

        # ---------------------------------------------------------------------
        # Load invoice:
        # ---------------------------------------------------------------------
        if data_invoice:
            domain = []
            filter_assigned = True

            # Period:
            if from_date:
                domain.append(
                    ('invoice_id.date_invoice', '>=', from_date))
                if not filter_assigned:
                    filter_text += u'Dalla data %s, ' % from_date
            if to_date:
                domain.append(
                    ('invoice_id.date_invoice', '<=', to_date))
                if not filter_assigned:
                    filter_text += u'Alla data %s, ' % to_date

            # Many2one
            if search_fiscal:
                domain.append(
                    ('invoice_id.partner_id.property_account_position', '=',
                     search_fiscal.id))
                if not filter_assigned:
                    filter_text += u'Pos. fiscale %s, ' % search_fiscal.name
            if search_partner:
                domain.append(
                    ('invoice_id.partner_id', '=', search_partner.id))
                if not filter_assigned:
                    filter_text += u'Cliente %s, ' % search_partner.name
            if search_family:
                domain.append(
                    ('product_id.family_id', '=', search_family.id))
                if not filter_assigned:
                    filter_text += u'Famiglia %s, ' % search_family.name
            if search_product:
                domain.append(
                    ('product_id', '=', search_product.id))
                if not filter_assigned:
                    filter_text += \
                        u'Prodotto %s, ' % search_product.default_code
            if search_agent:
                domain.append(
                    ('invoice_id.partner_id.agent_id', '=', search_agent.id))
                filter_text += u'Agent %s, ' % search_agent.name
            if search_region:
                domain.append(
                    ('invoice_id.partner_id.state_id.region_id', '=',
                     search_region.id))
                filter_text += u'FT Regione %s, ' % search_region.name
            if search_country:
                domain.append(
                    ('invoice_id.partner_id.country_id', '=',
                     search_country.id))
                filter_text += u'FT Nazione %s, ' % search_country.name

            if search_statistic:
                domain.append(
                    ('invoice_id.partner_id.statistic_category_id', '=',
                     search_statistic.id))
                filter_text += u'FT Cat. statistica %s, ' % \
                               search_statistic.name

            # Search and open line:
            invoice_ids = invoice_pool.search(cr, uid, domain, context=context)
            _logger.warning('FT total lines: %s' % len(invoice_ids))
            for line in invoice_pool.browse(
                    cr, uid, invoice_ids, context=context):
                if line.invoice_id.type == 'out_refund':
                    sign = -1
                    document_mode = 'NC'
                else:
                    sign = 1
                    document_mode = 'FT'

                # Readability:
                product = line.product_id
                invoice = line.invoice_id
                qty = sign * line.quantity
                subtotal = sign * line.price_subtotal
                season = self.get_season_period(invoice.date_invoice)

                master_data.append((
                    document_mode,
                    season,
                    invoice.date_invoice[:10],
                    invoice.name,
                    invoice.partner_id.name,
                    invoice.partner_id.property_account_position.name,
                    invoice.partner_id.state_id.region_id.name or '',
                    invoice.partner_id.country_id.name or '',
                    invoice.partner_id.statistic_category_id.name or '',

                    product.family_id.name or '',
                    product.default_code or '',

                    line.multi_discount_rates,
                    line.discount,
                    qty,
                    line.price_unit,
                    (subtotal / qty) if qty else 0.0,
                    subtotal,
                    product,
                    ))

        # ---------------------------------------------------------------------
        #                               Excel:
        # ---------------------------------------------------------------------
        # Collect database:
        total_all = {}
        total_all_reference = {}
        total_family = {}
        total_family_reference = {}
        total_price = {}

        season_list = []
        reference_list = {}
        col_header = ['Q.', 'Totale']  # , '# doc.'] # XXX change?
        col_total = len(col_header)

        # ---------------------------------------------------------------------
        # Detail Page:
        # ---------------------------------------------------------------------
        if page_detail:
            ws_name = 'Dettaglio'
            excel_pool.create_worksheet(ws_name)

            # TODO Format list:
            excel_pool.set_format()
            f_title = excel_pool.get_format('title')
            f_header = excel_pool.get_format('header')
            f_text = excel_pool.get_format('text')
            f_number = excel_pool.get_format('number')
            f_number_red = excel_pool.get_format('bg_red_number')

            excel_pool.column_width(ws_name, [
                8, 10, 8, 15,
                35, 20, 20, 20, 15,
                15, 10,
                10, 10,
                10, 10, 10, 15, 3
                ])

            # -----------------------------------------------------------------
            # Title:
            # -----------------------------------------------------------------
            row = 0

            excel_pool.write_xls_line(ws_name, row, [
                filter_text,
                ], default_format=f_title)
            row += 1

            excel_pool.write_xls_line(ws_name, row, [
                filter_text_total,
                ], default_format=f_title)
            row += 1

            # -----------------------------------------------------------------
            # Header:
            # -----------------------------------------------------------------
            header = [
                'Documento', 'Stagione', 'Data', 'Origine',
                'Partner', 'Pos. fiscale', 'Regione', 'Nazione', 'Cat. Stat.',
                'Famiglia', 'Prodotto',
                'Scala', 'Sconto',
                'Q.', 'Prezzo', 'Netto', 'Totale', 'Rif.',
                ]
            excel_pool.write_xls_line(ws_name, row, header,
                default_format=f_header)
            excel_pool.autofilter(ws_name, row, 0, row, len(header) - 1)

            # Write record data as is:
            for record in sorted(master_data):
                row += 1

                (   # Record to variable:
                    document,
                    season,
                    date,
                    origin,
                    partner,
                    fiscal_position,
                    region,
                    country,
                    statistic_category,

                    family,
                    default_code,

                    discount,
                    discount_scale,
                    qty,
                    price,
                    price_net,
                    subtotal,
                    # total,
                    # rif,
                    product,
                    ) = record

                # discounted?

                # -------------------------------------------------------------
                #             Collect data for other report:
                # -------------------------------------------------------------
                if season not in season_list:
                    season_list.append(season)
                is_reference = 'X'  # always
                if reference_date:
                    if season not in reference_list:
                        month = reference_date[5:7]
                        reference_list[season] = '20%s%s' % (
                            season[:2] if month >= '09' else season[-2:],
                            reference_date[4:],
                            )
                    if date > reference_list[season]:
                        is_reference = ''

                # -------------------------------------------------------------
                # Total price:
                # -------------------------------------------------------------
                if page_price and default_code:
                    key = (family, default_code, product)
                    if key not in total_price:
                        total_price[key] = []
                    total_price[key].append((
                        date,
                        price,
                        price_net,
                        discount_scale,
                        ))

                # -------------------------------------------------------------
                # Total sale:
                # -------------------------------------------------------------
                # Total:
                if page_comparison:
                    if document not in total_all:
                        total_all[document] = {}
                    if season not in total_all[document]:
                        # Q, total
                        total_all[document][season] = [0.0, 0.0]
                    total_all[document][season][0] += qty  # Pz.
                    total_all[document][season][1] += subtotal  # Pz.

                # Total with reference date:
                if page_comparison and reference_date:
                    if is_reference:
                        if document not in total_all_reference:
                            total_all_reference[document] = {}
                        if season not in total_all_reference[document]:
                            # Q, total
                            total_all_reference[document][season] = [0.0, 0.0]
                        total_all_reference[document][season][0] += qty
                        total_all_reference[document][season][1] += subtotal

                # -------------------------------------------------------------
                # Total sale for family:
                # -------------------------------------------------------------
                if page_comparison_family:
                    key = (family, document)
                    if key not in total_family:
                        total_family[key] = {}
                    if season not in total_family[key]:
                        # Q, total
                        total_family[key][season] = [0.0, 0.0]

                    total_family[key][season][0] += qty  # Pz.
                    total_family[key][season][1] += subtotal  # Pz.

                # Total with reference date:
                if page_comparison_family and reference_date:
                    key = (family, document)
                    if is_reference:
                        if key not in total_family_reference:
                            total_family_reference[key] = {}
                        if season not in total_family_reference[key]:
                            # Q, total
                            total_family_reference[key][season] = [0.0, 0.0]
                        total_family_reference[key][season][0] += qty
                        total_family_reference[key][season][1] += subtotal

                # -------------------------------------------------------------
                # Write detail line:
                excel_pool.write_xls_line(
                    ws_name, row, [
                        document,
                        season,
                        date,
                        origin,
                        partner,
                        fiscal_position,
                        region,
                        country,
                        statistic_category,
                        family,
                        default_code,
                        discount,
                        discount_scale,
                        (qty, f_number),
                        (price, f_number),
                        (price_net, f_number),
                        (subtotal, f_number),
                        is_reference,
                        ], default_format=f_text)

        _logger.warning('Season: %s' % season_list)
        _logger.warning('Reference: %s' % reference_list)

        # ---------------------------------------------------------------------
        # Invoiced compared Page:
        # ---------------------------------------------------------------------
        if page_price:
            detail_mask = 'N.: %s, L.: %s (Sconto: %s) [Data: %s]'
            gap = 0.001
            extra_column_tot = 1

            ws_name = 'Prezzi'
            excel_pool.create_worksheet(ws_name)

            # Width setup:
            columns_width = [
                16, 10,
                10, 10,
                10,
                10, 10,
                10, 10,
                ]
            fixed_column = len(columns_width)

            excel_pool.column_width(
                ws_name, columns_width, default_format=f_text)

            row = 0
            excel_pool.write_xls_line(
                ws_name, row, [
                    'Famiglia',
                    'Codice',
                    'Ultimo prezzo',
                    'Ultimo sconto',
                    'Listino',
                    '50 + 30', '% Delta',
                    '50 + 40', '% Delta',
                    'Cambio prezzo (Netto, Lordo, Sconto, Data)',
                    ], default_format=f_header)

            row = 0
            old_code = {}
            for key in sorted(total_price):
                (family, default_code, product) = key
                old_price = False
                row += 1

                for date, price, price_net, discount_scale in sorted(
                        total_price[key]):

                    # ---------------------------------------------------------
                    # First time or change code:
                    # ---------------------------------------------------------
                    if old_price == False:
                        excel_pool.write_xls_line(
                            ws_name, row, [
                                family, default_code,
                                # TODO compiled after:
                                '', '',
                                '',  # Listino
                                '', '',  # 50 - 30
                                '', '',  # 50 - 40
                                detail_mask % (
                                    price_net, price, discount_scale, date,
                                    ),
                                ], default_format=f_text)
                        old_price = price_net
                        start_col = fixed_column

                    # ---------------------------------------------------------
                    # Extra change:
                    # ---------------------------------------------------------
                    else:
                        if abs(price_net - old_price) <= gap:
                            continue

                        start_col += 1
                        if start_col - (fixed_column) + 1 > extra_column_tot:
                            extra_column_tot = start_col - fixed_column + 1

                        excel_pool.write_xls_line(
                            ws_name, row, [
                                detail_mask % (
                                    price_net, price, discount_scale, date,
                                    ),
                                ], default_format=f_text, col= start_col)
                        old_price = price_net

                # -------------------------------------------------------------
                # Extra price:
                # -------------------------------------------------------------
                f_number_color = f_number
                lst_price = product.lst_price

                lst_50_30 = lst_price * 0.5 * 0.7
                if lst_50_30:
                    delta_50_30 = '%10.2f %%' % (
                        ((price_net - lst_50_30) / lst_50_30 * 100.0), )
                    if price_net < lst_50_30:
                        f_number_color = f_number_red
                else:
                    delta_50_30 = ''

                lst_50_40 = lst_price * 0.5 * 0.6
                if lst_50_40:
                    delta_50_40 = '%10.2f %%' % (
                        ((price_net - lst_50_40) / lst_50_40 * 100.0), )
                else:
                    delta_50_40 = ''

                excel_pool.write_xls_line(
                    ws_name, row, [
                        price_net, discount_scale,
                        lst_price,
                        lst_50_30, delta_50_30,
                        lst_50_40, delta_50_40,
                        ], default_format=f_number_color, col=2)

            # -----------------------------------------------------------------
            # Width setup extra columns:
            # -----------------------------------------------------------------
            columns_width = [45 for item in range(0, extra_column_tot)]
            excel_pool.column_width(
                ws_name, columns_width, col=fixed_column, default_format=f_text)
            excel_pool.merge_cell(
                ws_name, [
                    0, fixed_column, 0, fixed_column -1 + extra_column_tot])

        if page_comparison or page_comparison_family:
            multi_report = []

            # -----------------------------------------------------------------
            # A. Collect data total sold:
            # -----------------------------------------------------------------
            if page_comparison:
                ws_name = 'Venduto totale'
                excel_pool.create_worksheet(ws_name)

                multi_report.append((ws_name, total_all, 'Documento', '%s'))

                if reference_date:
                    ws_name = 'Venduto al %s' % reference_date[5:]
                    excel_pool.create_worksheet(ws_name)
                    multi_report.append((
                        ws_name,
                        total_all_reference,
                        'Documento al %s' % reference_date[5:],
                        '%s',
                        ))

            # -----------------------------------------------------------------
            # B. Collect data family sold:
            # -----------------------------------------------------------------
            if page_comparison_family:
                ws_name = 'Venduto famiglia'
                excel_pool.create_worksheet(ws_name)

                multi_report.append(
                    (ws_name, total_family, 'Famiglia', '%s [%s]'))

                if reference_date:
                    ws_name = 'Venduto famglia al %s' % reference_date[5:]
                    excel_pool.create_worksheet(ws_name)
                    multi_report.append((
                        ws_name,
                        total_family_reference,
                        'Documento al %s' % reference_date[5:],
                        '%s [%s]',
                        ))

            # -----------------------------------------------------------------
            #               Collect total document for season:
            # -----------------------------------------------------------------
            total_number_document = {'OC': {}, 'FT': {}, 'DDT': {}}

            # -----------------------------------------------------------------
            # 1. OC (sale order):
            # -----------------------------------------------------------------
            for order in sale_order_pool.browse(
                    cr, uid, sale_order_ids, context=context):
                date = order.date_order[:10]
                season = self.get_season_period(date)

                # Check reference:
                if reference_date and date > reference_list[season]:
                    continue

                if season in total_number_document['OC']:
                    total_number_document['OC'][season] += 1
                else:
                    total_number_document['OC'][season] = 1

            # -----------------------------------------------------------------
            # 2. DDT (transport document):
            # -----------------------------------------------------------------
            for ddt in stock_ddt_pool.browse(
                    cr, uid, stock_ddt_ids, context=context):
                date = ddt.date[:10]
                season = self.get_season_period(date)

                # Check reference:
                if reference_date and date > reference_list[season]:
                    continue

                if season in total_number_document['DDT']:
                    total_number_document['DDT'][season] += 1
                else:
                    total_number_document['DDT'][season] = 1

            # -----------------------------------------------------------------
            # 3. FT (invoice):
            # -----------------------------------------------------------------
            f_out = open(os.path.expanduser('~/invoice.log'), 'w')

            for invoice in account_invoice_pool.browse(
                    cr, uid, account_invoice_ids, context=context):
                date = invoice.date_invoice[:10]
                season = self.get_season_period(date)
                f_out.write('%s|%s|%s\n' % (
                    invoice.number,
                    date,
                    season,
                    ))

                # Check reference:
                if reference_date and date > reference_list[season]:
                    continue

                if season in total_number_document['FT']:
                    total_number_document['FT'][season] += 1
                else:
                    total_number_document['FT'][season] = 1

            # -----------------------------------------------------------------
            # Add 2 pages for document and family invoiced:
            # -----------------------------------------------------------------
            for ws_name, total_db, title, mask in multi_report:
                season_col = {}  # XXX every time?
                row = 0
                col = -1  # 1 extra fixed data!

                # -------------------------------------------------------------
                # First block of header:
                # -------------------------------------------------------------
                header = [title]
                excel_pool.column_width(ws_name, [25], default_format=f_text)
                excel_pool.write_xls_line(
                    ws_name, row, header, default_format=f_header)
                excel_pool.merge_cell(
                    ws_name, [row, 0, row + 1, 0])

                # -------------------------------------------------------------
                # Dynamic header:
                # -------------------------------------------------------------
                for season in sorted(season_list):
                    col += col_total
                    header = ['' for item in range(0, col_total)]
                    season_col[season] = col
                    excel_pool.merge_cell(
                        ws_name, [row, col, row, col + col_total - 1])

                    # Season:
                    excel_pool.write_xls_line(
                        ws_name, row, [season], default_format=f_header,
                        col=col)

                    # Subtitle:
                    excel_pool.write_xls_line(
                        ws_name, row + 1, col_header,
                        default_format=f_header, col=col)

                # -------------------------------------------------------------
                # Width setup:
                # -------------------------------------------------------------
                columns_width = [10 for item in range(0, col + 1)]
                excel_pool.column_width(
                    ws_name, columns_width, col=1, default_format=f_number)

                # -------------------------------------------------------------
                # Data:
                # -------------------------------------------------------------
                row += 1
                for document in sorted(total_db):
                    row += 1
                    excel_pool.write_xls_line(
                        ws_name, row, [mask % document],
                        default_format=f_text)

                    for season in total_db[document]:
                        start_col = season_col[season]
                        item = total_db[document][season]

                        # Add extra data (total document):
                        number_doc = total_number_document.get(
                            document, {}).get(season, 0)
                        # TODO item.append(number_doc)

                        excel_pool.write_xls_line(
                            ws_name, row, item,
                            default_format=f_number, col=start_col)

            # -----------------------------------------------------------------
            # Add Delivery data:
            # -----------------------------------------------------------------
            row = 8
            ws_name = 'Venduto totale'
            excel_pool.write_xls_line(
                ws_name, row, [
                    'Totale documenti',
                    ], default_format=f_header)
            row += 1
            for document in total_number_document:
                excel_pool.write_xls_line(
                    ws_name, row, [
                        document,
                        ], default_format=f_text)
                col = 1
                for season in sorted(total_number_document[document]):
                    excel_pool.write_xls_line(
                        ws_name, row, [
                            '# %s [%s]' % (
                                total_number_document[document][season],
                                season,
                                ),
                            ], default_format=f_text, col=col)
                    col += 2
                row += 1

        return excel_pool.return_attachment(cr, uid, 'CRM Report all')

    _columns = {
        # ---------------------------------------------------------------------
        # Report common parameters:
        # ---------------------------------------------------------------------
        # Period:
        'from_date': fields.date('From date >='),
        'to_date': fields.date('To date <='),

        # Foreign keys:
        'fiscal_position_id': fields.many2one(
            'account.fiscal.position', 'Posizione fiscale'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'family_id': fields.many2one('product.template', 'Family'),#todo filter
        'product_id': fields.many2one('product.product', 'Product'),

        # ---------------------------------------------------------------------
        # Report managed parameters:
        # ---------------------------------------------------------------------
        'agent_id': fields.many2one('res.partner', 'Agent'), # TODO filter
        'country_id': fields.many2one('res.country', 'Country'),
        'state_id': fields.many2one('res.country.state', 'State'),
        'region_id': fields.many2one('res.country.region', 'Region'),

        'statistic_category_id': fields.many2one(
            'statistic.category', 'Categoria statistica'),
        # city
        # cap

        # Numeric output data:
        'with_qty': fields.boolean(
            'With quantity',
            help='All data will be indicated total of quantity'),
        'with_total': fields.boolean(
            'With total',
            help='All data will be indicated with subtotal: price net x q.'),
        'with_discount': fields.boolean(
            'With discount',
            help='All data will be indicated with medium discount'),
        'with_pricelist': fields.boolean(
            'With pricelist',
            help='All data will be indicated with medium pricelist'),

        # Group by:
        'x_axis': fields.selection(axis_group, 'Asse X'),
        'y_axis': fields.selection(axis_group, 'Asse Y'),

        'field_number': fields.boolean('Field q.'),
        'field_real': fields.boolean(
            'Field real', help='Total without discount'),
        'field_total': fields.boolean(
            'Field discount total', help='Real total discounted'),

        'sorted': fields.selection([
            ('partner', 'Partner'),
            ('product', 'Product'),
            ('agent', 'Agent'),
            ('family', 'Family'),
            ('region', 'Region'),
            ('country', 'Country'),
            ], 'Sorted', required=True),

        # ---------------------------------------------------------------------
        # Report all:
        # ---------------------------------------------------------------------
        'reference_date': fields.date('Reference date (compare)'),
        'with_previsional': fields.boolean('With previsional order'),

        # Data manage
        'data_order': fields.boolean('With order'),
        'data_ddt': fields.boolean('With DDT pending'),
        'data_invoice': fields.boolean('With invoice'),

        'order_full': fields.boolean(
            'With full order',
            help='If check extract all order, instead remain order.'),

        # Page enable:
        'page_detail': fields.boolean('Page detail'),
        'page_price': fields.boolean('Page price'),
        'page_comparison': fields.boolean('Page comparison'),
        'page_comparison_family': fields.boolean('Page comparison family'),
        }

    _defaults = {
        # ---------------------------------------------------------------------
        # Report managed:
        # ---------------------------------------------------------------------
        'with_qty': lambda *x: True,
        'sorted': lambda *x: 'partner',
        'field_number': lambda *x: True,
        'field_real': lambda *x: True,
        'field_total': lambda *x: True,

        # ---------------------------------------------------------------------
        # Report all:
        # ---------------------------------------------------------------------
        # Data manage:
        'data_order': lambda *x: True,
        'data_ddt': lambda *x: True,
        'data_invoice': lambda *x: True,

        # Page show:
        'page_detail': lambda *x: True,
        'page_price': lambda *x: True,
        'page_comparison': lambda *x: True,
        'page_comparison_family': lambda *x: True,
        }
