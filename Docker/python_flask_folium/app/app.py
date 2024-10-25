#!/usr/bin/python
###############################################################################
# Copyright (C) 2001-2024 Micronaet S.r.l. <https://micronaet.com>
# Developer: Nicola Riolini @thebrush
#            https://it.linkedin.com/in/thebrush
#            https://linktr.ee/nicolariolini
###############################################################################

import os
import pdb
import gmplot
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
    filename = 'gmplod_{}.html'.format(
        datetime.now().strftime('%Y%m%d%H%M%S'))
    temp_file = './templates/{}'.format(filename)
    if request.method == 'POST':
        # Dynamic page:
        try:
            gmap = False
            for partner in partner_data:
                record = partner_data[partner]

                # Create Maps at first record:
                if not gmap:
                    gmap = gmplot.GoogleMapPlotter(
                        record['lat'],
                        record['lng'],
                        zoom=12)
                gmap.marker(**record)

            gmap.draw(temp_file)
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
