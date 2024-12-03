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
import cgi

from unidecode import unidecode
import openerp.addons.decimal_precision as dp
from openerp.osv import fields, osv, expression, orm
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import (
    DEFAULT_SERVER_DATE_FORMAT,
    DEFAULT_SERVER_DATETIME_FORMAT,
    DATETIME_FORMATS_MAP,
    float_compare)


_logger = logging.getLogger(__name__)


# todo move from here:
flask_url = 'http://192.168.1.182:5001'
url_open = '%s/open?filename={}' % flask_url

odoo_url = 'http://192.168.1.181:18069/web?db={db}#id={partner_id}&' \
           'view_type=form&model=res.partner&menu_id=682&action=884'


# Utility:
def clean_utf8(value):
    """ Clean UTF8
    """
    return (value or '').encode('utf8').decode('utf8')


def clean_ascii(value):
    """ Clean ASCII
    """
    return (value or '').encode('ascii', 'replace').decode('ascii')


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

        try:
            b64 = open(filename, 'rb').read().encode('base64')
        except:
            raise osv.except_osv(
                _('Report error'),
                _('Cannot return file: %s') % filename,
                )

        attachment_id = attachment_pool.create(cr, uid, {
            'name': name,
            'datas_fname': 'HTML Mappa.kml',
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
        partner_pool = self.pool.get('res.partner')

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

        # ---------------------------------------------------------------------
        # Filter:
        # ---------------------------------------------------------------------
        if state_code:
            domain.append(
                ('state_id.code', '=', state_code))

        if city:
            domain.append(
                ('city', '=', city))

        if state:
            domain.append(
                ('state_id', '=', state.id))

        # ---------------------------------------------------------------------
        # Set operation:
        # ---------------------------------------------------------------------
        # Customer:
        # ---------------------------------------------------------------------
        customer_mode = wizard.customer_mode
        this_domain = domain[:]
        if customer_mode == 'yes':
            this_domain.append(
                ('sql_customer_code', '!=', False),
            )
            customer_ids = set(partner_pool.search(
                cr, uid, this_domain, context=context))
        elif customer_mode == 'no':
            this_domain.append(
                ('sql_customer_code', '=', False),
            )
            customer_ids = set(partner_pool.search(
                cr, uid, this_domain, context=context))
        else:
            customer_ids = False

        # ---------------------------------------------------------------------
        # Supplier:
        # ---------------------------------------------------------------------
        supplier_mode = wizard.supplier_mode
        this_domain = domain[:]
        if supplier_mode == 'yes':
            this_domain.append(
                ('sql_supplier_code', '!=', False),
            )
            supplier_ids = set(partner_pool.search(
                cr, uid, this_domain, context=context))
        elif supplier_mode == 'no':
            this_domain.append(
                ('sql_supplier_code', '=', False),
            )
            supplier_ids = set(partner_pool.search(
                cr, uid, this_domain, context=context))
        else:
            supplier_ids = False

        # ---------------------------------------------------------------------
        # Lead:
        # ---------------------------------------------------------------------
        lead_mode = wizard.lead_mode
        this_domain = domain[:]
        if lead_mode == 'yes':
            this_domain.extend([
                ('sql_customer_code', '=', False),
                ('sql_supplier_code', '=', False),
            ])
            lead_ids = set(partner_pool.search(
                cr, uid, this_domain, context=context))
        elif lead_mode == 'no':
            # todo work with mode filter?
            this_domain.extend([
                '|',
                ('sql_customer_code', '!=', False),
                ('sql_supplier_code', '!=', False),
            ])
            lead_ids = set(partner_pool.search(
                cr, uid, this_domain, context=context))
        else:
            lead_ids = False

        partner_ids = set()
        if customer_ids:
            partner_ids = partner_ids.union(customer_ids)
        if supplier_ids:
            partner_ids = partner_ids.union(supplier_ids)
        if lead_ids:
            partner_ids = partner_ids.union(lead_ids)

        if partner_ids:
            domain.append(
                ('id', 'in', tuple(partner_ids)),
            )
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

    def action_download(self, cr, uid, ids, context=None):
        """ Download instead of open directly
        """
        def clean_html(value=u''):
            """ Clean for HTML
            """
            try:
                # value = unidecode(value)
                value = (value or '').strip()
                value = cgi.escape(value)  # ex html
                return value
            except:
                _logger.error('Error convert{}\n{}'.format(
                    value, sys.exc_info()))
                return ''

        if context is None:
            context = {}

        # Parameters:
        name = clean_html(u'Mappa ODOO')
        description = clean_html(u'Elenco partner esportati da ODOO')

        icon = '503'
        icon_link = \
            'https://www.gstatic.com/mapspro/images/stock/' \
            '{icon}-wht-blank_maps.png'.format(icon=icon)

        pin_colors = {
            'Clienti': 'ff44af62',  # Green dark
            'Clienti (contatto)': 'ff3644db',  # Green
            'Destinazioni': 'ff44af62',  # Blue dark
            'Destinazioni (contatto)': 'ffabdbb7',  # Blue
            'Fornitori': 'ff3644db',  # Red dask
            'Fornitori (contatto)': 'ff969cee',  # Red

            'Lead': 'ff44af62',  # Blue dark
            'Lead (contatto)': 'ffabdbb7',  # Blue
        }

        document = '''<?xml version="1.0" encoding="UTF-8"?>
          <kml xmlns="http://www.opengis.net/kml/2.2">
           <Document>
            <name>{name}</name>
            <description>{description}</description>    
            {style}    
            {folders}
           </Document>
         </kml>    
        '''

        style = ''
        for color in pin_colors.values():
            style += u'''
            <Style id="icon-{icon}-{color}-normal">
              <IconStyle>
                <color>{color}</color>
                <scale>1.1</scale>
                <Icon>
                  <href>{icon_link}</href>
                </Icon>
                <hotSpot x="16" xunits="pixels" y="32" yunits="insetPixels"/>
              </IconStyle>
              <LabelStyle>
                <scale>0</scale>
              </LabelStyle>
              <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
              </BalloonStyle>
            </Style>
            <Style id="icon-{icon}-{color}-highlight">
              <IconStyle>
                <color>{color}</color>
                <scale>1.1</scale>
                <Icon>
                  <href>{icon_link}</href>
                </Icon>
                <hotSpot x="16" xunits="pixels" y="32" yunits="insetPixels"/>
              </IconStyle>
              <LabelStyle>
                <scale>1.1</scale>
              </LabelStyle>
              <BalloonStyle>
                <text><![CDATA[<h3>$[name]</h3>]]></text>
              </BalloonStyle>
            </Style>

            <StyleMap id="icon-{icon}-{color}">
              <Pair>
                <key>normal</key>
                <styleUrl>#icon-{icon}-{color}-normal</styleUrl>
              </Pair>
              <Pair>
                <key>highlight</key>
                <styleUrl>#icon-{icon}-{color}-highlight</styleUrl>
              </Pair>
            </StyleMap>
            '''.format(
                color=color,
                icon=icon,
                icon_link=icon_link,
            )

        folder = '''
            <Folder>
              <name>{name}</name>
              {placemarks}
            </Folder>
            '''

        placemark = '''
              <Placemark>
                <name>{name}</name>
                <description>{descrition}</description>
                <styleUrl>#icon-{icon}-{color}</styleUrl>
                <Point>
                  <coordinates>{lat},{lon},0</coordinates>
                </Point>
              </Placemark>
              '''

        ctx = context.copy()
        ctx['kml_mode'] = True
        partners = self.action_done(cr, uid, ids, context=ctx)

        folders = ''
        for mode in partners:
            placemarks = ''
            color = pin_colors[mode]
            for partner in partners[mode]:
                odoo_partner = partner['partner']
                location = partner['location']
                name = odoo_partner.name
                description = partner.get('popup', '')

                placemarks += placemark.format(
                    icon=icon,
                    name=clean_html(name),
                    description=description,
                    lat=location[1],
                    lon=location[0],
                    color=color,
                    # todo popup
                )

            folders += folder.format(
                name=mode,
                placemarks=placemarks
            )

        # Write file:
        kml_filename = '/tmp/{}.kml'.format(
            str(datetime.now()).replace('/', '').replace(':', '')
        )
        kml_file = open(kml_filename, 'w')
        kml_file.write(document.format(
            name=name,
            description=description,
            style=style,
            folders=folders,
        ))
        kml_file.close()

        # Return file
        return self.return_attachment(
            cr, uid, 'KML Partner file', kml_filename, context=context)

    def action_done(self, cr, uid, ids, context=None):
        """ Event for button done
        """
        if context is None:
            context = {}
        kml_mode = context.get('kml_mode')

        partner_pool = self.pool.get('res.partner')
        domain = self.get_domain(cr, uid, ids, context=context)
        partner_ids = partner_pool.search(cr, uid, domain, context=context)

        partner_data = {}
        _logger.info('Found {} partner'.format(len(partner_ids)))
        for partner in partner_pool.browse(
                cr, uid, partner_ids, context=context):
            partner_ref = '{} {}-{}'.format(
                clean_ascii(partner.name),
                clean_ascii(partner.street),
                clean_ascii(partner.city),
            )
            partner_name = unidecode(partner.name.replace('\n', ' '))
            partner_id = partner.id  # for ODOO URL

            if kml_mode:
                # -------------------------------------------------------------
                # KML mode:
                # -------------------------------------------------------------
                if partner.sql_customer_code:
                    color = 'Clienti'
                elif partner.sql_destination_code:
                    color = 'Destinazioni'
                elif partner.sql_supplier_code:
                    color = 'Fornitori'
                else:
                    color = 'Lead'

                if not partner.is_company:
                    color += ' (contatto)'
                record = {
                    'partner': partner,
                    'location': [partner.geo_latitude, partner.geo_longitude],
                    # popup
                }
            else:
                # -------------------------------------------------------------
                # Maps mode:
                # -------------------------------------------------------------
                # Color setup:
                if partner.sql_customer_code:
                    color = 'green'
                elif partner.sql_destination_code:
                    color = 'blue'
                elif partner.sql_supplier_code:
                    color = 'red'
                elif partner.is_company:
                    color = 'orange'
                else:
                    color = 'yellow'

                record = {
                    'tooltip': partner_name,
                    'location': [partner.geo_latitude, partner.geo_longitude],
                    'color': color,  # Mode in KML file
                    # popup
                }

            # -----------------------------------------------------------------
            # Info Window:
            # -----------------------------------------------------------------
            popup = '{}<br/>'.format(partner_name)

            try:
                phone = (partner.phone or '').strip()
                if phone:
                    popup += "Tel.: <a href='callto:{}'>{}</a>" \
                             "<br/>".format(phone, phone)
            except:
                _logger.error('Error converting phone')

            try:
                email = (partner.email or '').strip()
                if email:
                    popup += "Mail: <a href='mailto:{}'>{}</a>" \
                             "<br/>".format(email, email)
            except:
                _logger.error('Error converting mail')

            try:
                website = (partner.website or '').strip()
                if website:
                    popup += "Sito: <a href='{}' target='_blank'>{}" \
                             "</a><br/>".format(website, website)
            except:
                _logger.error('Error converting phone')

            odoo_partner_url = odoo_url.format(
                db=cr.dbname, partner_id=partner_id)
            popup += "<a href='{}' target='_blank'>Apri ODOO" \
                     "</a><br/>".format(odoo_partner_url)

            if popup:
                record['popup'] = popup

            if kml_mode:
                if color not in partner_data:
                    partner_data[color] = []
                partner_data[color].append(record)
            else:  # Map mode
                partner_data[partner_ref] = record

        if kml_mode:
            return partner_data

        # ---------------------------------------------------------------------
        #                         Call MAPS Flask:
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

        'customer_mode': fields.selection([
            ('yes', 'Sì'),
            ('no', 'No'),
            ('all', 'Indifferente'),
        ], 'Cliente', required=True),
        'supplier_mode': fields.selection([
            ('yes', 'Sì'),
            ('no', 'No'),
            ('all', 'Indifferente'),
        ], 'Fornitore', required=True),
        'contact_mode': fields.selection([
            ('yes', 'Sì'),
            ('no', 'No'),
            ('all', 'Indifferente'),
        ], 'Contatto', required=True),
        'lead_mode': fields.selection([
            ('yes', 'Sì'),
            ('no', 'No'),
            ('all', 'Indifferente'),
        ], 'Lead', required=True),
    }

    _defaults = {
        'customer_mode': lambda *x: 'yes',
        'supplier_mode': lambda *x: 'no',
        'lead_mode': lambda *x: 'all',
        'contact_mode': lambda *x: 'all',
    }
