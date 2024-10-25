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
import traceback
from flask import Flask, render_template, request, send_from_directory, jsonify
from datetime import datetime

# import sys
# import configparser
# from excel_report import Excel


# -----------------------------------------------------------------------------
#                                  Class
# -----------------------------------------------------------------------------
class FlaskMSSQL:
    """ Class for manage this structure of FLASK + MS SQL Server
    """
    # -------------------------------------------------------------------------
    #                              Constructor:
    # -------------------------------------------------------------------------
    def __init__(self, app, config_filename='flask.cfg'):
        """ Constructor
        """
        # Save Flask App:
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


if __name__ == '__main__':
    MyFlaskSQL.run()
