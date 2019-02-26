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
    ''' Wizard for extract data from sale, invoice
    '''
    _name = 'crm.excel.extract.report.wizard'
    _description = 'CRM Excel export'

    def coordinate_data(self, x, line):
        ''' Extract coordinate data from line
        '''
        if olap_data['x'] == 'year':
            return = line.product_id.date_order[:4]
        elif olap_data['x'] == 'period':
            return = line.order_id.date_order # TODO
        elif olap_data['x'] == 'agent':
            return = line.order_id.partner_id.agent_id
        elif olap_data['x'] == 'family':
            return = line.product_id.family_id
        else:
            _logger.error('No X value: %s' % x)
            return = False
        
    def collect_data_olap(self, olap_data, line):
        ''' Collect data for OLAP Page
        '''
        if not olap_data['active']:
            return
        
        # Get X data:
        x_value = self.coordinate_date(olap_data['x'], line)
        if x_value not in olap_data['x_header']:
            olap_data['x_header'].append(x_value)
            
        y_value = self.coordinate_date(olap_data['y'], line)
        if y_value not in olap_data['y_header']:
            olap_data['y_header'].append(y_value)

        # Insert data in table:
        key = (x_value, y_value)
        if key not in olap_data['data']:
            olap_data['data'][key] = [
                0.0, # quantity
                0.0, # subtotal
                0.0, # not discunted
                ] # TODO total block
        
        # Update data:
        qty = line.product_uom_qty
        olap_data['data'][key][0] += qty
        olap_data['data'][key][1] += line.price_subtotal
        olap_data['data'][key][2] += qty * price_unit

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------
    def action_sale_report(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
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

        # Browseable:
        partner = wiz_browse.partner_id
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

        # ---------------------------------------------------------------------
        # Setup domain filter:
        # ---------------------------------------------------------------------
        domain = []
        filter_text = 'Ordini cliente: '
        
        #Period:
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
            filter_text += u'Cliente %s, ' % family.name
                                
        if country:
            domain.append(
                ('order_id.partner_id.country_id', '=', country.id))
            filter_text += u'Cliente %s, ' % country.name
        if state:
            domain.append(
                ('order_id.partner_id.state_id', '=', state.id))
            filter_text += u'Cliente %s, ' % state.name
        if region:
            domain.append(
                ('order_id.partner_id.state_id.region_id', '=', region.id))
            filter_text += u'Cliente %s, ' % region.name

        # TODO    
        # Char
        
        # Search and open line:
        line_ids = line_pool.search(cr, uid, domain, context=context)
        line_proxy = line_pool.browse(cr, uid, line_ids, context=context)

        # ---------------------------------------------------------------------        
        # Sorted mode:
        # ---------------------------------------------------------------------        
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

        # ---------------------------------------------------------------------        
        #                               Excel:
        # ---------------------------------------------------------------------        

        
        # ---------------------------------------------------------------------        
        # Collect data (for other pages):
        # ---------------------------------------------------------------------        
        olap_data = {
            'active': x_axis and y_axis,
            'empty': ['', '', ''], # empty line

            # Configuration:
            'x': x_axis,
            'y': y_axis,
            
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
            20, 35, 35, 
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
            'Documento', 'Partner', 'Agente', 
            'Via', 'Paese', 'Regione', 
            'Q.', 'Prezzo', 'Sconto', 'Netto', 'Subtotale',
            ], default_format=f_header)
            
        # Line:
        for line in sorted(line_proxy, key=key):
            # Collect data:
            self.collect_data_olap(olap_data, line)
             
            row += 1
            product = line.product_id
            order = line.order_id
            partner = order.partner_id
            #agent = partner.agent_id
            
            qty = line.product_uom_qty
            subtotal = line.price_subtotal
            net = (line.price_subtotal / qty) if qty else 0.0

            excel_pool.write_xls_line(ws_name, row, [
                product.default_code or '', 
                product.family_id.name or '', 
                product.name,
                
                order.name, 
                partner.name, 
                partner.agent_id.name,
                
                partner.street, 
                partner.city,
                partner.state_id.region_id.name, 

                (qty, f_number),
                (line.price_unit, f_number), 
                (line.discount, f_number),
                (net, f_number),
                (line.price_subtotal, f_number),
                ], default_format=f_text)
        
        # ---------------------------------------------------------------------        
        # OLAP Page:
        # ---------------------------------------------------------------------        
        olap_data = {
            'x': x_axis,
            'y': y_axis,
            
            # Report data:
            'data': {},
            'x_header': [],
            'y_header': [],            
            }
                    
        if olap_data['active']:
            ws_name = 'OLAP'

            # Header:    
            row = 0        
            excel_pool.write_xls_line(ws_name, row, [
                'Dettaglio', 
                ], default_format=f_header)

            row += 1
            for x in olap_data['x']:
                col = 1
                for y in olap_data['y']:
                    key = (x, y)
                    record = olap_data['data'].get(
                        key, olap_data['data']['empty'])
                    excel_pool.write_xls_line(
                        ws_name, row, record, 
                        default_format=f_header, 
                        col=col)
                    col += len(record)    

        # ---------------------------------------------------------------------        
        # Detail Page:
        # ---------------------------------------------------------------------        
        # TODO 
                    

        return excel_pool.return_attachment(cr, uid, 'CRM Report')

    # TODO Also DDT
    def action_ddt_report(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        if context is None: 
            context = {}

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        return True
    
    def action_invoice_report(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        if context is None: 
            context = {}

        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        return True

    _columns = {
        # Period:
        'from_date': fields.date('From date >='),
        'to_date': fields.date('To date <='),
        
        # Foreign keys:
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'agent_id': fields.many2one('res.partner', 'Agent'), # TODO filter
        'product_id': fields.many2one('product.product', 'Product'),
        'family_id': fields.many2one('product.product', 'Family'), # TODO filter        
        'country_id': fields.many2one('res.country', 'Country'),
        'state_id': fields.many2one('res.country.state', 'State'),
        'region_id':fields.many2one('res.country.region', 'Region'),
        # city
        # cap

        # Numeric output data:
        'with_qty': fields.boolean('With quantity', 
            help='All data will be indicated total of quantity'),
        'with_total': fields.boolean('With total', 
            help='All data will be indicated with subtotal: price net x q.'),
        'with_discount': fields.boolean('With discount', 
            help='All data will be indicated with medium discount'),
        'with_pricelist': fields.boolean('With pricelist', 
            help='All data will be indicated with medium pricelist'),
        
        # Group by:    
        'x_axis': fields.selection(axis_group, 'Asse X'),
        'y_axis': fields.selection(axis_group, 'Asse Y'),            
        
        'sorted': fields.selection([
            ('partner', 'Partner'),
            ('product', 'Product'),
            ('agent', 'Agent'),
            ('family', 'Family'),
            ('region', 'Region'),
            ('country', 'Country'),
            ], 'Sorted', required=True),
        }
        
    _defaults = {
        'with_qty': lambda *x: True,
        'sorted': lambda *x: 'partner',
        }        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
