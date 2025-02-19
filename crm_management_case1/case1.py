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

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """
    _inherit = 'res.partner'

    def scheduled_autoassign_crm_level(self, cr, uid, context=None):
        """ Auto-assign partner CRM category
        """
        sale_pool = self.pool.get('sale.order')
        now = datetime.now()
        year_1 = (now - timedelta(days=365)).strftime(
            DEFAULT_SERVER_DATE_FORMAT)
        year_2 = (now - timedelta(days=365 * 2)).strftime(
            DEFAULT_SERVER_DATE_FORMAT)

        partner_ids = self.search(cr, uid, [], context=context)
        assign_data = {
            1: [],
            2: [],
            3: [],
            4: [],
            5: [],
        }
        total = len(partner_ids)
        _logger.info('Partner found: {}'.format(total))
        counter = 0
        for partner in self.browse(cr, uid, partner_ids, context=context):
            counter += 1
            if not counter % 50:
                _logger.info('Reading {} / {} partner'.format(
                    counter, total))

            # Account Partner code:
            account_partner = any((
                partner.sql_customer_code,
                partner.sql_supplier_code,
                partner.sql_destination_code,
            ))

            # Check also parent partner:
            parent = partner.parent_id
            if not account_partner and parent:
                account_partner = any((
                    parent.sql_customer_code,
                    parent.sql_supplier_code,
                    parent.sql_destination_code,
                    ))

            # -----------------------------------------------------------------
            # Account partner: Sales
            # -----------------------------------------------------------------
            if account_partner:
                # Check last order:
                sale_ids = sale_pool.search(cr, uid, [
                    ('partner_id', '=', partner.id),
                ], order='date_order desc', limit=1, context=context)
                if sale_ids:
                    order = sale_pool.browse(cr, uid, sale_ids, context=context)[0]
                    order_date = order.date_order
                    if order_date <= year_1:
                        # Regular
                        assign_data[1].append(partner.id)
                    elif order_date >= year_2:
                        # Occasional
                        assign_data[2].append(partner.id)
                    else: # < year_2
                        # Inactive
                        assign_data[3].append(partner.id)
            else:
                # -------------------------------------------------------------
                # Lead partner: Mail Chimp
                # -------------------------------------------------------------
                # Lead
                assign_data[4].append(partner.id)

                # Contact
                # todo Contact: assign_data[partner.id] = 4

        _logger.info('Update partner operation')
        for crm_level in assign_data:
            _logger.info('Update level: {}'.format(crm_level))
            selected_ids = assign_data[crm_level]
            self.write(cr, uid ,selected_ids, {
                'crm_level': crm_level,
            }, context=context)
        _logger.info('End Update partner operation')
        return True

    def open_original_form_partner(self, cr, uid, ids, context=None):
        """
        """
        model_pool = self.pool.get('ir.model.data')
        tree_id = model_pool.get_object_reference(
            cr, uid, 
            'crm_management_case1', 'view_res_partner_crm_insert_tree'
            )[1]
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': ids[0],
            'res_model': 'res.partner',
            #'view_id': view_id, # False
            'views': [
                (False, 'form'),
                (tree_id, 'tree'),
                ],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }
    
    _columns = {
        'crm_level': fields.selection([
            (1, 'Regular client'),  # OC < 1 year
            (2, 'Occasional client'),  # 1 year < OC < 2 year
            (3, 'Inactive client'),  # OC < 2 year

            # todo Integrate with MailChimp:
            (4, 'Lead'),  # No buy, but comunication
            (5, 'Contact'),  # No buy, no comunication
            ], 'CRM')
        }
    
    _defaults = {
        # 'crm_level': lambda *x: 1,
        }