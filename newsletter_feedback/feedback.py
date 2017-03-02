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
import xlrd
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

class CrmNewsletterFeedbackCategory(orm.Model):
    """ Model name: CrmNewsletterFeedbackCategory
    """
    
    _name = 'crm.newsletter.feedback.category'
    _description = 'Newsletter feedback'

    
    _columns = {
        'name': fields.char('Category', size=64, required=True),
        'note': fields.text('Note'),    
        }

class CrmNewsletterFeedbackCategory(orm.Model):
    """ Model name: CrmNewsletterFeedbackCategory
    """
    
    _name = 'crm.newsletter.feedback.log'
    _description = 'Newsletter activity'
    _rec_name = 'date'
    _order = 'date'
    
    _columns = {
        'date': fields.date('Date', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'opt_out':fields.boolean('Opt out'),
        'category_id': fields.many2one(
            'crm.newsletter.feedback.category', 'Newsletter category', 
            help='Esit of newsletter'),
        'note': fields.text('Note'),    
        }

class ResCompany(orm.Model):
    """ Model name: Res Company
    """    
    _inherit = 'res.company'

    def import_newsletter_feedback_category(
            self, cr, uid, ids, context=None):
        ''' Import procedure for esit of last newsletter
        '''
        filename = '/home/administrator/photo/xls/newsletter/errori.xls'
        _logger.info('Start import procedure on file: %s' % filename)

        # Pool used:
        news_pool = self.pool.get('crm.newsletter.feedback.log')
        partner_pool = self.pool.get('res.partner')
        category_pool = self.pool.get('crm.newsletter.feedback.category')

        try:
            WB = xlrd.open_workbook(filename)
        except:
            raise osv.except_osv(
                _('Error XLSX'), 
                _('Cannot read XLS file: %s' % filename),
                )

        # Load current list:                
        WS = WB.sheet_by_index(0)

        error_db = {}
        i = 0
        import pdb; pdb.set_trace()
        for row in range(1, WS.nrows):
            i += 1
            # Read fields
            date = WS.cell(row, 0).value
            error = WS.cell(row, 1).value      
            email = WS.cell(row, 2).value
            active = WS.cell(row, 3).value or False # transform in boolean
            remove = WS.cell(row, 4).value or False # transform in boolean
            
            if not email or not date:
                _logger.error('Jump line: %s' % i)
                continue
                
            #date = datetime.strptime(date, '%d/%m/%Y')
            date = '%s-%s-%s' % (
                date[-4:],
                date[3:5],
                date[:2],
                )
            # Category management:
            if error and error not in error_db:          
                 error = error.lower()  
                 category_ids = category_pool.search(cr, uid, [
                     ('name', '=', error)], context=context)
                 if category_ids:
                     error_db[error] = category_ids[0]
                 else:
                     error_db[error] = category_pool.create(cr, uid, {
                         'name': error,
                         }, context=context)
                         
            # Partner management:
            partner_ids = partner_pool.search(cr, uid, [
                ('email', '=', email)], context=context)
            if not partner_ids:  
                _logger.error('Partner email not found: %s' % email)
                continue
                
            partner_id = partner_ids[0]
            category_id = error_db.get(error, False)
            
            # Create log in newsletter:
            news_id = news_pool.create(cr, uid, {
                'date': date,
                'opt_out': remove,
                'category_id': category_id,
                'partner_id': partner_id,
                }, context=context)
            
            # Update partner form:
            partner_pool.write(cr, uid, partner_id, {
                'news_feedback_id': category_id,
                'news_feedback_date': date,
                'news_opt_out': remove,                
                }, context=context)            
            _logger.info('News log updated: %s' % i)
        return True    


class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
    
    _columns = {
        'news_feedback_id': fields.many2one(
            'crm.newsletter.feedback.category', 'Newsletter category', 
            help='Esit of newsletter'),
        'news_feedback_date': fields.date('Feedback date'),    
        'news_opt_out':fields.boolean('Opt out'),
        'newsletter_ids': fields.one2many(
            'crm.newsletter.feedback.log', 'partner_id', 'Activity log'),
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
