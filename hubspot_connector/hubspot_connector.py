#!/usr/bin/python
# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP)
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<https://micronaet.com>)
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
import pdb
import re
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
import requests

_logger = logging.getLogger(__name__)


class HubspotConnector(orm.Model):
    """ Hubspot Connector
    """
    _name = 'hubspot.connector'
    _description = 'Hubspot Connector'
    _order = 'name'

    # Utility:
    def get_company_hubspot_connector(self, cr, uid, context=None):
        """ Search current connection when called from another object
        """
        hubspot_ids = self.search(cr, uid, [], context=context)   # Search company_id

        if not hubspot_ids:
            raise osv.except_osv(
                _(u'Errore:'),
                _(u'Non trovata configurazione Hubspot'),
            )
        return hubspot_ids[0]

    def prepare_hubspot_data(self, partner, mode='contact', category_map=None):
        """ Create dict for REST Call
        """
        if category_map is None:
            category_map = {}

        # todo ID ODOO
        if mode == 'contacts':
            return {
                    # "associations": [
                    #    {
                    #        "to": {"id": "{}".format(partner.id)},
                    #        "types": [
                    #            {
                    #                "associationCategory": "HUBSPOT_DEFINED",
                    #                "associationTypeId": 123
                    #            }
                    #        ]
                    #    }
                    # ],
                    "properties": {
                        # Company:
                        # 'lifecyclestage':
                        # 'name': partner.name,

                        # Contact:
                        'firstname': partner.name or '',
                        'address': partner.street or '',
                        'city': partner.city or '',
                        'provincia': partner.state_id.code or '',
                        'regione': partner.state_id.region_id.name or '',
                        'country': partner.country_id.code or '',
                        'zip': partner.zip or '',
                        'email': partner.email or '',

                        # 'state',
                        # 'hs_object_id' 'firstname' 'lastname' 'phone' 'mobilephone' 'Fax' 'email' 'email_pec'
                        # 'website' 'city' 'state'
                    }
                }
        else:  # companies
            # Extract domain from email:
            email = partner.email or ''
            if email:
                domain = email.split('@')[-1].lower().strip().replace(' ', '').replace(',', '.')
                if domain in ('gmail.com', 'microsoft.com', 'ymail.com', 'libero.it', 'tim.it', 'mac.com'):
                    domain = ''
            else:
                domain = ''
            return {
                    "properties": {
                        'lifecyclestage': category_map.get(partner.newsletter_category_id.id, ''),
                        'domain': domain,
                        # Company:
                        'name': partner.name or '',
                        'address': partner.street or '',
                        'city': partner.city or '',
                        'provincia': partner.state_id.code or '',
                        'regione': partner.state_id.region_id.name or '',
                        'country': partner.country_id.code or '',
                        'zip': partner.zip or '',
                        # 'email': partner.email or '',
                    }
                }

    def button_delete_contact(self, cr, uid, ids, context=None):
        """ Update contacts on Hubspot:
        """
        call = "gdpr-delete"
        timeout = 15

        # Partner used:
        partner_pool = self.pool.get('res.partner')

        if context is None:
            context = {}
        unlink_partner_id = context.get('unlink_partner_id')

        if not unlink_partner_id:
            raise osv.except_osv(
                _(u'Errore:'),
                _(u'Partner ID non trovato, non è possibile cancellare'),
            )

        # --------------------------------------------------------------------------------------------------------------
        # Open Partner:
        # --------------------------------------------------------------------------------------------------------------
        partner = partner_pool.browse(cr, uid, unlink_partner_id, context=context)
        if partner.is_company:
             mode = 'companies'
             field_name = 'hubspot_companies_ref'
             hubspot_ref = partner.hubspot_companies_ref
        else:
            mode = 'contacts'
            field_name = 'hubspot_contacts_ref'
            hubspot_ref = partner.hubspot_contacts_ref

        if not hubspot_ref:  # UPDATE
            raise osv.except_osv(
                _(u'Errore:'),
                _(u'Non trovato ID Hubspot, non è possibile cancellare'),
            )

        # --------------------------------------------------------------------------------------------------------------
        # Delete hubspot partner:
        # --------------------------------------------------------------------------------------------------------------
        connector = self.browse(cr, uid, ids, context=context)[0]
        endpoint = connector.endpoint
        token = connector.token
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json"
        }

        # Generate Payload:
        payload = {
            'objectId': "{}".format(hubspot_ref),
            # "idProperty": "<string>"  # todo ID ODOO?
        }

        url = "{}/{}/{}".format(endpoint, mode, call)
        _logger.info('Calling: {}'.format(url))
        response = requests.post(
            url=url, json=payload, headers=headers, timeout=timeout,
        )

        if response.ok:
            _logger.info(u"Partner ODOO {} aggiornato correttamente su HubSpot (ID: {})".format(
                partner.id, hubspot_ref))
            partner_pool.write(cr, uid, [partner.id], {
                field_name: False,  # Clean Hubspot Reference
            }, context=context)
        else:
            raise osv.except_osv(
                u'Errore:',
                u"Errore agg. HS ID {} (payload: {}):\n\n{}".format(
                    payload, hubspot_ref, response.text))

        return True

    def button_update_contact(self, cr, uid, ids, context=None):
        """ Update contacts on Hubspot:
            force_domain: Used to update single partner or all category of partner
        """
        # --------------------------------------------------------------------------------------------------------------
        # Parameter:
        # --------------------------------------------------------------------------------------------------------------
        timeout = 15
        no_raise = False

        partner_pool = self.pool.get('res.partner')
        category_pool = self.pool.get('crm.newsletter.category.hubspot')

        connector = self.browse(cr, uid, ids, context=context)[0]
        if context is None:
            context = {}

        # --------------------------------------------------------------------------------------------------------------
        # Load category:
        # --------------------------------------------------------------------------------------------------------------
        _logger.info('Loading hubspot CRM categories')
        category_map = {}
        category_ids = category_pool.search(cr, uid, [
            ('hubspot_on', '=', True),
        ], context=context)

        for category in category_pool.browse(cr, uid, category_ids, context=context):
            category_map[category.id] = category.name or category.category_id.name

        # --------------------------------------------------------------------------------------------------------------
        #                                          Publish contact:
        # --------------------------------------------------------------------------------------------------------------
        domain = context.get('force_domain') or []
        partner_ids = partner_pool.search(cr, uid, domain, context=context)
        _logger.info('Selected partners #{}'.format(len(partner_ids)))
        # --------------------------------------------------------------------------------------------------------------
        # Publish contact:
        # --------------------------------------------------------------------------------------------------------------
        endpoint = connector.endpoint
        token = connector.token
        url = {
            'companies': "{}/companies".format(endpoint),
            'contacts': "{}/contacts".format(endpoint),
        }
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json"
        }

        # todo manage ODOO contact create ad unique HS contact!
        total = len(partner_ids)
        counter = 0
        for partner in partner_pool.browse(cr, uid, partner_ids, context=context):
            counter += 1
            # ----------------------------------------------------------------------------------------------------------
            # Mode: Companies - Contacts:
            # ----------------------------------------------------------------------------------------------------------
            if partner.is_company:
                mode = 'companies'
                field_name = 'hubspot_companies_ref'
                hubspot_ref = partner.hubspot_companies_ref
            else:
                mode = 'contacts'
                field_name = 'hubspot_contacts_ref'
                hubspot_ref = partner.hubspot_contacts_ref

            # ----------------------------------------------------------------------------------------------------------
            # Create Payload:
            # ----------------------------------------------------------------------------------------------------------
            payload = self.prepare_hubspot_data(partner, mode=mode, category_map=category_map)
            if hubspot_ref:  # UPDATE
                # ------------------------------------------------------------------------------------------------------
                # Update:
                # ------------------------------------------------------------------------------------------------------
                response = requests.patch(
                    "{}/{}".format(url[mode], hubspot_ref), json=payload, headers=headers, timeout=timeout)

                if response.ok:
                    _logger.info(u"{} di {}. Partner {} aggiornato correttamente su HubSpot (ID: {})".format(
                        counter, total,
                        partner.id, hubspot_ref))
                else:
                    _logger.error(
                        u"Errore aggiornamento HubSpot per {} (ID: {}): {}".format(
                            partner.id, hubspot_ref, response.text))
            else:  # CREATE
                # ------------------------------------------------------------------------------------------------------
                # Create:
                # ------------------------------------------------------------------------------------------------------
                try:
                    response = requests.post(url[mode], json=payload, headers=headers, timeout=timeout)
                    if response.ok:
                        res_json = response.json()
                        new_hp_id = res_json.get('id')
                        if new_hp_id:  # Save hubspot ID for future update
                            partner_pool.write(cr, uid, [partner.id], {
                                field_name: new_hp_id,
                            }, context=context)
                            cr.commit()  # Commit to save immediately the ID:
                            # _logger.info("Partner %s sincronizzato con successo ID: %s", partner.name, new_hp_id)

                    elif response.status_code == 409: # Contact yet present in hubspot
                        res_json = response.json()
                        msg = res_json.get('message', '')
                        # _logger.warning("Contatto %s già esistente su HubSpot: %s", partner.name, msg)

                        # Cerco di recuperare l'ID esistente dal messaggio di errore per registrarlo comunque
                        match = re.search(r'ID: (\d+)', msg)
                        if match:
                            existing_id = match.group(1)
                            partner_pool.write(cr, uid, [partner.id], {
                                field_name: existing_id,
                            }, context=context)
                            cr.commit()
                    else:
                        raise osv.except_osv(
                            _(u'Errore:'),
                            u'Error HubSpot payload {}:\n\n {}'.format(payload, response.text),
                        )

                except Exception as e:
                    if no_raise:
                        _logger.error(u'Error call HS {}:\n\n {}'.format(payload, str(e))),
                    else:
                        raise osv.except_osv(
                            _('Errore:'),
                            _(u'Errore chiamata HS {}:\n\n {}'.format(payload, str(e))),
                        )
                    continue
                    # No commit here for security, go next

    def button_get_contact(self, cr, uid, ids, context=None):
        """ Get contacts from Hubspot:
        """
        timeout = 15

        # Partner used:
        partner_pool = self.pool.get('res.partner')
        if context is None:
            context = {}
        selected_partner_id = context.get('selected_partner_id')

        if not selected_partner_id:
            raise osv.except_osv(
                _(u'Errore:'),
                _(u'Partner ID non trovato, non è possibile leggerlo'),
            )

        # --------------------------------------------------------------------------------------------------------------
        # Open Partner:
        # --------------------------------------------------------------------------------------------------------------
        partner = partner_pool.browse(cr, uid, selected_partner_id, context=context)
        if partner.is_company:
             mode = 'companies'
             hubspot_ref = partner.hubspot_companies_ref
        else:
            mode = 'contacts'
            hubspot_ref = partner.hubspot_contacts_ref

        if not hubspot_ref:  # UPDATE
            raise osv.except_osv(
                _(u'Errore:'),
                _(u'Non trovato ID Hubspot, non è possibile leggerlo'),
            )

        # --------------------------------------------------------------------------------------------------------------
        # Get hubspot partner:
        # --------------------------------------------------------------------------------------------------------------
        connector = self.browse(cr, uid, ids, context=context)[0]
        endpoint = connector.endpoint
        token = connector.token
        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json"
        }

        url = "{}/{}/{}".format(endpoint, mode, hubspot_ref)
        _logger.info('Calling: {}'.format(url))
        response = requests.get(url=url, headers=headers, timeout=timeout)

        if response.ok:
            raise osv.except_osv(
                'Info',
                u"Partner ODOO {} dettaglio HS {}\n:{}".format(partner.id, hubspot_ref, response.text))
        else:
            raise osv.except_osv(
                u'Errore:',
                u"Errore agg. HS ID {} (payload: {}):\n\n{}".format(payload, hubspot_ref, response.text))
        return True

    _columns = {
        'name': fields.char('Nome connessione', required=True, size=100),
        'company_id': fields.many2one('res.company', 'Azienda'),
        'endpoint': fields.char(
            'Endpoint', required=True, size=120, help='Per es.https://api.hubapi.com/crm/v3/objects'),
        'token': fields.char('Token', required=True, size=100),
        'user_token': fields.char('Token', size=100),
        'domain': fields.char('Domain', size=80),
        'hubspot_code': fields.char('Code', size=80),
    }

    _defaults = {
        'endpoint': lambda *s: 'https://api.hubapi.com/crm/v3/objects',
    }


class CrmNewsletterCategoryHubspot(orm.Model):
    """ Model name: Crm Newsletter Hubspot Category
    """
    _name = 'crm.newsletter.category.hubspot'
    _rec_name = 'category_id'
    _order = 'category_id'

    def get_force_category(self, category_id, context):
        """ Prepare context for call original method
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['force_domain'] = [
            ('newsletter_category_id', '=', category_id),
            ('is_address', '=', False),
        ]
        return ctx

    def button_update_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        hubspot_pool = self.pool.get('hubspot.connector')
        # Get connection:
        hubspot_id = hubspot_pool.get_company_hubspot_connector(cr, uid, context=context)

        ctx = self.get_force_category(ids[0], context=context)
        return hubspot_pool.button_update_contact(cr, uid, [hubspot_id], context=ctx)

    def button_update_contact_new(self, cr, uid, ids, context=None):
        """ Update contacts on Hubspot:
            force_domain: Used to update single partner or all category of partner
        """
        hubspot_pool = self.pool.get('hubspot.connector')

        if context is None:
            context = {}

        ctx = context.copy()
        ctx['force_domain'] = [
            ('hubspot_companies_ref', '=', False),
            ('hubspot_contacts_ref', '=', False),
            ('newsletter_category_id', '=', ids[0]),
            ('is_address', '=', False),
        ]

        # Get connection:
        hubspot_id = hubspot_pool.get_company_hubspot_connector(cr, uid, context=context)
        return hubspot_pool.button_update_contact(cr, uid, [hubspot_id], context=ctx)

    def button_odoo_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        model_pool = self.pool.get('ir.model.data')

        # Get domain:
        ctx = self.get_force_category(ids[0], context=context)
        domain = ctx['force_domain']

        #tree_id = model_pool.get_object_reference(
        #    cr, uid,
        #    'base_geo_localize',
        #    'res_partner_geocodes_view')[1]
        #search_view_id = model_pool.get_object_reference(
        #    cr, uid,
        #    'crm_newsletter_category',
        #    'view_res_partner_newsletter_search')[1]
        tree_id = search_view_id = form_id = False

        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner di categoria'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': False,
            'res_model': 'res.partner',
            'view_id': tree_id,
            'search_view_id': search_view_id,
            'views': [
                (tree_id, 'tree'),
                (form_id, 'form'),
            ],
            'domain': domain,
            'context': context,
            'target': 'current',  # 'new'
        }

    _columns = {
        'hubspot_on': fields.boolean('Pubblicata', help='Se spuntato i contatti collegati sono importati su hubspot'),
        'category_id': fields.many2one('crm.newsletter.category', 'Categoria CRM', required=True),
        'hubspot_id': fields.many2one('hubspot.connector', 'Hubspot'),
        'name': fields.char(
            'Nome Hubspot', size=80,
            help='Nome utilizzato su hubspot, se non presente viene utilizzato quello di ODOO'),
    }


class HubspotConnectorInherit(orm.Model):
    """ Hubspot Connector Inherit
    """
    _inherit = 'hubspot.connector'

    _columns = {
        'category_ids': fields.one2many('crm.newsletter.category.hubspot', 'hubspot_id', 'Categorie CRM'),
    }


class ResPartnerInherit(orm.Model):
    """ Res Partner
    """
    _inherit = 'res.partner'

    def button_open_hs_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        partner = self.browse(cr, uid, ids[0], context=context)

        if partner.is_company:
             mode = 'companies'
             hubspot_ref = partner.hubspot_companies_ref
        else:
            mode = 'contacts'
            hubspot_ref = partner.hubspot_contacts_ref

        url = 'https://app-eu1.hubspot.com/{}/{}'.format(mode, hubspot_ref)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def button_get_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        hubspot_pool = self.pool.get('hubspot.connector')
        # Get connection ID:
        hubspot_id = hubspot_pool.get_company_hubspot_connector(cr, uid, context=context)

        if context is None:
            context = {}
        ctx = context.copy()

        ctx['selected_partner_id'] = ids[0]
        return hubspot_pool.button_get_contact(cr, uid, [hubspot_id], context=ctx)

    def hubspot_update_single_partner(self, cr, uid, ids, context=None):
        """ Prepare context for call original method
        """
        hubspot_pool = self.pool.get('hubspot.connector')
        # Get connection:
        hubspot_id = hubspot_pool.get_company_hubspot_connector(cr, uid, context=context)

        if context is None:
            context = {}

        ctx = context.copy()
        ctx['force_domain'] = [
            ('id', '=', ids[0]),  # Only this partner
        ]
        return hubspot_pool.button_update_contact(cr, uid, [hubspot_id], context=ctx)

    def button_delete_contact(self, cr, uid, ids, context=None):
        """ Call delete action
        """
        hubspot_pool = self.pool.get('hubspot.connector')
        # Get connection:
        hubspot_id = hubspot_pool.get_company_hubspot_connector(cr, uid, context=context)

        if context is None:
            context = {}

        ctx = context.copy()
        ctx['unlink_partner_id'] = ids[0]
        return hubspot_pool.button_delete_contact(cr, uid, [hubspot_id], context=ctx)

    _columns = {
        'hubspot_contacts_ref': fields.char(
            'Hubspot ref. Contatto',
            help='ID Hubpost, assegnato al momento della crezione, usato per aggiornamenti (contatti)',
        ),
        'hubspot_companies_ref': fields.char(
            'Hubspot ref. Azienda',
            help='ID Hubpost, assegnato al momento della crezione, usato per aggiornamenti (aziende)',
        ),
    }
