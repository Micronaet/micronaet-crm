#!/usr/bin/python
###############################################################################
# Copyright (C) 2001-2024 Micronaet S.r.l. <https://micronaet.com>
# Developer: Nicola Riolini @thebrush
#            https://it.linkedin.com/in/thebrush
#            https://linktr.ee/nicolariolini
###############################################################################

import os
import pdb
import folium
import odoorpc
import traceback
import configparser
from flask import Flask, render_template, request, send_from_directory, jsonify
from datetime import datetime

# import sys
# from excel_report import Excel


# -----------------------------------------------------------------------------
#                                  Class
# -----------------------------------------------------------------------------
class FlaskMSSQL:
    """ Class for manage this structure of FLASK + MS SQL Server
    """
    # Utility:
    def get_subfolder(self, subfolder=''):
        """ Get folder for save data
        """
        data_folder = os.getenv('data_folder')  # ENV Variable
        if subfolder:
            return os.path.join(data_folder, subfolder)
        else:
            return data_folder

    def get_odoo(self):
        """ Connect to odoo
        """
        odoo_param = self.context.get('odoo', {})
        odoo = odoorpc.ODOO(
            odoo_param.get('server'), odoo_param.get('port'))

        # Login
        odoo.login(
            odoo_param.get('database'),
            odoo_param.get('username'),
            odoo_param.get('password'),
        )
        return odoo

    # -------------------------------------------------------------------------
    #                              Constructor:
    # -------------------------------------------------------------------------
    def __init__(self, app, config_filename='flask.cfg'):
        """ Constructor
        """
        # Setup init parameters and save in instance context:
        self.context = {}

        # ---------------------------------------------------------------------
        # Config file:
        # ---------------------------------------------------------------------
        # Generate name:
        config_filename = 'odoo.cfg'
        config_fullname = os.path.join(
            self.get_subfolder(),  # Root data folder
            config_filename,
        )

        # Create if not present:
        if not os.path.isfile(config_fullname):
            print('Create init CFG file {}: Change it!'.format(
                config_filename))

            # Create init file:
            cfg_file = open(config_fullname, 'w')
            cfg_file.write('''
        [ODOO]
            server: localhost
            port: 8069
            username: admin
            password: secret
            database: database            
        ''')
            cfg_file.close()

        # Read config file:
        config = configparser.ConfigParser()
        config.read([config_fullname])

        # ---------------------------------------------------------------------
        # Save MS SQL Parameters:
        # ---------------------------------------------------------------------
        self.context['odoo'] = {
            'server': config.get('ODOO', 'server'),
            'port': config.get('ODOO', 'port'),
            'username': config.get('ODOO', 'username'),
            'password': config.get('ODOO', 'password'),
            'database': config.get('ODOO', 'database'),
        }

        # ---------------------------------------------------------------------
        # Save Flask App:
        # ---------------------------------------------------------------------
        self.app = app

    # -------------------------------------------------------------------------
    # Flask Method:
    # -------------------------------------------------------------------------
    def run(self, debug=True):
        """ Start Flask
        """
        self.app.run(debug=debug)


# -----------------------------------------------------------------------------
#                             Webserver URI:
# -----------------------------------------------------------------------------
app = Flask(__name__)
MyFlaskSQL = FlaskMSSQL(app=app)


@app.route('/', methods=['GET', 'POST'])
def home():
    """ Hello page, log access on a file
    """
    partner_data = request.json
    filename = 'folium_{}.html'.format(
        datetime.now().strftime('%Y%m%d%H%M%S'))
    temp_file = './templates/{}'.format(filename)
    if request.method == 'POST':
        # Dynamic page:
        try:
            fmap = False
            for partner in partner_data:
                record = partner_data[partner]

                # [‘red’, ‘blue’, ‘green’, ‘purple’, ‘orange’, ‘darkred’,
                # ’lightred’, ‘beige’, ‘darkblue’, ‘darkgreen’, ‘cadetblue’,
                # ‘darkpurple’, ‘white’, ‘pink’, ‘lightblue’, ‘lightgreen’,
                # ‘gray’, ‘black’, ‘lightgray’]
                if 'color' in record:
                    icon = folium.Icon(color=record['color'])
                    del(record['color'])
                else:
                    icon = folium.Icon(color='grey')
                record['icon'] = icon

                # Create Maps at first record:
                if not fmap:
                    fmap = folium.Map(
                        location=record['location'],
                        titles='Clienti',
                        zoom_start=12,
                    )
                folium.Marker(**record).add_to(fmap)

                # Marker:
                # location = [45.3288, -121.6625],
                # tooltip = "Click me!",
                # popup = "Mt. Hood Meadows",
                # icon = folium.Icon(icon="cloud"),

            fmap.save(temp_file)
            return filename
        except:
            return ''  # No file means error!
    else:
        # Static page:
        return render_template('home.html')


@app.route('/open', methods=['GET'])
def open():
    """ Hello page, log access on a file
    """
    filename = request.args.get('filename')
    if not filename:
        print('Error Opening {}'.format(filename))
        return 'Error'
    else:
        print('Opening {}...'.format(filename))
        return render_template(filename)


@app.route('/search', methods=['GET', 'POST'])
def search():
    """ Hello page, log access on a file
    """
    # Read parameter from POST
    state_code = request.form.get('filter_province', False)
    city = request.form.get('filter_city', False)
    from_wizard = request.form.get('from_wizard', False)

    if not from_wizard:
        return render_template('search.html')

    wizard_obj = 'res.partner.map.geocodes'
    odoo = MyFlaskSQL.get_odoo()
    pdb.set_trace()
    wizard_pool = odoo.env[wizard_obj]
    wizard = wizard_pool.create({
        'customer_mode': 'yes',  # 'all'
        'supplier_mode': 'yes',
        # 'state_id': False,
        'state_code': state_code,
        'city': city,
    })
    result = wizard.action_done()

    # province_data = request.json
    url = 'Ciao'
    return url


if __name__ == '__main__':
    MyFlaskSQL.run()
