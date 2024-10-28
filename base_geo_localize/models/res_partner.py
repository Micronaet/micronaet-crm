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

import logging
import pdb

from openerp.osv import osv, fields
from openerp import tools
from openerp.tools.translate import _
from geopy.geocoders import Nominatim
from datetime import datetime

_logger = logging.getLogger(__name__)

google_url = 'https://www.google.com/maps/place/' \
             '{latitude},{longitude}/@{latitude},{longitude},17z/data=!3m1!4b1'


class ResPartner(osv.osv):
    """ Add extra fields
    """
    _inherit = "res.partner"

    _columns = {
        'geo_find': fields.boolean(
            'Localizzato', help='Generato con geolocalizzazione'),
        'geo_address': fields.char('Geo Indirizzo', size=180),
        'geo_latitude': fields.float('Geo Latitudine', digits=(16, 5)),
        'geo_longitude': fields.float('Geo Longitudine', digits=(16, 5)),
        'geo_date': fields.date('Geo Data'),
        'geo_altitude': fields.float('Geo Altitudine', digits=(16, 5)),
    }

    '''
    def get_geo_grade(self, value):
        """ Return 45.23456 in 45°23'44.6"
        """
        item1 = int(value)
        value -= item1
        item2 = int(value * 60.0)
        value -= item2
        item3 = value * 60.0
        return item1, item2, item3
    '''

    # Button event:
    def open_geo_localize(self, cr, uid, ids, context=None):
        """
        """
        partner = self.browse(cr, uid, ids, context=context)[0]
        latitude = partner.geo_latitude
        longitude = partner.geo_longitude
        if not longitude or not latitude:
            raise osv.except_osv(
                _('Errore:'),
                _('Non trovata Lat. o Long.!'),
                )
        url = google_url.format(
            # lat1=lat1, lat2=lat2, lat3=lat3,
            # lon1=lon1, lon2=lon2, lon3=lon3,
            latitude=latitude,
            longitude=longitude,
            )
        _logger.info('Open MPS: {}'.format(url))
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def geo_localize(self, cr, uid, ids, context=None):
        """ Extract geo data from address
        """
        def clean_utf8(value):
            """ Clean UTF8
            """
            return (value or '').encode('utf8').decode('utf8')

        geolocator = Nominatim(user_agent="ODOO Micronaet")
        partner = self.browse(cr, uid, ids, context=context)[0]

        partner_address = 'OVERRIDDEN'
        try:
            street = u'{} {}'.format(
                    clean_utf8(partner.street), clean_utf8(partner.street2))
            zipcode = clean_utf8(partner.zip).replace(' ', '')
            city = clean_utf8(partner.city)
            province = ' ({})'.format(partner.state_id.code) if \
                partner.state_id else ''
            country = clean_utf8(partner.country_id.name)

            partner_address = u'{} - {} {}{} {}'.format(
                street, zipcode, city, province, country)
            _logger.info(u'Geolocalize ID {}: {}'.format(
                partner.id, partner_address))
        except:
            _logger.info(u'Error, strange text: {}'.format(partner_address))
            return False
        try:
            location = geolocator.geocode(partner_address)
        except:
            raise osv.except_osv(
                _('Errore:'),
                _('Timeout del servizio!'),
                )
        try:
            data = {
                'geo_find': True,
                'geo_address': location.address,
                'geo_altitude': location.altitude,
                'geo_latitude': location.latitude,
                'geo_longitude': location.longitude,
                'geo_date': datetime.now(),
            }
            self.write(cr, uid, [partner.id], data, context=context)
            return True
        except:
            self.write(cr, uid, [partner.id], {
                'geo_find': False,
                'geo_address': 'Errore indirizzo non decifrabile!'
            }, context=context)
            return False
