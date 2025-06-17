# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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


class ResPartnerNewsletterExtractWizard(orm.TransientModel):
    """ Wizard for extract partner list in XLSX
    """
    _name = 'res.partner.newsletter.extract.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_done(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        def clean_mail(email):
            """ Check mail and clean
            """
            if not email:
                return False
            email = email.strip()
            if '@' not in email:
                return False
            return email

        # Pool used
        partner_pool = self.pool.get('res.partner')
        xls_pool = self.pool.get('excel.writer')

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]

        # ---------------------------------------------------------------------
        # Invoice part:
        # ---------------------------------------------------------------------
        with_invoice = wiz_browse.with_invoice
        invoice_date = wiz_browse.invoice_date
        mode = wiz_browse.mode
        agent = wiz_browse.agent_id

        partner_invoiced = {}
        if with_invoice:
            invoice_pool = self.pool.get('account.invoice')
            if invoice_date:
                _logger.warning(
                    'Extract also invoice data from %s' % invoice_date)
                invoice_domain = [('date_invoice', '>=', invoice_date)]
            else:
                invoice_domain = []

            invoice_ids = invoice_pool.search(cr, uid, invoice_domain,
                context=context)
            for invoice in invoice_pool.browse(
                    cr, uid, invoice_ids, context=context):
                partner_id = invoice.partner_id.id
                if partner_id not in partner_invoiced:
                    partner_invoiced[partner_id] = 0.0
                partner_invoiced[partner_id] += invoice.amount_untaxed

        # ---------------------------------------------------------------------
        # Create domain depend on parameter passed:
        # ---------------------------------------------------------------------
        domain = []

        if wiz_browse.no_opt_out:
            domain.append(('news_opt_out', '=', False))
        if wiz_browse.newsletter_category_ids:
            nl_ids = [item.id for item in wiz_browse.newsletter_category_ids]
            domain.append(('newsletter_category_id', 'in', nl_ids))

        if wiz_browse.accounting == 'customer':
            domain.append(('sql_customer_code', '!=', False))
        elif wiz_browse.accounting == 'supplier':
            domain.append(('sql_supplier_code', '!=', False))
        elif wiz_browse.accounting == 'destination':
            domain.append(('sql_destination_code', '!=', False))

        elif wiz_browse.accounting == 'not_customer':
            domain.append(('sql_customer_code', '=', False))
        elif wiz_browse.accounting == 'not_supplier':
            domain.append(('sql_supplier_code', '=', False))
        elif wiz_browse.accounting == 'not_destination':
            domain.append(('sql_destination_code', '=', False))

        if wiz_browse.country_id:
            # domain.append(('country_id', '=', wiz_browse.country_id.id))
            country_id = wiz_browse.country_id.id
        else:
            country_id = False
        if wiz_browse.no_country_id:
            # domain.append(('country_id', '!=', wiz_browse.no_country_id.id))
            no_country_id = wiz_browse.no_country_id.id
        else:
            no_country_id = False

        if wiz_browse.fiscal_id:
            domain.append(('property_account_position', '=',
                wiz_browse.fiscal_id.id))
        if wiz_browse.no_fiscal_id:
            domain.append(('property_account_position', '!=',
                wiz_browse.no_fiscal_id.id))

        if wiz_browse.state_id:
            domain.append(('state_id', '=', wiz_browse.state_id.id))

        if agent:
            domain.append(('agent_id', '=', agent.id))

        _logger.warning('Domain: %s' % (domain, ))
        # Last filter:
        # domain.extend([
        #    '|',
        #    ('email', '!=', False),
        #    ('email_promotional_id', '!=', False),
        #    ])

        # Prefetch data:
        partner_ids = partner_pool.search(cr, uid, domain, context=context)
        partners = sorted(partner_pool.browse(
                cr, uid, partner_ids, context=context), key=lambda x: x.name)

        # ---------------------------------------------------------------------
        #                       PROMOTIONAL MODE:
        # ---------------------------------------------------------------------
        if mode == 'promotional':
            header_line = [
                'Partner', 'Email', 'Lingua',
                'Indirizzo', 'Paese', 'Provincia', 'Nazione',
                ]
            column_w = [
                40, 35, 10,
                35, 35, 10, 20,
            ]

            # Create Excel WB
            ws_ml = _('Mailing')

            xls_pool.create_worksheet(ws_ml)
            xls_pool.write_xls_line(ws_ml, 0, header_line)
            xls_pool.column_width(ws_ml, column_w)

            _logger.warning('Total partner selected: %s' % len(partner_ids))

            records = {}
            for partner in partners:
                # Check country parameters:
                if country_id and partner.country_id.id != country_id:
                    continue
                if no_country_id and partner.country_id.id == no_country_id:
                    continue

                # Loop for use N email address for promotionals
                partner_email = [partner]
                exclude_ids = set((
                    partner.email_picking_id.id,
                    partner.email_ddt_id.id,
                    partner.email_invoice_id.id,
                    partner.email_payment_id.id,
                    partner.email_pec_id.id,
                    ))

                for contact in partner.child_ids:
                    if contact.id not in exclude_ids:
                        partner_email.append(contact)

                for recipient in partner_email:
                    email = recipient.email
                    if email:
                        email = clean_mail(email)

                    if not email:  # Separate test not in else!
                        continue

                    records[email] = partner

            row = 0
            for email in sorted(records, key=lambda x: records[x].name):
                partner = records[email]

                italian = partner.company_id.country_id == partner.country_id

                row += 1
                xls_pool.write_xls_line(ws_ml, row, [
                    partner.name.strip(),
                    email,
                    'Italiano' if italian else 'Inglese',

                    partner.street or '',
                    partner.city or '',
                    partner.state_id.code if partner.state_id else '',
                    partner.country_id.name if partner.country_id else '',
                    ])

        else:
            header_line = [
                'ID',
                'Mail generica', 'Mail promozionale', 'Mail listini',
                'Mail offerte', 'Mail conferme ordine', 'Mail ordini',
                'Mail magazzino', 'Mail DDT', 'Mail fatture', 'Mail pagamenti',
                'Mail PEC',

                'Azienda', 'Cli,', 'For.', 'Agente',
                'Nome', 'Paese', 'Nazione', 'Categoria', 'Gruppo',
                'Fatturato (%s)' % (invoice_date or 'Tutti'),
                ]
            if wiz_browse.extra_data:
                header_line.extend([
                    'Codice cliente',
                    'Codice fornitore',
                    'Codice destinazione',
                    ])
            column_w = [
                1,
                55, 55, 55, 55, 55, 55, 55, 55, 55, 55, 55,
                5, 5, 5, 25,
                45, 35, 30, 20, 20, 20, 20, 20, 15]

            # Create Excel WB
            ws_ml = _('Mailing list')

            xls_pool.create_worksheet(ws_ml)
            xls_pool.write_xls_line(ws_ml, 0, header_line)
            xls_pool.column_width(ws_ml, column_w)

            ws_out = _('Opt out partner')
            xls_pool.create_worksheet(ws_out)
            xls_pool.write_xls_line(ws_out, 0, header_line)
            xls_pool.column_width(ws_out, column_w)

            ws_err = _('Errori mail')
            xls_pool.create_worksheet(ws_err)
            xls_pool.write_xls_line(ws_err, 0, header_line)
            xls_pool.column_width(ws_err, column_w)

            row = row_err = row_out = 0
            _logger.warning('Total partner selected: %s' % len(partner_ids))

            for partner in partners:
                if country_id and partner.country_id.id != country_id:
                    continue

                if no_country_id and partner.country_id.id == no_country_id:
                    continue

                # Data to export:
                record = [
                    partner.id,

                    clean_mail(partner.email),
                    clean_mail(partner.email_promotional_address),
                    clean_mail(partner.email_pricelist_address),
                    clean_mail(partner.email_quotation_address),
                    clean_mail(partner.email_confirmation_address),
                    clean_mail(partner.email_order_address),
                    clean_mail(partner.email_picking_address),
                    clean_mail(partner.email_ddt_address),
                    clean_mail(partner.email_invoice_address),
                    clean_mail(partner.email_payment_address),
                    clean_mail(partner.email_pec_address),

                    'X' if partner.is_company else '',
                    'X' if partner.customer else '',
                    'X' if partner.supplier else '',
                    partner.agent_id.name or '',

                    partner.name,
                    partner.city,
                    partner.country_id.name if partner.country_id else '',
                    partner.newsletter_category_id.name if partner.newsletter_category_id else '',
                    partner.newsletter_group or '',
                    partner_invoiced.get(partner.id, 0.0),
                    ]

                if wiz_browse.extra_data:
                    record.extend([
                        partner.sql_customer_code,
                        partner.sql_supplier_code,
                        partner.sql_destination_code,
                        ])
                if partner.news_opt_out:
                    row_out += 1
                    xls_pool.write_xls_line(
                        ws_out, row_out, record)
                    continue  # No more write on file

                if record[0]:  # email present
                    row += 1
                    xls_pool.write_xls_line(ws_ml, row, record)
                else:
                    row_err += 1
                    xls_pool.write_xls_line(
                        ws_err, row_err, record)

                if partner.email_promotional_id:
                    record[0] = clean_mail(partner.email_promotional_id.email)
                    if record[0]:  # email
                        row += 1
                        xls_pool.write_xls_line(ws_ml, row, record)
                    else:
                        row_err += 1
                        xls_pool.write_xls_line(
                            ws_err, row_err, record)

                if not(row % 100):
                    _logger.info('... Exporting: %s' % row)

            _logger.info('Total %s, Mail: %s, Optout: %s, No mail: %s' % (
                row + row_err + row_out,
                row,
                row_out,
                row_err,
                ))

        # Common part:
        return xls_pool.return_attachment(
            cr, uid,
            'Newsletter', 'newsletter.xlsx', context=context)

    _columns = {
        'newsletter_category_ids': fields.many2many(
            'crm.newsletter.category', 'partner_category_news_rel',
            'partner_id', 'category_id',
            'Newsletter category'),

        'mode': fields.selection([
            # Account:
            ('default', 'Default'),
            ('promotional', 'Promozionale'),
            ], 'Accounting', required=True),

        'accounting': fields.selection([
            # Account:
            ('customer', 'Customer'),
            ('supplier', 'Supplier'),
            ('destination', 'Destination'),

            # Not account:
            ('not_customer', 'Non cliente'),
            ('not_supplier', 'Non fornitore'),
            ('not_destination', 'Non destinazione'),

            ('all', 'All'),
            ], 'Accounting', required=True),

        'with_invoice': fields.boolean(
            'Con fatturato',
            help='Se spuntato attiva il conteggio fatturato nella relativa '
                 'colonna'),
        'invoice_date': fields.date('Dalla data (fatturazione)'),

        # Country:
        'country_id': fields.many2one(
            'res.country', 'Country',
            ),
        'no_country_id': fields.many2one(
            'res.country', 'No Country',
            ),
        'extra_data': fields.boolean('Extra dati',
            help='Aggiunge colonne non presenti di solito per la importazione',
            ),
        'no_opt_out': fields.boolean('No opt-out',
            help='Esporta solo quelli che non si sono chiamati fuori',
            ),
        # Fiscal position:
        'fiscal_id': fields.many2one(
            'account.fiscal.position', 'Fiscal position',
            ),
        'no_fiscal_id': fields.many2one(
            'account.fiscal.position', 'No Fiscal position',
            ),

        'state_id': fields.many2one(
            'res.country.state', 'State',
            ),
        'agent_id': fields.many2one(
            'res.partner', 'Agente',
            ),
        }

    _defaults = {
        'mode': lambda *x: 'default',
        'accounting': lambda *x: 'customer',
        'no_opt_out': lambda *x: True,
        }
