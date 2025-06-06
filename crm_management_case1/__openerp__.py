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

{
    'name': 'CRM Management',
    'version': '0.1',
    'category': 'CRM',
    'description': '''
        Manage case 1
        Add management for company 1 (particular case study used)
        ''',
    'author': 'Micronaet S.r.l. - Nicola Riolini',
    'website': 'http://www.micronaet.it',
    'license': 'AGPL-3',
    'depends': [
        'base',
        'crm',
        'sale',
        'crm_newsletter_category', # newsletter_category_id
        'campaign_base', # type_id
        'partner_addresses',

        # Field for sql code:
        'sql_partner_agent',
        'sql_partner',
        ],
    'init_xml': [],
    'demo': [],
    'data': [
        #'security/ir.model.access.csv',
        'case1_view.xml',
        'scheduler.xml',
        ],
    'active': False,
    'installable': True,
    'auto_install': False,
    }
