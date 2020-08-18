import csv
import os

import requests
from flask import render_template, redirect, request
from werkzeug.utils import secure_filename

from packet import app
from packet.models import Packet, Freshman
from packet.routes.shared import packet_sort_key
from packet.utils import before_request, packet_auth, admin_auth
from packet.log_utils import log_cache, log_time


@app.route('/admin/')
@log_cache
@packet_auth
@admin_auth
@before_request
@log_time
def admin(info=None):
    open_packets = Packet.open_packets()

    # Pre-calculate and store the return values of did_sign(), signatures_received(), and signatures_required()
    for packet in open_packets:
        packet.did_sign_result = packet.did_sign(info['uid'], app.config['REALM'] == 'csh')
        packet.signatures_received_result = packet.signatures_received()
        packet.signatures_required_result = packet.signatures_required()

    open_packets.sort(key=packet_sort_key, reverse=True)

    all_freshmen = Freshman.get_all()

    return render_template('admin.html',
                           open_packets=open_packets,
                           all_freshmen=all_freshmen,
                           info=info)
