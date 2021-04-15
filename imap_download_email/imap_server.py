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
import pdb
import sys
import logging
import openerp
import imaplib
import email
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from openerp.tools.translate import _
from openerp.tools import (DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)

_logger = logging.getLogger(__name__)


class ImapServerCategory(orm.Model):
    """ Model name: Category of IMAP server (for manage the import mode)
    """
    _name = 'imap.server.category'
    _description = 'IMAP Server category'
    _order = 'name'

    # TODO create overridable procedure for manage the type of import
    def import_read_email(self, cr, iud, context=None):
        """ Parse message list passed (ID: message)
        """
        # TODO To be overridden
        '''
        # Pool used:
        user_pool = self.pool.get('res.users')
        partner_pool = self.pool.get('res.partner')
        
        # Save message somewhere?
        for msg_id, message in new_mail.iteritems():
            record = {
                'To': False,
                'From': False,
                'Date': False,
                'Received': False,
                'Message-Id': False,
                'Subject': False,        
                }
                
            # Populate parameters:
            for (param, value) in message.items():
                if param in record:
                    record[param] = value

            # Extract user:
            email_address = (
                record.get('From') or '').split('<')[-1].split('>')[0]

            user_id = 1
            if email_address:
                # Search user:
                user_ids = user_pool.search(cr, uid, [
                    ('email', '=', email_address),
                    ], context=context)
                if user_ids:
                    user_id = user_ids[0]

            # Try to search partner from 'to address':
            to_address = (record.get('To') or '').split(', ')
            if to_address: # Take only the first                   
                email_address = \
                    to_address[0].split('<')[-1].split('>')[0]
                    
            if email_address:
                # Search user:
                partner_ids = partner_pool.search(cr, uid, [
                    ('email', '=', email_address),
                    ], context=context)
                if partner_ids:
                    partner_id = partner_ids[0]
                    if len(partner_ids) > 1:
                        _logger.warning(
                            '%s partner with address: %s' % (
                                len(partner_ids),
                                email_address,
                                ))

            _logger.info('Read mail: To: %s - From: %s - Subject: %s' % (
                record['To'],
                record['From'],
                record['Subject'],
                ))
            # -------------------------------------------------------------
            # Write on file:
            # -------------------------------------------------------------
            #eml_file = '%s.eml' % (os.path.join(
            #    store_folder, 
            #    str(doc_id),
            #    ))                
            #f_eml = open(eml_file, 'w')
            #f_eml.write(eml_string)
            # TODO remove file after confirm
            #f_eml.close()
            
            msg_ids.append(msg_id) # at the end (for delete message)'''
        return True  # msg_ids

    _columns = {
        'name': fields.char('IMAP category', size=80, required=True),
        'code': fields.char('Code', size=15, required=True),
        'note': fields.text('Note'),
        }

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Code must be unique!'),
        ]


class ImapServer(orm.Model):
    """ Model name: CRM Lead IMAP
    """
    _name = 'imap.server'
    _description = 'IMAP Server'
    _order = 'name'

    # -------------------------------------------------------------------------
    # Download IMAP server procedure:
    # -------------------------------------------------------------------------
    def force_import_email_document(self, cr, uid, ids, context=None):
        """ Force import passed server import all email in object
        """
        category_pool = self.pool.get('imap.server.category')
        mail_pool = self.pool.get('imap.server.mail')

        _logger.info('Start read # %s IMAP server' % (
            len(ids),
            ))

        # Read all server:
        for address in self.browse(cr, uid, ids, context=context):
            server = address.host  # '%s:%s' % (address.host, address.port)
            store_as_file = address.store_as_file
            authorized = [item.strip() for item in
                          address.authorized.split('|')]

            # -----------------------------------------------------------------
            # Read all email:
            # -----------------------------------------------------------------
            try:
                if_error = _('Error find imap server: %s' % server)
                if address.SSL:
                    mail = imaplib.IMAP4_SSL(server)  # SSL
                else:
                    mail = imaplib.IMAP4(server)  # No more used!

                server_mail = address.user
                if_error = _('Error login access user: %s' % server_mail)
                mail.login(server_mail, address.password)

                if_error = _('Error access start folder: %s' % address.folder)
                mail.select(address.folder)
            except:
                raise osv.except_osv(
                    _('IMAP server error:'),
                    if_error,
                    )

            esit, result = mail.search(None, 'ALL')
            tot = 0
            for msg_id in result[0].split():
                tot += 1

                # Read and parse result:
                esit, result = mail.fetch(msg_id, '(RFC822)')
                eml_string = result[0][1]
                message = email.message_from_string(eml_string)
                record = {
                    'To': False,
                    'From': False,
                    'Date': False,
                    'Received': False,
                    'Message-Id': False,
                    'Subject': False,
                    }

                # Populate parameters:
                for (param, value) in message.items():
                    if param in record:
                        record[param] = value
                address_from = record['From']
                address_to = record['To']
                odoo_data = {
                    'to': address_to,
                    'from': address_from,
                    'date': record['Date'],
                    'received': record['Received'],
                    'message_id': record['Message-Id'],
                    'subject': record['Subject'],
                    'state': 'draft',
                    'server_id': address.id,
                    }

                if server_mail in address_to:
                    _logger.warning('Jumped server mail is in CCN')
                    continue

                is_authorized = False
                for check_mail in authorized:
                    if check_mail in address_from:
                        is_authorized = True
                        break
                if not is_authorized:
                    _logger.warning('Jumped mail not authorized')
                    continue

                if not record['Message-Id']:
                    _logger.warning('No message ID for this email')
                if not store_as_file:
                    odoo_data['message'] = message

                mail_id = mail_pool.create(
                    cr, uid, odoo_data, context=context)

                # -------------------------------------------------------------
                # Write on file:
                # -------------------------------------------------------------
                if store_as_file:
                    fullname = mail_pool.get_fullname(
                        cr, uid, mail_id, context=context)
                    _logger.info('...Saving %s' % fullname)
                    f_eml = open(fullname, 'w')
                    f_eml.write(eml_string)
                    f_eml.close()

                # TODO manage commit roll back also in email
                mail.store(msg_id, '+FLAGS', '\\Deleted')
                _logger.info('Read mail: To: %s - From: %s - Subject: %s' % (
                    record['To'],
                    record['From'],
                    record['Subject'],
                    ))

            _logger.info('End read IMAP %s [tot msg: %s]' % (
                address.name,
                tot,
                ))

            # -----------------------------------------------------------------
            # Close operations:
            # -----------------------------------------------------------------
            # mail.expunge() # TODO clean trash bin
            mail.close()
            mail.logout()
            _logger.info('End read IMAP server')

            category_pool.import_read_email(cr, uid, context=context)
        return True

    # -------------------------------------------------------------------------
    # Scheduled operations for all IMAP Server:
    # -------------------------------------------------------------------------
    def schedule_import_email_document(
            self, cr, uid, category_code=False, context=None):
        """ Search schedule address and launch importation:
        """
        domain = [('is_active', '=', True)]
        if category_code:
            domain.append(('category_id.code', '=', category_code), )
        imap_ids = self.search(cr, uid, domain, context=context)

        if not imap_ids:
            return False
        return self.force_import_email_document(
            cr, uid, imap_ids, context=context)

    _columns = {
        'is_active': fields.boolean('Is active'),
        'name': fields.char('Email', size=80, required=True),
        'host': fields.char(
            'IMAP server', size=64, help='Email IMAP server', required=True),
        'port': fields.integer('Port', required=True),
        'user': fields.char(
            'Username', size=64, help='Email user', required=True),
        'password': fields.char(
            'Password', size=64, help='Email password', required=True),
        'folder': fields.char(
            'Folder', size=64, help='Email IMAP folder'),
        'SSL': fields.boolean('SSL'),
        'remove': fields.boolean('Remove after import'),
        'category_id': fields.many2one(
            'imap.server.category', 'Category', required=True),
        'comment': fields.text('Note'),
        'authorized': fields.text(
            'Autorizzati',
            help='Email separati da |, es.: '
                 'nome1@dominio1.it|nome2@dominio2.it'),

        # Store:
        'store_as_file': fields.boolean(
            'Salva come file',
            help='Salva la mail come file sul server e tiene un numero minimo'
                 ' di informazoni nel database'),
        'store_folder': fields.char(
            'Folder', size=64, help='Email IMAP folder'),
        }

    _defaults = {
        'is_active': lambda *a: True,
        'port': lambda *a: 993,
        'SSL': lambda *a: True,
        'folder': lambda *a: 'INBOX',
        }


class ImapServerMail(orm.Model):
    """ Model name: Mail imported
    """
    _name = 'imap.server.mail'
    _description = 'IMAP Server mail'
    _rec_name = 'subject'
    _order = 'date'

    def get_fullname(self, cr, uid, ids, context=None):
        """
        """
        mail_id = ids if type(ids) == int else ids[0]
        mail = self.browse(cr, uid, mail_id, context=context)
        server = mail.server_id
        filename = 'auto_%s_%s.eml' % (
            server.id,
            mail_id,
        )
        if server.store_as_file:
            store_folder = os.path.expanduser(
                os.path.join(server.store_folder, cr.dbname))
            os.system('mkdir -p %s' % store_folder)  # Create if no exist
            return os.path.join(store_folder, filename)
        return False

    def parse_address(self, address):
        """ Extract name and email from address
        """
        split_value = address.split('<')
        email = split_value[-1].split('>')[0]
        name = '<'.join(split_value[:-1]).strip().strip('"').strip()
        return name or email, email

    def workflow_confirm(self, cr, uid, ids, context=None):
        """ Confirm email and import in LEAD
        """
        partner_pool = self.pool.get('res.partner')
        mail_id = ids if type(ids) == int else ids[0]
        mail = self.browse(cr, uid, mail_id, context=context)
        name, email = self.parse_address(mail.to)

        partner_ids = partner_pool.search(cr, uid, [
            ('email', '=', email),
        ], context=context)
        if partner_ids:  # Link to first partner (master)
            new_partner = False
            partner = partner_pool.browse(
                cr, uid, partner_ids, context=context)[0]
            if partner.parent_id:
                partner_id = partner.parent_id.id
            else:
                partner_id = partner_ids[0]
        else:  # Create
            new_partner = True
            partner_id = partner_pool.create(cr, uid, {
                'name': name,
                'email': email,
                'is_company': True,
                'is_address': False,
            }, context=context)

        self.write(cr, uid, ids, {
            'partner_id': partner_id,
            'state': 'completed',
            'new_partner': new_partner,
        }, context=context)

    def download_file_eml(self, cr, uid, ids, context=None):
        """ Get filename if present and return attachment
        """
        if context is None:
            context = {
                'lang': 'it_IT',
                }

        mail_id = ids[0]

        # Pool used:
        attachment_pool = self.pool.get('ir.attachment')

        fullname = self.get_fullname(
            cr, uid, mail_id, context=context)

        try:
            b64 = open(fullname, 'rb').read().encode('base64')
        except:
            _logger.error(_('Cannot return file: %s') % fullname)
            raise osv.except_osv(
                _('Report error'),
                _('Cannot return file: %s') % fullname,
                )

        # Clean previous attachement:
        attachment_ids = attachment_pool.search(cr, uid, [
            ('name', '=', 'Email'),
            ('datas_fname', '=', 'odoo_email.eml'),
        ], context=context)
        if attachment_ids:
            try:
                attachment_pool.unlink(
                    cr, uid, attachment_ids, context=context)
            except:
                _logger.error('Cannot delete previous attachment returned')

        attachment_id = attachment_pool.create(cr, uid, {
            'name': 'Email',
            'datas_fname': 'odoo_email.eml',
            'type': 'binary',
            'datas': b64,
            'partner_id': 1,
            'res_model': 'res.partner',
            'res_id': 1,
            }, context=context)

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/binary/saveas?model=ir.attachment&field=datas&'
                   'filename_field=datas_fname&id=%s' % attachment_id,
            'target': 'self',
            }

    _columns = {
        'message_id': fields.char('ID', size=80),
        'to': fields.char('To', size=100),
        'from': fields.char('From', size=100),
        'received': fields.char('Received', size=100),
        'subject': fields.char('Subject', size=100),
        'date': fields.char('Date', size=30),
        'message': fields.text('Message'),
        'new_partner': fields.boolean('Partner nuovo'),
        'server_id': fields.many2one('imap.server', 'Server'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('completed', 'Completed'),  # Elaborated
            ], 'State'),
        }

    _defaults = {
        'state': lambda *x: 'draft',
        }


# class ResPartner(orm.Model):
#    """ Model name: Partner
#    """
#    _inherit = 'res.partner'
