# -*- coding: utf-8 -*-
###############################################################################
#
#    Copyright (C) 2001-2014 Micronaet SRL (<http://www.micronaet.it>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
import os
import sys
import logging
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)


_logger = logging.getLogger(__name__)

class ProductProductCatalog(orm.Model):
    """ Model name: Catalog
    """    
    _name = 'product.product.catalog'
    _description = 'Product catalog'    

    _columns = {
        'name': fields.char('Catalog', size=64, required=True), 
        'note': fields.text('Note'),
        'from_date': fields.date('From date'),
        'to_date': fields.date('To date'),
        }

class ProductTemplate(orm.Model):
    """ Model name: ProductTemplate
    """    
    _inherit = 'product.template'
    
    _columns = {
        'catalog_ids': fields.many2many(
            'product.product.catalog', 'product_catalog_rel', 
            'product_id', 'catalog_id', 
            'Catalog'), 
        'status': fields.selection([
            # Raw materials:
            ('exit', 'Uscente'),
            ('used', 'In uso'),
            ('kurtz', 'Kurtz'),
    
            # Both:
            ('catalog', 'Catalog'),
            ('obsolete', 'Obsolete'),
            
            # Product:
            ('out', 'Out catalog'),
            ('stock', 'Stock'),
            ('sample', 'Sample'),
            ('promo', 'Promo'),
            ('parent', 'Padre'),
            ('todo', 'Todo'),
            ], 'Gamma', required=True)
        }

    _defaults = {
        'status': lambda *x: 'todo',
        }    

class ProductProduct(orm.Model):
    """ Model name: ProductProduct
    """    
    _inherit = 'product.product'
    
    _columns = {
        'sortable': fields.boolean('Sortable'),
        'sortable_from': fields.date('Order from'),
        'sortable_to': fields.date('Order to'), # TODO used?
        }

    _defaults = {
        'sortable': lambda *x: True,
        }    
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
