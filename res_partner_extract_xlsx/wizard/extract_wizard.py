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


class ModuleWizard(orm.TransientModel):
    """ Wizard for
    """
    _name = 'res.partner.extract.report.xlsx.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_print(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]

        partner_pool = self.pool.get('res.partner')
        excel_pool = self.pool.get('excel.writer')

        # ---------------------------------------------------------------------
        # Domain creation:
        # ---------------------------------------------------------------------
        domain = []
        domain_text = ''

        check_mode = wiz_browse.check

        # -----------------
        # Filter selection:
        # -----------------
        if wiz_browse.mode == 'all':
            domain_text += _('Tutti i partner; ')
        elif wiz_browse.mode == 'customer':
            domain.append(('sql_customer_code', '!=', False))
            domain_text += _('Solo clienti; ')
        elif wiz_browse.mode == 'supplier':
            domain.append(('sql_supplier_code', '!=', False))
            domain_text += _('Solo fornitori; ')
        elif wiz_browse.mode == 'destination':
            domain.append(('sql_destination_code', '!=', False))
            domain_text += _('Solo destinazioni; ')

        # ------------
        # Filter char:
        # ------------
        # Filter name:
        if wiz_browse.name:
            domain.append(('name', '=', wiz_browse.name))
            domain_text += _('Nome: %s; ') % wiz_browse.name

        # From name:
        if wiz_browse.from_name:
            domain.append(('name', '>=', wiz_browse.from_name))
            domain_text += _('Dal nome: %s; ') % wiz_browse.from_name
        # To name:
        if wiz_browse.to_name:
            domain.append(('name', '<=', wiz_browse.to_name))
            domain_text += _('Al nome: %s; ') % wiz_browse.to_name

        # Zip:
        if wiz_browse.zip:
            domain.append(('zip', '=', wiz_browse.zip))
            domain_text += _('CAP: %s; ') % wiz_browse.zip

        # City:
        if wiz_browse.city:
            domain.append(('city', '=', wiz_browse.city))
            domain_text += _('Citta\': %s; ') % wiz_browse.city

        # ----------------
        # Filter MO field:
        # ----------------
        # Agent:
        if wiz_browse.agent_id:
            domain.append(('agent_id', '=', wiz_browse.agent_id.id))
            domain_text += _('Agente: %s; ') % wiz_browse.agent_id.name

        # Country:
        if wiz_browse.country_id:
            domain.append(('country_id', '=', wiz_browse.country_id.id))
            domain_text += _('Nazione: %s; ') % wiz_browse.country_id.name

        # todo Region

        # Search
        partner_ids = partner_pool.search(cr, uid, domain, context=context)

        # ---------------------------------------------------------------------
        # Excel export:
        # ---------------------------------------------------------------------
        # Create:
        ws_name = _('Partner')
        excel_pool.create_worksheet(ws_name)
        row = 0

        # Format:
        excel_pool.set_format()

        f_title = excel_pool.get_format('title')
        f_header = excel_pool.get_format('header')
        f_text = excel_pool.get_format('text')
        f_text_green = excel_pool.get_format('bg_green')
        f_text_red = excel_pool.get_format('bg_red')
        f_text_yellow = excel_pool.get_format('bg_yellow')
        f_text_grey = excel_pool.get_format('bg_grey')

        # Layout:
        width = [
             40,
             # Address:
             40, 30, 10, 25,
             20, 20, 20, 20, 20,
             # Accounting:
             5, 5, 6, 18, 10,
             # Email:
             35, 35, 35, 35, 35, 35, 35, 35, 35, 35, 35,
             ]

        header = [
            _('Nome'),

            # Address:
            _('Indirizzo'),
            _('Città'),
            _('Cap'),
            _('Paese'),

            # Contact:
            _('Web'),
            _('Telefono'),
            _('Fax'),
            _('Cellulare'),
            _('Agente'),

            # Accounting:
            _('Cli.'),
            _('Forn.'),
            _('Dest.'),

            _('Categoria'),
            _('Opt out'),

            # Email:
            _('Email'),
            _('Email Listini'),
            _('Email Preventivi'),
            _('Email Conferme'),
            _('Email DDT'),
            _('Email Fatture'),
            _('Email Promozionali'),
            _('Email Ordini'),
            _('Email Magazzino'),
            _('Email Pagamenti'),
            _('Email PEC'),
        ]
        if check_mode:
            # Add first extra column
            width.insert(0, 0)
            width.append(40)

            header.insert(0, 'ID')
            header.append('Controllo duplicati')

        excel_pool.column_width(ws_name, width)

        # Title:
        excel_pool.write_xls_line(ws_name, row, [
            'Estrazione partner, filtro utilizzato:',
            domain_text,
            ], default_format=f_title)
        row += 2

        # Header:
        excel_pool.write_xls_line(
            ws_name, row, header, default_format=f_header)
        # XXX no row += 1

        # Loop for every partner:
        double = {
            'address': [],
            'name': [],
            'email': [],
            'phone': [],
        }

        for partner in sorted(partner_pool.browse(
                cr, uid, partner_ids, context=context),
                key=lambda p: (
                        0 if p.sql_customer_code else 1,
                        0 if p.sql_supplier_code else 1,
                        0 if p.sql_destination_code else 1,
                        p.name)):
            row += 1

            name = (partner.name or '').strip()
            address = '%s%s' % (
                (partner.street or '').strip() or
                    'No street {}'.format(partner.id),
                (partner.city or '').strip() or
                    'No city {}'.format(partner.id),
            )
            data_email = [
                (partner.email or '').strip(),
                (partner.email_pricelist_address or '').strip(),
                (partner.email_quotation_address or '').strip(),
                (partner.email_confirmation_address or '').strip(),
                (partner.email_ddt_address or '').strip(),
                (partner.email_invoice_address or '').strip(),
                (partner.email_promotional_address or '').strip(),
                (partner.email_order_address or '').strip(),
                (partner.email_picking_address or '').strip(),
                (partner.email_payment_address or '').strip(),
                (partner.email_pec_address or '').strip(),
            ]

            data = [
                name,

                # Address:
                partner.street or '',
                partner.city or '',
                partner.zip or '',
                partner.country_id.name or '',

                # Contact:
                partner.website or '',
                partner.phone or '',
                partner.fax or '',
                partner.mobile or '',
                partner.agent_id.name or '',

                # Accounting:
                'X' if partner.sql_customer_code else '',
                'X' if partner.sql_supplier_code else '',
                'X' if partner.sql_destination_code else '',

                partner.newsletter_category_id.name or '',
                'X' if partner.geo_optout else '',
                ]
            account_data = any(data[-3:])  # No X
            data.extend(data_email)

            # -----------------------------------------------------------------
            # Check mode:
            # -----------------------------------------------------------------
            color_text = f_text
            if check_mode:
                # Check double
                comment = ''

                # -------------------------------------------------------------
                # Account partner:
                # -------------------------------------------------------------
                not_account = True
                if account_data:
                    comment = 'Gestionale (non controllato)'
                    color_text = f_text_green
                    not_account = False

                elif (name.endswith('[pec]') or
                        name.endswith('[payment]') or
                        name.endswith('[order]') or
                        name.endswith('[invoice]') or
                        name.endswith('[ddt]') or
                        name.endswith('[promotional]') or
                        name.endswith('[confirmation]')):
                    comment = 'Mail Gestionale (non controllato)'
                    color_text = f_text_yellow
                    not_account = False

                # -------------------------------------------------------------
                # Common part:
                # -------------------------------------------------------------
                # Partner name:
                if not name:
                    if not_account:
                        comment += '[Nome non presente] '
                elif name in double['name']:
                    if not_account:
                        comment += '[Nome doppio] '
                else:
                    double['name'].append(name)

                # Partner address:
                if address and address in double['address']:
                    if not_account:
                        comment += '[Indirizzo doppio] '
                else:
                    double['address'].append(address)

                # Partner email (multi)
                for this_email in data_email:
                    if not this_email:
                        continue
                    elif this_email in double['email']:
                        if not_account:
                            comment += '[Email doppia] '
                    else:
                        double['email'].append(this_email)

                if comment and not_account:
                    color_text = f_text_red
                else:
                    if not_account:
                        comment = '[LEAD] '

                # Add extra data:
                data.insert(0, partner.id)
                data.append(comment)

            excel_pool.write_xls_line(
                ws_name, row, data, default_format=color_text)

        return excel_pool.return_attachment(
            cr, uid, ws_name,
            name_of_file='partner_wizard.xlsx', context=context)

    _columns = {
        # Char filter:
        'check': fields.boolean(
            'Controllo',
            help='Esporta anche ID partner e aggiunge una casella di '
                 'controllo per segnalare duplicati'),
        'name': fields.char('Name', size=64),
        'from_name': fields.char('From Name', size=64),
        'to_name': fields.char('To Name', size=64),

        'zip': fields.char('ZIP code', size=5),
        'city': fields.char('City', size=64),

        # M2O filter:
        'agent_id': fields.many2one('res.partner', 'Agent'),
        'country_id': fields.many2one('res.country', 'Country'),

        # Account filter:
        'mode': fields.selection([
            ('all', 'All'),
            ('customer', 'Customer'),
            ('supplier', 'Supplier'),
            ('destination', 'Destination'),
            ], 'Mode', required=True),
        }

    _defaults = {
        'mode': lambda *x: 'customer',
        }
