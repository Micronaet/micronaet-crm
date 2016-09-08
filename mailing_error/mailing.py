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
import re
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
        # Utility:
        def clean(all_mail, mail_sent):
        ''' Remove not necessary mail
        '''
        res = []
        for email in all_mail:
            if email in mail_sent and email not in res:
                res.append(email)       
        return res        

        partner_pool = self.pool.get('res.partner')
        
        # Read base folder for mailing
        error_path = self.pool.get('res.company').get_base_local_folder(
            cr, uid, subfolder='mailing_error', context=context)
            
        # Read 2 subfolder for mailing:    
        mail_path = os.path.join(error_path, 'mail')
        csv_path = os.path.join(error_path, 'csv')
        
        # Create if not existe 2 subfolder paths
        os.system('mkdir -p %s' % mail_path)
        os.system('mkdir -p %s' % csv_path)
        
        # ---------------------------------------------------------------------
        # Read all mail in newsletter
        # ---------------------------------------------------------------------
        file_mail = os.path.join(csv_path, 'mail.csv')
        mail_sent = {}
        for address in open(file_mail, 'r'):
            address = address.strip().replace('\t', '')
            
            partner_ids = partner_pool.search(cr, uid, [
                ('email', '=', address),
                ], context=context)
            
            mail_sent[address] = partner_ids
            
        # ---------------------------------------------------------------------
        # Read all mail in error mail folder
        # ---------------------------------------------------------------------
        for mail_file in [f for f in os.listdir(mail_path)]:
            mail_fullfile = os.path.join(mail_path, mail_file)
            message = Parser().parse(open(mail_fullfile, 'r'))

            # Parse message parameters:
            subject = message['subject'].replace('\n','').replace('\r','')
            mail_to = message['to']
            mail_from = message['from']
            
             # Extract list of mail address in mail text file:
            all_mail = clean(
                re.findall(r'[\w\.-]+@[\w\.-]+', message.as_string()),
                mail_sent,
                )
            
            for mail_found in all_mail:
                partner_error = mail_sent.get(mail_found, False)                
                if partner_error:
                    partner_pool.write(cr, uid, partner_error, {
                        'address_error': True,
                        'address_error_text': 'From: %s\nto: %s\nSubject' % (
                            mail_from,
                            mail_to,
                            subject,
                            )
                        }, context=context)
                    # TODO delete file after update res.partner   
                    
                
            # Extract mail:    
            #try:    
            #   mail_address = mail.split('<')[1].split('>')[0]
            #except:
            #   mail_address = mail
            

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
