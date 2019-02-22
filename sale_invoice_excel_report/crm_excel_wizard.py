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
    ('period', 'Season'),
    ('agent', 'Agent'),
    ('family', 'Family'),
    ]

class CrmExcelExtractReportWizard(orm.TransientModel):
    ''' Wizard for extract data from sale, invoice
    '''
    _name = 'crm.excel.extract.report.wizard'
    _description = 'CRM Excel export'

    # -------------------------------------------------------------------------
    # Wizard button event:
    # -------------------------------------------------------------------------
    def action_sale_report(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
        if context is None: 
            context = {}

        line_ids = self.pool.get('sale.order.line')
        wiz_browse = self.browse(cr, uid, ids, context=context)[0]
        
        # ---------------------------------------------------------------------
        # Parameters:
        # ---------------------------------------------------------------------
        from_date = wiz_browse.from_date
        to_date = wiz_browse.to_date
        partner_id = wiz_browse.partner_id.id
        agent_id = wiz_browse.agent_id.id
        product_id = wiz_browse.product_id.id
        family_id = wiz_browse.family_id.id
        country_id = wiz.browse.country_id.id
        state_id = wiz.browse.state_id.id
        region_id = wiz.browse.region_id.id
                
        # ---------------------------------------------------------------------
        # Setup domain filter:
        # ---------------------------------------------------------------------
        domain = []
        
        #Period:
        if from_date:
            domain.append(
                ('order_id.date_order', '>=', from_date))    
        if to_date:
            domain.append(
                ('order_id.date_order', '<=', to_date))
            
        # Many2one 
        if partner_id:
            domain.append(
                ('order_id.partner_id', '=', partner_id))
        if agent_id:
            domain.append(
                ('order_id.partner_id.agent_id', '=', agent_id))
        if product_id:
            domain.append(
                ('product_id', '=', product_id))
        if family_id:
            domain.append(
                ('product_id.family_id', '=', family_id))
                                
        # TODO    
        # Char
        if country_id:
            domain.append(
                ('order_id.partner_id.country_id', '=', country_id))
        if state_id:
            domain.append(
                ('order_id.partner_id.state_id', '=', state_id))
        if region_id:
            domain.append(
                ('order_id.partner_id.state_id.region_id', '=', region_id))
           
        return True

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
        }
        
    _defaults = {
        'with_qty': lambda *x: True,
        }        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
