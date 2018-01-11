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
    ''' Wizard for extract partner list in XLSX
    '''
    _name = 'res.partner.newsletter.extract.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_done(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        def get_mail(email):
            ''' Check mail and clean            
            '''
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
        # Create domain depend on parameter passed:
        # ---------------------------------------------------------------------        
        domain = []        
        if wiz_browse.newsletter_category_ids:
            nl_ids = [item.id for item in wiz_browse.newsletter_category_ids]
            domain.append(('newsletter_category_id', 'in', nl_ids))
            
        if wiz_browse.accounting == 'customer':                    
            domain.append(('sql_customer_code', '!=', False))
        elif wiz_browse.accounting == 'supplier':                    
            domain.append(('sql_supplier_code', '!=', False))
            
        if wiz_browse.country_id:
            domain.append(('country_id', '=', wiz_browse.country_id.id))

        if wiz_browse.state_id:
            domain.append(('state_id', '=', wiz_browse.state_id.id))

        # Last filter:
        domain.extend([
            '|', 
            ('email', '!=', False),
            ('email_promotional_id', '!=', False),
            ])
            
        # Create Excel WB
        ws_ml = _('Mailing list')
        header_line = ['Nome', 'Email', 'Categoria']
        xls_pool.create_worksheet(ws_ml)
        xls_pool.write_xls_line(ws_ml, 0, header_line)
        
        ws_out = _('Opt out partner')
        xls_pool.create_worksheet(ws_out)
        xls_pool.write_xls_line(ws_out, 0, header_line)

        ws_err = _('Errori mail')
        xls_pool.create_worksheet(ws_err)
        xls_pool.write_xls_line(ws_err, 0, header_line)
        
        partner_ids = partner_pool.search(cr, uid, domain, context=context)
        
        row = row_err = row_out = 0
        _logger.warning('Total partner selected: %s' % len(partner_ids))
        for partner in sorted(partner_pool.browse(
                cr, uid, partner_ids, context=context),
                key=lambda x: x.name):
                
            # Data:    
            name = partner.name            
            email = get_mail(partner.email)
            category = partner.newsletter_category_id.name \
                if partner.newsletter_category_id else '',

            if partner.news_opt_out:
                row_out += 1
                xls_pool.write_xls_line(
                    ws_out, row_out, [name, email, category])
                continue # No more write on file     

            if email:
                row += 1
                xls_pool.write_xls_line(
                    ws_ml, row, [name, email, category])        
            else:        
                row_err += 1
                xls_pool.write_xls_line(
                    ws_err, row_err, [name, email, category])

            if partner.email_promotional_id:
                email = get_mail(partner.email_promotional_id.email)
                if email:
                    row += 1
                    xls_pool.write_xls_line(ws_ml, row, [
                        partner.name, 
                        email,
                        partner.newsletter_category_id.name \
                            if partner.newsletter_category_id else '',
                        ])        
                else:        
                    row_err += 1
                    xls_pool.write_xls_line(
                        ws_err, row_err, [name, email, category])

            if not(row % 100):
                _logger.info('... Exporting: %s' % row)
                
        return xls_pool.return_attachment(
            cr, uid,
            'Newsletter', 'newsletter.xlsx', context=context)

    _columns = {
        'newsletter_category_ids': fields.many2many(
            'crm.newsletter.category', 'partner_category_news_rel', 
            'partner_id', 'category_id', 
            'Newsletter category'),
        'accounting': fields.selection([
            ('customer', 'Customer'),
            ('supplier', 'Supplier'),
            ('all', 'All'),
            ], 'Accounting', required=True),
        'country_id': fields.many2one(
            'res.country', 'Country', 
            ),
        'state_id': fields.many2one(
            'res.country.state', 'State', 
            ),
        }

    _defaults = {
        'accounting': lambda *x: 'customer',
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: