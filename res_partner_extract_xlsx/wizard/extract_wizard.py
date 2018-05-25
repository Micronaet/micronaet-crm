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
    ''' Wizard for
    '''
    _name = 'res.partner.extract.report.xlsx.wizard'

    # --------------------
    # Wizard button event:
    # --------------------
    def action_print(self, cr, uid, ids, context=None):
        ''' Event for button done
        '''
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
            # TODO 

            
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
            # TODO
            
        # To name
        if wiz_browse.to_name:
            domain.append(('name', '<=', wiz_browse.to_name))
            # TODO 
            
        # TODO ZIP
        # TODO city    
            
        # TODO Region
        
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
        
        # Layout:
        column_width(ws_name, [
             40,
             
             # Address: 
             40,
             30,
             10,
             25,
             
             # Email:
             # TODO 
             ])
        
        # Title:
        excel_pool.write_xls_line(ws_name, row, [
            'Estrazione partner, filtro utilizzato:',
            
            ], default_format=f_title)
        
        
        # Header:
        excel_pool.write_xls_line(ws_name, row, [
            partner.name,
            partner.street or '',
            
            
            ], default_format=f_header)
        header = [
            _('Nome'),            
            
            # Address:
            _('Indirizzo'),
            _('Città'),
            _('Cap'),
            _('Paese'),
                        
            # E-mail:
            _('Email'),
            _('Email Listini'),
            # TODO 
            _('Web'),
            
            _('Telefono'),
            
            # Accounting:
            _('Cliente'),
            _('Fornitore'),
            _('Destinazione'),
            ]
        
        # Loop for every partner:
        for partner in partner_pool.browse(
                cr, uid, partner_ids, context=context):
            excel_pool.write_xls_line(ws_name, row, [
                partner.name,
                partner.street or '',
                
                # TODO 
                
                ], default_format=f_text)
        
        return excel_pool.return_attachment(cr, uid, ws_name, 
             name_of_file='partner_wizard.xlsx', context=context)

    _columns = {
        # Char filter:
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
            ], 'Mode'),
        }
     
    _defaults = {
        'mode': lambda *x: 'customer',
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
