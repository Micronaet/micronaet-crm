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
import re
from os import listdir
from os.path import isfile, join
from email.parser import Parser


_logger = logging.getLogger(__name__)

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.company'

    def import_mail_problem_address(self, cr, uid, ids, context=None):
        ''' Check error message folder and parse name for check error in 
            partner mail address
        '''
        partner_pool = self.pool.get('res.partner')
        
        error_path = self.pool.get('res.company').get_base_local_folder(
            cr, uid, subfolder='mailing_error', context=context)

        # ---------------------------------------------------------------------
        # Read all mail in newsletter
        # ---------------------------------------------------------------------
        mail_sent = []
    for address in open('/home/anna/Scrivania/Mail/mail.csv', 'r'):
        mail_sent.append(address.strip().replace('\t', ''))
    def clean(all_mail):
    ''' Remove not necessary mail
    '''
    res = []
    for email in all_mail:
        if email in mail_sent and email not in res:
            res.append(email)       
    return res        
        # ---------------------------------------------------------------------
        # Read all mail in error mail folder
    for mail_file in [f for f in listdir(error_path)]:
        mail_fullfile = join(error_path, mail_file)
        message = Parser().parse(open(mail_fullfile, 'r'))
        state = 'Not delivered'
        
         # Extract list of mail:
        all_mail = clean(re.findall(r'[\w\.-]+@[\w\.-]+', message.as_string()))
    
         # Extract mail:    
    try:    
       mail_address = mail.split("<")[1].split(">")[0]
    except:
       mail_address = mail
    subject = message['subject'].replace('\n','').replace('\r','')
        
        # ---------------------------------------------------------------------
        # Search customer mail for mark problem
        # ---------------------------------------------------------------------
        
        # ---------------------------------------------------------------------
        # Get list of partner problems and return custom tree list
        # ---------------------------------------------------------------------
        model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference(cr, uid, 
            'mailing_error', 'view_res_partner_mailing_error')[1]
        
        domain = []    
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Mailing error'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'res.partner',
            'view_id': view_id, # False
            'views': [(view_id, 'tree'), (False, 'form')],
            'domain': domain,
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }            

class ResPartner(orm.Model):
    """ Model name: ResPartner
    """    
    _inherit = 'res.partner'
            
    _columns = {
        'address_error': fields.boolean('Address error'),
        'address_error_text': fields.text(
            'Address error text', 
            help='Text for email error'),
        }
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
