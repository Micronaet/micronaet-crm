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

    # --------------------
    # Wizard button event:
    # --------------------
    def action_done(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        partner_pool = self.pool.get('res.partner')

        if context is None:
            context = {}

        wizard = self.browse(cr, uid, ids, context=context)[0]
        state_code = wizard.state_code
        city = wizard.city

        # Only partner with geocodes:
        domain = [
            ('geo_latitude', '!=', False),
            ('geo_longitude', '!=', False),
        ]
        if state_code:
            domain.append(
                ('state_id.code', '=', state_code))

        if city:
            domain.append(
                ('city', '=', city))

        partner_ids = partner_pool.search(cr, uid, domain, context=context)
        partner_data = {}
        for partner in partner_pool.browse(
                cr, uid, partner_ids, context=context):
            partner_data[partner.name] = (
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
        # 'state_id': fields.many2one(
        #    'res.state', 'Provincia',
        #    help='Seleziona nazione'),
        'state_code': fields.char('Provincia', size=4),
        'city': fields.char('Città', size=4),
    }
