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
        return True

    _columns = {
        'name': fields.char('Nome connessione', required=True, size=100),
        'company_id': fields.many2one('res.company', 'Azienda'),
        'token': fields.char('Token', required=True, size=100),
        'user_token': fields.char('Token', size=100),
        'domain': fields.char('Domain', size=80),
        'hubspot_code': fields.char('Code', size=80),
    }


class CrmNewsletterCategoryHubspot(orm.Model):
    """ Model name: Crm Newsletter Hubspot Category
    """
    _name = 'crm.newsletter.category.hubspot'
    _rec_name = 'category_id'
    _order = 'name'

    def button_update_contact(self, cr, uid, ids, context=None):
        """ Update contacts
        """
        return True

    _columns = {
        'hubspot_on': fields.boolean(
            'Pubblicata', help='Se spuntato i contatti collegati sono importati su hubspot'),
        'category_id': fields.many2one('crm.newsletter.category', 'Categoria CRM'),
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
