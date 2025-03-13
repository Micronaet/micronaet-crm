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


class SaleOrderInherit(orm.Model):
    """ Claim management
    """
    _inherit = 'sale.order'

    def button_claim_delivery(self, cr, uid, ids, context=context):
        """ Claim
        """
        order = self.browse(cr, uid, ids[0], context=context)
        now = str(datetime.now())[:10]
        self.write(cr, uid, ids, {
            'claim_date_last': now,
            'claim_date_log': '{}[{}] '.format(order.claim_date_log, now),
        }, context=context)

        return self.message_post(
            cr, uid, ids, body='Sollecitata consegna da parte del cliente',
            context=context)

    _columns = {
        'claim_date_last': fields.date('Data ultimo sollecito'),
        'claim_date_log': fields.text('Dettaglio solleciti'),
    }
