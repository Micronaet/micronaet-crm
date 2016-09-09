# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Abstract (http://www.abstract.it)
#    Copyright (C) 2014 Agile Business Group (http://www.agilebg.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import os
import sys
import logging
import openerp
import base64
import xlrd
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp import models, api, fields
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.exceptions import Warning
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp import SUPERUSER_ID#, api
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT, 
    DEFAULT_SERVER_DATETIME_FORMAT, 
    DATETIME_FORMATS_MAP, 
    float_compare)

_logger = logging.getLogger(__name__)


class ResPartnerCcamcardImportWizard(models.TransientModel):
    ''' Wizard import camcard contact 
    '''
    _name = 'res.partner.camcard.import.wizard'

    _columns = {
        #'type_id': fields.many2one('crm.tracking.campaign', 'Campaign'),
        }

    def camcard_import_xls(self, cr, uid, ids, context=None):
        ''' Camcard import procedure
        '''
        assert len(ids) == 1, 'Only one wizard record!'        
        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        # type_id = wiz_proxy.type_id, # TODO

        # Pool used:
        partner_pool = self.pool.get('res.partner')
        newsletter_pool = self.pool.get('crm.newsletter.category')
        
        # Read newsletter elements:
        newsletter_db = {}
        newsletter_ids = newsletter_pool.search(cr, uid, [], context=context)
        for newsletter in newsletter_pool.browse(
                cr, uid, newsletter_ids, context=context):
            if newsletter.name not in newsletter_db:
                newsletter_db[newsletter.name] = newsletter.id
        
        # Read base folder for mailing
        camcard_path = self.pool.get('res.company').get_base_local_folder(
            cr, uid, subfolder='camcard', context=context)
        camcard_path = os.path.expanduser(camcard_path)  
            
        # ---------------------------------------------------------------------
        # Read XLS camcard file sheet:
        # ---------------------------------------------------------------------
        filename = os.path.join(camcard_path, 'camcard.xlsx')
        try:
            book = xlrd.open_workbook(filename)
        except:
            raise osv.except_osv(
                _('Error:'), 
                _('No camcard XLSX file: %s') % filename,
                )
        sheet = book.sheet_by_index(0)

        # ---------------------------------------------------------------------
        # Read all mail in error mail folder
        # ---------------------------------------------------------------------
        start_row = 1 # no header
        max_row = 10000
        for row in range(1, max_row):            
            # Read fields:
            try: # Test if last line
                create = sheet.cell(row, 0).value                
            except:    
                break # no more row
            
            name = sheet.cell(row, 1).value
            first_name = sheet.cell(row, 2).value
            last_name = sheet.cell(row, 3).value
            industry = sheet.cell(row, 4).value
            location = sheet.cell(row, 5).value
            company1 = sheet.cell(row, 6).value
            dept1 = sheet.cell(row, 7).value
            title1 = sheet.cell(row, 8).value
            company2 = sheet.cell(row, 9).value
            dept2 = sheet.cell(row, 10).value
            title2 = sheet.cell(row, 11).value
            companyO = sheet.cell(row, 12).value
            deptO = sheet.cell(row, 13).value
            titleO = sheet.cell(row, 14).value
            mobile1 = sheet.cell(row, 15).value
            mobile2 = sheet.cell(row, 16).value
            mobileO = sheet.cell(row, 17).value
            phone1 = sheet.cell(row, 18).value
            phone2 = sheet.cell(row, 19).value
            phoneO = sheet.cell(row, 20).value
            fax1 = sheet.cell(row, 21).value
            fax2 = sheet.cell(row, 22).value
            faxO = sheet.cell(row, 23).value
            email1 = sheet.cell(row, 24).value
            email2 = sheet.cell(row, 25).value
            emailO = sheet.cell(row, 26).value
            address1 = sheet.cell(row, 27).value
            address2 = sheet.cell(row, 28).value
            addressO = sheet.cell(row, 29).value
            link = sheet.cell(row, 30).value
            birthday = sheet.cell(row, 31).value
            anniversary = sheet.cell(row, 32).value
            group = sheet.cell(row, 33).value # newsletter
            nickname = sheet.cell(row, 34).value
            note = sheet.cell(row, 35).value
            
            key = '%s-%s-%s-%s' % (name, company1, company2, companyO)
            
            # Get newsletter_category_id ID
            if group not in newsletter_db:
                newsletter_db[group] = newsletter_pool.create(cr, uid, {
                    'name': group,
                    }, context=context)
                    
            newsletter_category_id = newsletter_db[group]
                
            camcard_text = '''
                '<b>Name:</b> %s (%s %s)</br>
                '<b>Industry:</b> %s <b>Location:</b> %s</br>
                '<b>Company 1:</b> %s <b>Dep.:</b> %s <b>Title:</b> %s</br>
                '<b>Company 2:</b> %s <b>Dep.:</b> %s <b>Title:</b> %s</br>
                '<b>Company Other:</b> %s <b>Dep.:</b> %s <b>Title:</b> %s</br>
                '<b>Mobile:</b> %s   %s   %s</br>
                '<b>Phone:</b> %s   %s   %s</br>
                '<b>Fax:</b> %s   %s   %s</br>
                '<b>Email:</b> %s   %s   %s</br>
                '<b>Address:</b> %s   %s   %s</br>
                '<b>Link:</b> %s <b>Nickname:</b> %s</br>
                '<b>Birthday:</b> %s <b>Anniversary:</b> %s</br>
                '<b>Group:</b> %s</br>
                '<b>Note:</b> %s</br>''' % (
                    name, first_name, last_name,
                    industry, location,
                    company1, dept1, title1,
                    company2, dept2, title2,
                    companyO, deptO, titleO,
                    mobile1, mobile2, mobileO,
                    phone1, phone2, phoneO, 
                    fax1, fax2, faxO,
                    email1, email2, emailO,
                    address1, address2, addressO,
                    link, nickname,
                    birthday, anniversary,
                    group,
                    note,
                    )
            data = {
                'is_company': True,
                'user_id': uid,
                'name': '%s (%s)' % (name, (company1 or company2 or companyO)),
                'mobile': mobile1 or mobile2 or mobileO,
                'phone': phone1 or phone2 or phoneO,
                'fax': fax1 or fax2 or faxO,
                'email': email1 or email2 or emailO,
                'street': address1 or address2 or addressO,                
                'comment': camcard_text,
                'newsletter_category_id': newsletter_category_id,
                #'type_id': type_id, # TODO
                
                'camcard_key': key,
                'camcard': True,
                'camcard_date': create,
                'camcard_text': camcard_text,
                }

            partner_ids = partner_pool.search(cr, uid, [
                ('camcard_key', '=', key)], context=context)    
            if partner_ids:    
                partner_pool.write(cr, uid, partner_ids, data, context=context)
                _logger.info('%s Update %s' % (row, key))
            else:                
                partner_pool.create(cr, uid, data, context=context)
                _logger.info('%s Create %s' % (row, key))
        
        '''model_pool = self.pool.get('ir.model.data')
        view_id = model_pool.get_object_reference('module_name', 'view_res_partner_newsletter_tree')[1]
    
        return {
            'type': 'ir.actions.act_window',
            'name': _('Result for view_name'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            #'res_id': 1,
            'res_model': 'model.name',
            'view_id': view_id, # False
            'views': [(False, 'tree'), (False, 'form')],
            'domain': [],
            'context': context,
            'target': 'current', # 'new'
            'nodestroy': False,
            }'''
        return True

