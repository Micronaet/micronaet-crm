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
import pdb
import sys
import logging
import requests
import json
import openerp
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


_logger = logging.getLogger(__name__)


# todo move from here:
flask_url = 'http://192.168.1.182:5001'
url_open = '%s/open?filename={}' % flask_url


class ResPartnerMapGeocodes(orm.TransientModel):
    """ Wizard for Geocode partner
    """
    _name = 'res.partner.map.geocodes'

    # todo
    def return_attachment(self, cr, uid, name, filename, context=None):
        """ Return HTML page
        """
        # Pool used:
        attachment_pool = self.pool.get('ir.attachment')
        origin = '/tmp/{}'.format(filename)

        try:
            b64 = open(origin, 'rb').read().encode('base64')
        except:
            raise osv.except_osv(
                _('Report error'),
                _('Cannot return file: %s') % origin,
                )

        attachment_id = attachment_pool.create(cr, uid, {
            'name': name,
            'datas_fname': 'HTML Mappa',
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

    # --------------------
    # Wizard button event:
    # --------------------
    def get_domain(self, cr, uid, ids, context=None):
        """ Generate domain from wizard
        """
        if context is None:
            context = {}
        only_geo = context.get('only_geo', True)

        wizard = self.browse(cr, uid, ids, context=context)[0]
        state_code = wizard.state_code
        city = wizard.city
        state = wizard.state_id

        # Only partner with geocodes:
        if only_geo:
            domain = [
                ('geo_latitude', '!=', 0),
                ('geo_longitude', '!=', 0),
            ]
        else:
            domain = []

        if state_code:
            domain.append(
                ('state_id.code', '=', state_code))

        if city:
            domain.append(
                ('city', '=', city))

        if state:
            domain.append(
                ('state_id', '=', state.id))
        return domain

    def action_open_partner_all(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['only_geo'] = False
        return self.action_open_partner(cr, uid, ids, context=ctx)

    def action_open_partner(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        partner_pool = self.pool.get('res.partner')
        model_pool = self.pool.get('ir.model.data')

        domain = self.get_domain(cr, uid, ids, context=context)
        partner_ids = partner_pool.search(cr, uid, domain, context=context)

        tree_id = False
        # tree_id = model_pool.get_object_reference(
        #    cr, uid, 'base', 'view_res_partner_form')[1]

        return {
            'type': 'ir.actions.act_window',
            'name': _('Partner'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_id': partner_ids[0],
            'res_model': 'res.partner',
            # 'view_id': view_id, # False
            'views': [
                (tree_id, 'tree'),
                (False, 'form'),
            ],
            'domain': [('id', 'in', partner_ids)],
            'context': context,
            'target': 'current',  # 'new'
            'nodestroy': False,
        }

    def action_done(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        partner_pool = self.pool.get('res.partner')

        domain = self.get_domain(cr, uid, ids, context=context)

        partner_ids = partner_pool.search(cr, uid, domain, context=context)
        partner_data = {}
        _logger.info('Found {} partner'.format(len(partner_ids)))
        for partner in partner_pool.browse(
                cr, uid, partner_ids, context=context):
            partner_ref = '{} {}-{}'.format(
                partner.name,
                partner.street,
                partner.city,
            )
            partner_data[partner_ref] = (
                partner.geo_latitude,
                partner.geo_longitude,
            )

        # ---------------------------------------------------------------------
        # Call MAPS Flask:
        # ---------------------------------------------------------------------
        headers = {
            'Content-type': 'application/json',
            'Accept': 'text/plain',
        }

        reply = requests.post(
            flask_url, data=json.dumps(partner_data), headers=headers)

        url = 'URL NON PRESENTE'
        if reply.ok:
            filename = reply.text
            if filename:
                url = url_open.format(filename)
                return {
                    'type': 'ir.actions.act_url',
                    'url': url,
                    'target': 'new',
                }
        raise osv.except_osv(
            _('Errore MAPS'),
            _('Errore aprendo la mappa generata: {}'.format(url)),
        )

    _columns = {
        # 'country_id': fields.many2one(
        #    'res.country', 'Nazione',
        #    help='Seleziona nazione'),
        'state_id': fields.many2one(
            'res.country.state', 'Provincia',
            help='Seleziona provincia'),
        'city': fields.char('Città', size=60),
        'state_code': fields.char('Provincia', size=4),
    }
