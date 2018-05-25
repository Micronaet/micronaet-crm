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
        
        # Agent:
        
        # Filter name:
        
        # From name:
        # To name
        
        # Country:
        
        # TODO Region, CAP, City
        
        # Search 
        
        # ---------------------------------------------------------------------
        # Excel export:
        # ---------------------------------------------------------------------
        # Create:
        ws_name = 'Partner'
        excel_pool.create_worksheet(ws_name)
        row = 0
        
        # Title:
        
        
        # Header:
        header = [
            _('Nome'),
            _('Indirizzo'),
            
            ]
        
        # Loop for every partner:
        #line = [
        #    partner.name
        #    ]
        # excel_pool.write_xls_line(ws_name, row, line, default_format=False)
        
        return excel_pool.return_attachment(cr, uid, ws_name, 
             name_of_file='partner_wizard.xlsx', context=context)

    _columns = {
        
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
