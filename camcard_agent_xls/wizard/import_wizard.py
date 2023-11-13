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
import pdb
import sys
import logging
import xlrd
import openerp
import openerp.netsvc as netsvc
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)
import codecs

_logger = logging.getLogger(__name__)


class ResPartnerCamcardImportWizard(osv.osv_memory):
    """ Wizard import camcard contact
    """
    _name = 'res.partner.camcard.import.xls.wizard'

    _columns = {
        # 'type_id': fields.many2one('crm.tracking.campaign', 'Campaign'),
        'mode': fields.selection([
            ('camcard', 'Camcard'),
            ('xls', 'XLS (name, email)'),
            ('custom', 'File personalizzato XLSX'),
            ], 'Mode', required=True),
        }

    _defaults = {
        # Default value:
        'mode': lambda *x: 'custom',
        }

    # Utility:
    def name_email_import_xls(self, cr, uid, sheet, context=None):
        """ Import name and email with same wizard
            Mode > Simple file (A)

        """
        # Pool used:
        partner_pool = self.pool.get('res.partner')

        start_row = 1  # no header

        for row in range(start_row, sheet.nrows):
            # Read fields:
            name = sheet.cell(row, 0).value
            email = sheet.cell(row, 1).value

            if not name:
                _logger.error('End import, no name: %s' % row)
                break

            if not email:
                _logger.error('Yump mail jump line: %s' % row)
                continue

            data = {
                'is_company': True,
                'customer': False,
                'supplier': False,
                'user_id': uid,
                'name': name,
                'email': email.lower(),
                # 'newsletter_category_id': newsletter_category_id,
                # 'type_id': type_id, # TODO
                }

            partner_ids = partner_pool.search(cr, uid, [
                ('email', '=', email),
                ], context=context)
            if partner_ids:
                # partner_pool.write(
                # cr, uid, partner_ids, data, context=context)
                _logger.warning('%s Mail yet present: %s' % (row, email))
            else:
                partner_pool.create(cr, uid, data, context=context)
                _logger.info('%s Create %s' % (row, name))
        return True

    def crm_contact_custom_import_xls(
            self, cr, uid, path, sheet, context=None):
        """ Contact custom file import procedure
            Mode > Contact custom file (B)
        """
        # Pool used:
        partner_pool = self.pool.get('res.partner')
        newsletter_pool = self.pool.get('crm.newsletter.category')
        campaign_pool = self.pool.get('crm.tracking.campaign')
        country_pool = self.pool.get('res.country')
        state_pool = self.pool.get('res.country.state')
        model_pool = self.pool.get('ir.model.data')

        log_file = {
            'error': codecs.open(
                os.path.join(path, 'contact.error_log.csv'), 'w', 'utf-8'),
            'warning': codecs.open(
                os.path.join(path, 'contact.warning_log.csv'), 'w', 'utf-8'),
            }

        # =====================================================================
        #                    Setup used external tables:
        # =====================================================================
        # 1. Setup newsletter:
        newsletter_db = {}
        newsletter_ids = newsletter_pool.search(cr, uid, [], context=context)
        for newsletter in newsletter_pool.browse(
                cr, uid, newsletter_ids, context=context):
            name = newsletter.name.upper()
            if name not in newsletter_db:
                newsletter_db[name] = newsletter.id

        # 2. Setup country:
        country_db = {
            'name': {},
            'code': {},
        }
        country_ids = country_pool.search(cr, uid, [], context=context)
        for country in country_pool.browse(
                cr, uid, country_ids, context=context):
            name = country.name.upper()
            code = (country.code or '').upper()
            if name not in country_db['name']:
                country_db['name'][name] = country.id
            if code not in country_db['code']:
                country_db['code'][code] = country.id

        # 3. Setup state:
        state_db = {
            'name': {},
            'code': {},
            }
        state_ids = state_pool.search(cr, uid, [], context=context)
        for state in state_pool.browse(
                cr, uid, state_ids, context=context):
            name = state.name.upper()
            code = state.code.upper()
            if name not in state_db['name']:
                state_db['name'][name] = state.id
            if code not in state_db['code']:
                state_db['code'][code] = state.id

        # 4. Setup campaign:
        campaign_db = {}
        campaign_ids = campaign_pool.search(cr, uid, [], context=context)
        for campaign in campaign_pool.browse(
                cr, uid, campaign_ids, context=context):
            name = campaign.name.upper()
            if name not in campaign_db:
                campaign_db[name] = campaign.id

        # =====================================================================
        #                          Read XLSX Sheet
        # =====================================================================
        pdb.set_trace()
        start_row = 1  # no header
        selected_ids = []
        for row in range(start_row, sheet.nrows):
            is_company = (sheet.cell(row, 0).value or '').strip() != ''
            name = sheet.cell(row, 1).value  # Company
            first_name = sheet.cell(row, 2).value
            last_name = sheet.cell(row, 3).value
            # title = sheet.cell(row, 11).value

            street = sheet.cell(row, 4).value
            city = sheet.cell(row, 5).value
            state = (sheet.cell(row, 6).value or '').upper()  # foreign
            zipcode = sheet.cell(row, 7).value
            country = (sheet.cell(row, 8).value or '').upper()  # foreign

            website = sheet.cell(row, 9).value
            phone = sheet.cell(row, 10).value
            mobile = sheet.cell(row, 11).value
            email = sheet.cell(row, 12).value
            # fax = sheet.cell(row, 21).value

            group = (sheet.cell(row, 13).value or '').upper()  # Newsletter
            campaign = (sheet.cell(row, 14).value or '').upper()  # Campagne

            note = sheet.cell(row, 15).value
            # birthday = sheet.cell(row, 31).value

            # -----------------------------------------------------------------
            # Foreign keys:
            # -----------------------------------------------------------------
            # Newsletter ID
            newsletter_category_id = newsletter_db.get(group, '')

            # State ID
            state_id = state_db['code'].get(state, '')
            if not state_id:
                state_id = state_db['name'].get(state, '')

            # Country ID
            country_id = country_db['code'].get(country, '')
            if not country_id:
                country_id = country_db['name'].get(country, '')

            # Campaign ID
            campaign_id = campaign_db.get(campaign, '')

            # -----------------------------------------------------------------
            #                            Check error:
            # -----------------------------------------------------------------
            error_text = warning_text = u''

            # Mandatory company or contact reference
            if not name and not first_name and not last_name:
                error_text += u'[Non trovato nome o Società: %s] ' % (row + 1)

            # Campaign if present check ID:
            if campaign and not campaign_id:
                error_text += u'[Campagna non trovata: %s] ' % campaign

            # Newsletter if present check ID:
            if group and not newsletter_category_id:
                error_text += u'[Newsletter non trovata: %s] ' % group

            # State if present check ID:
            if state and not state_id:
                error_text += u'[Provincia non trovata: %s] ' % state

            # Country if present check ID:
            if country and not country_id:
                error_text += u'[Nazione non trovata: %s] ' % country

            # -----------------------------------------------------------------
            # Partner creation:
            # -----------------------------------------------------------------
            contact_name = u'%s %s' % (first_name, last_name)
            partner_name = name or contact_name
            partner_data = {
                'is_company': is_company,
                'user_id': uid,

                'name': partner_name,

                'street': street,
                'city': city,
                'state_id': state_id,
                'zipcode': zipcode,
                'country_id': country_id,

                'website': website,
                'phone': phone,
                'mobile': mobile,
                'email': email,
                # 'fax': fax,

                'newsletter_category_id': newsletter_category_id,
                'type_id': campaign_id,
                'mexal_note': note,
                }

            partner_ids = partner_pool.search(cr, uid, [
                ('name', '=', partner_name),
            ], context=context)

            if partner_ids:
                # todo remove some fields?:
                # del(partner_data['newsletter_category_id'])
                # del(partner_data['type_id'])

                partner_pool.write(
                    cr, uid, partner_ids, partner_data, context=context)
                partner_id = partner_ids[0]
                _logger.info(u'%s Update %s' % (row, name))
                warning_text += u'[Partner già presente %s ID %s ' \
                                u'(aggiornato)] ' % (
                                    name or contact_name, partner_id
                                    )
                partner_id = partner_ids[0]
            else:
                partner_id = partner_pool.create(
                    cr, uid, partner_data, context=context)
                _logger.info(u'%s Create %s' % (row, name))
            selected_ids.append(partner_id)

            # -----------------------------------------------------------------
            # Contact setup:
            # -----------------------------------------------------------------
            if name and (first_name or last_name):
                # Create also contact
                contact_data = {
                    'name': contact_name,
                    'parent_id': partner_id,
                    }

                contact_ids = partner_pool.search(cr, uid, [
                    ('parent_id', '=', partner_id),
                    ('name', '=', contact_name),
                ], context=context)

                if contact_ids:
                    partner_pool.write(
                        cr, uid, contact_ids, contact_data, context=context)
                    _logger.info('%s Update contact %s' % (row, contact_name))
                    warning_text += u'[Contatto già presente %s ID %s ' \
                                    u'(aggiornato)] ' % (
                                        contact_name, contact_ids[0]
                                        )
                else:
                    partner_pool.create(
                        cr, uid, contact_data, context=context)
                    _logger.info('%s Create contact %s' % (row, contact_name))

            # -----------------------------------------------------------------
            # Manage error log:
            # -----------------------------------------------------------------
            if error_text:
                log_file['error'].write(u'%s. %s\n' % (
                    row, error_text,
                ))
                log_file['error'].flush()

            if warning_text:
                log_file['warning'].write(u'%s. %s\n' % (
                    row, warning_text,
                ))
                log_file['warning'].flush()

        # Return view with selected partner:
        tree_id = model_pool.get_object_reference(
            cr, uid,
            'crm_newsletter_category', 'view_res_partner_newsletter_tree'
        )[1]
        form_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner importati'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': False,
            'res_model': 'res.partner',
            'view_id': tree_id,
            'views': [
                (tree_id, 'tree'),
                (form_id, 'form'),
            ],
            'domain': [('id', 'in', selected_ids)],
            'context': context,
            'target': 'current',  # 'new'
            'nodestroy': False,
        }

    def camcard_import_xls(self, cr, uid, ids, context=None):
        """ Camcard import procedure
        """
        assert len(ids) == 1, 'Only one wizard record!'

        wiz_proxy = self.browse(cr, uid, ids, context=context)[0]
        mode = wiz_proxy.mode
        # type_id = wiz_proxy.type_id, # TODO

        # Pool used:
        partner_pool = self.pool.get('res.partner')
        newsletter_pool = self.pool.get('crm.newsletter.category')

        # Read base folder for mailing
        camcard_path = self.pool.get('res.company').get_base_local_folder(
            cr, uid, subfolder='camcard', context=context)
        camcard_path = os.path.expanduser(camcard_path)

        # ---------------------------------------------------------------------
        # Read XLS camcard file sheet:
        # ---------------------------------------------------------------------
        filename = os.path.join(camcard_path, '%s.xlsx' % mode)
        try:
            book = xlrd.open_workbook(filename)
            _logger.info('Read XLSX file: %s' % filename)
        except:
            raise osv.except_osv(
                _('Error:'),
                _('No camcard XLSX file: %s') % filename,
                )
        sheet = book.sheet_by_index(0)

        # ---------------------------------------------------------------------
        # A Mode > xls:
        # ---------------------------------------------------------------------
        if mode == 'xls':
            return self.name_email_import_xls(
                cr, uid, sheet, context=context)

        # ---------------------------------------------------------------------
        # B Mode > Custom:
        # ---------------------------------------------------------------------
        elif mode == 'custom':
            return self.crm_contact_custom_import_xls(
                cr, uid, camcard_path, sheet, context=context)

        # ---------------------------------------------------------------------
        # C Mode > camcard:
        # ---------------------------------------------------------------------
        # Read newsletter elements:
        newsletter_db = {}
        newsletter_ids = newsletter_pool.search(cr, uid, [], context=context)
        for newsletter in newsletter_pool.browse(
                cr, uid, newsletter_ids, context=context):
            if newsletter.name not in newsletter_db:
                newsletter_db[newsletter.name] = newsletter.id

        # ---------------------------------------------------------------------
        # Read all mail in error mail folder
        # ---------------------------------------------------------------------
        start_row = 1  # no header
        max_row = 10000
        for row in range(1, max_row):
            # Read fields:
            try:  # Test if last line
                create = sheet.cell(row, 0).value
            except:
                break  # no more row

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
                # 'type_id': type_id, # TODO

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
        return True
