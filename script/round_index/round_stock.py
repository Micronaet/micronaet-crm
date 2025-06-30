# -*- coding: utf-8 -*-
###############################################################################
#
# ODOO (ex OpenERP) 
# Open Source Management Solution
# Copyright (C) 2001-2015 Micronaet S.r.l. (<http://www.micronaet.it>)
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
import erppeek
import xlsxwriter
import ConfigParser as configparser 
import pdb
from datetime import datetime


excluded = [
    'NMO',
    'SBANC',
    'ANTICIPATO',
    'TRASP',
    'PALLET',
    'SC.EXTRA',
    'VARIE',
    'LOCAZIONE',
    'EMO',
    'EUROPALLET',
    ]

# ----------------------------------------------------------------------------------------------------------------------
# Read configuration parameter:
# ----------------------------------------------------------------------------------------------------------------------
company = 'gpb'
# From config file:
cfg_file = os.path.expanduser('../openerp_{}.cfg'.format(company))

config = configparser.ConfigParser()
config.read([cfg_file])
dbname = config.get('dbaccess', 'dbname')
user = config.get('dbaccess', 'user')
pwd = config.get('dbaccess', 'pwd')
server = config.get('dbaccess', 'server')
port = config.get('dbaccess', 'port')   # verify if it's necessary: getint

# Excel:
start_date = datetime.now().replace(month=1, day=1).strftime('%Y-%m-%d')

file_out = './round_stock_{}.xlsx'.format(company)
row_start = 1

# ----------------------------------------------------------------------------------------------------------------------
# Utility:
# ----------------------------------------------------------------------------------------------------------------------
def xls_write_row(WS, row, row_data, format_cell=None):
    """ Write line in Excel file
    """
    col = 0
    for item in row_data:
        if format_cell:
            WS.write(row, col, item, format_cell)
        else:            
            WS.write(row, col, item)
        col += 1
    return True

# ----------------------------------------------------------------------------------------------------------------------
# Connect to ODOO:
# ----------------------------------------------------------------------------------------------------------------------
odoo = erppeek.Client(
    'http://%s:%s' % (server, port),
    db=dbname,
    user=user,
    password=pwd,
    # 
    )
odoo.context = {'lang': 'it_IT'}    

# ----------------------------------------------------------------------------------------------------------------------
# Read database used:
# ----------------------------------------------------------------------------------------------------------------------
WB = xlsxwriter.Workbook(file_out)

# ----------------------------------------------------------------------------------------------------------------------
#                           Acquisti
# ----------------------------------------------------------------------------------------------------------------------
# Used for Purchase and Correspond:
loop = (
    ('OF', 'Acquisti'), 
    ('OC', 'Corrispettivi'),
    )
    
move_pool = odoo.model('stock.move')
product_data = {}
for doc, ws_name in loop:
    WS = WB.add_worksheet(ws_name)

    row = 0
    xls_write_row(WS, row, [
        'Codice',
        'Q.',
        'Prezzo',

        'Picking',
        'Date',
        'Partner',
        'Origine',
        ])

    # Read newsletter category and put in database:
    domain = [
        ('product_id', '!=', False),
        ('state', '=', 'done'),
        ('picking_id.date', '>=', start_date),
        ('picking_id.origin', 'ilike', doc),
        ]
    if doc == 'OC':
        domain.append(('picking_id.correspond', '=', True))
    move_ids = move_pool.search(domain)

    total = len(move_ids)
    moves = move_pool.browse(move_ids)
    for move in moves:
        product = move.product_id
        default_code = (product.default_code  or '').upper()
        if default_code in excluded:
            continue

        row += 1
        print('Row {} {} / {}'.format(doc, row, total))

        error = ''
        picking = move.picking_id        
        product_qty = move.product_uom_qty or 0
        
        if doc == 'OC':
            origin_line = move.sale_line_id
        else:    
            origin_line = move.purchase_line_id
            
        if picking.partner_id:
            partner_name = picking.partner_id.name or ''
        else:
            partner_name = ''
            error += '[No partner] '
            
        if origin_line:
            price = origin_line.price_unit  # todo discount for OC?
        else:
            price = 0
            error += '[No {} price] '.format(doc)

        if default_code not in product_data:
            # Product, Q. buy, Q. Sold, Total Bye, Total Sold
            product_data[default_code] = [
                product,  # Product
                0.0,  # Q. Buy
                0.0,  # Q. Sold
                0.0,  # Total Buy
                0.0,  # Total Sold
            ]
        
        if doc == 'OC':
            # Sold:
            product_data[default_code][2] += product_qty
            product_data[default_code][4] += product_qty * price
        else:
            # Buy:
            product_data[default_code][1] += product_qty
            product_data[default_code][3] += product_qty * price

        xls_write_row(WS, row, [
            default_code,
            product_qty,
            price or 0,

            picking.name or '',
            picking.date or '',
            partner_name or '',
            picking.origin or '',
            error,
            ])

# ----------------------------------------------------------------------------------------------------------------------
#                           Vendite
# ----------------------------------------------------------------------------------------------------------------------
WS = WB.add_worksheet('Vendite')
line_pool = odoo.model('account.invoice.line')

row = 0
xls_write_row(WS, row, [
    'Codice',
    'Q.',
    'P.d.V.',

    'Fattura',
    'Data',
    'Partner',
    'Errore',
    ])

# Read newsletter category and put in database:
line_ids = line_pool.search([
    ('product_id', '!=', False),
    ('invoice_id.date_invoice', '>=', start_date),
    ])
total = len(line_ids)
lines = line_pool.browse(line_ids)

for line in lines:
    product = line.product_id
    default_code = (product.default_code  or '').upper()
    if default_code in excluded:
        continue

    row += 1
    print('Invoice Row {} / {}'.format(row, total))
    error = ''
    invoice = line.invoice_id
    
    subtotal = line.price_subtotal or 0.0
    product_qty = line.quantity or 0.0
    if product_qty:
        price = subtotal / product_qty
    else:
        price = 0.0
        error += '[No purchase price] '
        
    if default_code not in product_data:
        # product.mx_net_mrp_qty
        product_data[default_code] = [
            product,  # Product
            0.0,  # Q. Buy
            0.0,  # Q. Sold
            0.0,  # Total Buy
            0.0,  # Total Sold
        ]

    product_data[default_code][2] += product_qty  # sold
    product_data[default_code][4] += product_qty * price  # sold
    
    partner_name = invoice.partner_id.name or ''
        
    xls_write_row(WS, row, [
        default_code,
        product_qty,
        price or 0,

        invoice.number or '',
        invoice.date_invoice or '',
        partner_name or '',
        error,
        ])

# ----------------------------------------------------------------------------------------------------------------------
#                           Prodotti
# ----------------------------------------------------------------------------------------------------------------------
print('Create page: Prodotti')
WS = WB.add_worksheet('Prodotti')
row = 0
xls_write_row(WS, row, [
    'Codice',
    'Nome',
    'Acq.',
    'Vend.',
    'Inv. iniz.',
    'Inv. fin.',
    'Mag. medio',
    
    'Acq. medio',
    'Acq. utilizzato',
    'Vend. media', 
    'Marg. medio',
    'Marg. %',
    'Indice rotazione',
    

    'List. (anag.)',
 
    'Inv. costo solo acq.',
    'Inv. non movim.',
    'Costo trasp.',
    'Cambio',
    'Commento',
    'Escluso',
    ])

medium_data = {
    # quantity:
    'start': 0.0,
    'purchase': 0.0,
    'sold': 0.0,

    # subtotal:
    'total_purchase': 0.0,
    'total_sold': 0.0,
}

for default_code in sorted(product_data):
    row += 1
    product, purchase_qty, sold_qty, total_purchase, total_sold = product_data[default_code]
    name = product.name

    # ------------------------------------------------------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------------------------------------------------------
    error = ''
    start_qty = product.mx_start_qty
    final_qty = start_qty + purchase_qty - sold_qty
    medium_qty = (start_qty + final_qty) / 2.0
    
    # ------------------------------------------------------------------------------------------------------------------
    # Comment
    # ------------------------------------------------------------------------------------------------------------------
    if purchase_qty: 
        medium_purchase = total_purchase / purchase_qty
    else:
        medium_purchase = 0.0

    # ------------------------------------------------------------------------------------------------------------------
    # Price used for cost of purchase:
    # ------------------------------------------------------------------------------------------------------------------
    if purchase_qty:
        # Uso prezzo "only buy" (se presente se no il medio) + "trasporto" 
        if product.inventory_cost_only_buy:
            used_purchase = (product.inventory_cost_only_buy + product.inventory_cost_transport)
        else:
            # Prezzo medio usato:
            used_purchase = (medium_purchase + product.inventory_cost_transport)
            error += '[No costo only buy] '
    else:
        # Uso prezzo "senza movimenti"
        used_purchase = product.inventory_cost_no_move 
        error += '[Non acquistato] '
        
    if not sold_qty:
        error += '[Non venduto] '

    # ------------------------------------------------------------------------------------------------------------------
    # Margin:
    # ------------------------------------------------------------------------------------------------------------------
    if sold_qty: 
        medium_sold = total_sold / sold_qty
    else:
        medium_sold = 0.0
        
    margin = medium_sold - used_purchase    
    if not (medium_sold and used_purchase):
        margin_rate = '/'  # Not used
        error += '[Margine non calcolabile] '        
    else:
        margin_rate = margin / medium_sold
        
    # ------------------------------------------------------------------------------------------------------------------
    # Rotation rate:    
    # ------------------------------------------------------------------------------------------------------------------
    if medium_qty:
        rotation_rate = sold_qty * used_purchase / medium_qty
    else:
        rotation_rate = '/'
    
    # ==================================================================================================================
    #                            Medium data
    # ==================================================================================================================
    if default_code[:1] != 'F' and used_purchase > 0 and sold_qty > 0:
        medium_excluded = False

        # Quantity:
        medium_data['start'] += start_qty
        medium_data['purchase'] += purchase_qty
        medium_data['sold'] += sold_qty

        # Subtotal:
        medium_data['total_purchase'] += total_purchase
        medium_data['total_sold'] += total_sold
    else:
        medium_excluded = True

    # ------------------------------------------------------------------------------------------------------------------
    # Write line
    # ------------------------------------------------------------------------------------------------------------------
    xls_write_row(WS, row, [
        default_code,
        name,
        purchase_qty,
        sold_qty,        
        start_qty,
        final_qty,
        medium_qty,
        
        medium_purchase,
        used_purchase,
        medium_sold,
        margin,
        margin_rate,
        rotation_rate,
        
        product.lst_price,  # Prezzo listino

        product.inventory_cost_only_buy,
        product.inventory_cost_no_move,
        product.inventory_cost_transport,
        product.inventory_cost_exchange,
        
        error,
        'X' if medium_excluded else '',
        ])

# ----------------------------------------------------------------------------------------------------------------------
#                          Totali
# ----------------------------------------------------------------------------------------------------------------------
print('Create page: Totali')
WS = WB.add_worksheet('Totali')
row = 0
xls_write_row(WS, row, [
    'Q.\nIniziale',
    'Q.\nFinale',
    'Q.\nAcq.',
    'Q.\nVend.',
    'Q.\nMedia',

    'Totale\nAcq.',
    'Totale\nVend.',
    'Totale\nMarg.',
    'Totale\nMarg. %',

    'Indice rotazione',
])

final_qty = medium_data['start'] + medium_data['purchase'] - medium_data['sold']
medium_qty = (medium_data['start'] + final_qty) / 2.0

total_margin = medium_data['total_sold'] + medium_data['total_purchase']
if medium_data['total_sold']:
    margin_rate = total_margin / medium_data['total_sold']
else:
    margin_rate = 0.0

if medium_qty:
    rotation_rate = 0.0  # q venduta media * costo acquiesto / medium_qty
else:
    rotation_rate = '/'

# ------------------------------------------------------------------------------------------------------------------
# Write line
# ------------------------------------------------------------------------------------------------------------------
xls_write_row(WS, row, [
    medium_data['start'],
    final_qty,
    medium_data['purchase'],
    medium_data['sold'],
    medium_qty,

    medium_data['total_purchase'],
    medium_data['total_sold'],
    total_margin,
    margin_rate,

    rotation_rate,
])

WB.close()
