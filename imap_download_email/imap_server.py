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
        # now = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # Read all server:
        for address in self.browse(cr, uid, ids, context=context):
            server = address.host  # '%s:%s' % (address.host, address.port)
            if address.store_as_file:
                store_folder = os.path.expanduser(
                    os.path.join(address.store_folder, cr.dbname))
                os.system('mkdir -p %s' % store_folder)  # Create if no exist
            else:
                store_folder = False

            # -----------------------------------------------------------------
            # Read all email:
            # -----------------------------------------------------------------
            try:
                if_error = _('Error find imap server: %s' % server)
                if address.SSL:
                    mail = imaplib.IMAP4_SSL(server)  # SSL
                else:
                    mail = imaplib.IMAP4(server)  # No more used!

                if_error = _('Error login access user: %s' % address.user)
                mail.login(address.user, address.password)

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

                odoo_data = {
                    'to': record['To'],
                    'from': record['From'],
                    'date': record['Date'],
                    'received': record['Received'],
                    'message_id': record['Message-Id'],
                    'subject': record['Subject'],
                    'state': 'draft',
                    'server_id': address.id,
                    }
                if not record['Message-Id']:
                    _logger.warning('No message ID for this email')
                if not store_folder:
                    odoo_data['message'] = message

                mail_id = mail_pool.create(
                    cr, uid, odoo_data, context=context)

                # -------------------------------------------------------------
                # Write on file:
                # -------------------------------------------------------------
                if store_folder:
                    filename = 'auto_%s_%s.eml' % (
                        address.id,
                        mail_id,
                    )
                    fullname = os.path.join(store_folder, filename)
                    _logger.info('Saving %s ...' % fullname)
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

    _columns = {
        'message_id': fields.char('ID', size=80),
        'to': fields.char('To', size=100),
        'from': fields.char('From', size=100),
        'received': fields.char('Received', size=100),
        'subject': fields.char('Subject', size=100),
        'date': fields.char('Date', size=30),
        'message': fields.text('Message'),
        'server_id': fields.many2one('imap.server', 'Server'),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('completed', 'Completed'),  # Elaborated
            ], 'State'),
        }

    _defaults = {
        'state': lambda *x: 'draft',
        }
