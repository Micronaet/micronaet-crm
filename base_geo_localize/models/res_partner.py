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

from openerp.osv import osv, fields
from openerp import tools
from openerp.tools.translate import _
from geopy.geocoders import Nominatim
from datetime import datetime

# google_url = 'https://www.google.com/maps/@{latitude},{longitude}'
google_url = "https://www.google.com/maps/place/" \
             "{latitude_grad}\"N+{longitude_grad}\"E/@{latitude},{longitude}"


class ResPartner(osv.osv):
    """ Add extra fields
    """
    _inherit = "res.partner"

    _columns = {
        'geo_address': fields.char('Geo Indirizzo', size=180),
        'geo_latitude': fields.float('Geo Latitudine', digits=(16, 5)),
        'geo_longitude': fields.float('Geo Longitudine', digits=(16, 5)),
        'geo_date': fields.date('Geo Data'),
        'geo_altitude': fields.float('Geo Altitudine', digits=(16, 5)),
    }

    def get_geo_grade(self, value):
        """ Return 45.23456 in 45°23'44.6"
        """
        item1 = int(value)
        value -= item1
        item2 = int(value * 60.0)
        value -= item2
        item3 = value * 60.0
        return "'{}°{}'{}\"".format(item1, item2, item3)

    # Button event:
    def open_geo_localize(self, cr, uid, ids, context=None):
        """
        """
        partner = self.browse(cr, uid, ids, context=context)[0]
        latitude = partner.geo_latitude
        latitude_grad = self.get_geo_grade(latitude)
        longitude = partner.geo_longitude
        longitude_grad = self.get_geo_grade(longitude)
        url = google_url.format(
            latitude_grad=latitude_grad,
            longitude_grad=longitude_grad,
            latitude=latitude,
            longitude=longitude,
            )

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def geo_localize(self, cr, uid, ids, context=None):
        """ Extract geo data from address
        """
        geolocator = Nominatim(user_agent="ODOO Micronaet")
        partner = self.browse(cr, uid, ids, context=context)[0]

        location = geolocator.geocode('{} - {} {}{} {}'.format(
            ('{} {}'.format(
                partner.street or '',
                partner.street2 or '')).strip(),
            partner.zip or '',
            partner.city or '',
            ' ({})'.format(partner.state_id.code) if partner.state_id else '',
            partner.country_id.name or '',
            ))

        data = {
            'geo_address': location.address,
            'geo_altitude': location.altitude,
            'geo_latitude': location.latitude,
            'geo_longitude': location.longitude,
            'geo_date': datetime.now(),
        }
        return self.write(cr, uid, [partner.id], data, context=context)
