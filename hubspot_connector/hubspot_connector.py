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

    def button_update_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        partner_pool = self.pool.get('res.partner')
        category_pool = self.pool.get('crm.newsletter.category.hubspot')

        connector = self.browse(cr, uid, ids, context=context)[0]

        if context is None:
            context = {}

        # --------------------------------------------------------------------------------------------------------------
        # Load category:
        # --------------------------------------------------------------------------------------------------------------
        category_map = {}
        category_ids = category_pool.search(cr, uid, [
            ('hubspot_on', '=', True),
        ], context=context)

        for category in category_pool.browse(cr, uid, category_ids, context=context):
            category_map[category.id] = category.name or category.category_id.name

        # --------------------------------------------------------------------------------------------------------------
        #                                                 Publish contact:
        # --------------------------------------------------------------------------------------------------------------
        domain = context.get('force_domain') or []
        partner_ids = partner_pool.search(cr, uid, domain, context=context)[:2]

        # --------------------------------------------------------------------------------------------------------------
        # Publish contact:
        # --------------------------------------------------------------------------------------------------------------
        endpoint = connector.endpoint  # 'https://api.hubapi.com/crm/v3/objects'
        url = "{}/contacts".format(endpoint)
        token = connector.token

        headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json"
        }

        pdb.set_trace()
        for partner in partner_pool.browse(cr, uid, partner_ids, context=context):
            hubspot_id = partner.hubspot_id
            if not hubspot_id:
                payload = {
                    #"associations": [
                    #    {
                    #        "to": {"id": "{}".format(partner.id)},
                    #        "types": [
                    #            {
                    #                "associationCategory": "HUBSPOT_DEFINED",
                    #                "associationTypeId": 123
                    #            }
                    #        ]
                    #    }
                    #],
                    "properties": {
                        # Company:
                        # 'lifecyclestage':
                        'name': partner.name,
                        'address': partner.street or '',
                        'city': partner.city or '',
                        'zip': partner.zipcode or '',
                        #'state',
                        #'hs_object_id',
                        # Contact:
                        #'hs_object_id' 'firstname' 'lastname' 'phone' 'mobilephone' 'Fax' 'email' 'email_pec' 'website'
                        #'city' 'state'
                    }
                }
                try:
                    response = requests.post(url, json=payload, headers=headers)
                    if response.status_code in [200, 201]:
                        res_data = response.json()
                        # Salva l'ID di HubSpot nel campo di Odoo per i futuri aggiornamenti
                        new_hp_id = res_data.get('id')
                        partner.write({'hubspot_ref': new_hp_id})
                        #if response.ok:
                        #    response_json = response.json()
                        #    # print(response.text)
                        #else:
                        #    pass  # Error creating
                    else:
                        _logger.error("Errore HubSpot: %s", response.text)
                except Exception as e:
                    _logger.error("Errore durante la chiamata: %s", str(e))
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
        ]
        return ctx

    def button_update_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        hubspot_pool = self.pool.get('hubspot.connector')
        ctx = self.get_force_category(ids[0], context=context)
        return hubspot_pool.button_update_contact(cr, uid, ids, context=ctx)

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

    _columns = {
        'hubspot_ref': fields.char(
            'Hubspot ref.',
            help='ID Hubpost, assegnato al momento della crezione, usato per aggiornamenti',
        ),
    }
