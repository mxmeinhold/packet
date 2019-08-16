"""
Shared API endpoints
"""
from flask import request

from packet import app, db
from packet.context_processors import get_rit_name
from packet.mail import send_report_mail
from packet.utils import before_request, packet_auth, notify_slack
from packet.models import Packet, MiscSignature, NotificationSubscription
from packet.notifications import packet_signed_notification, packet_100_percent_notification


@app.route("/api/v1/sign/<packet_id>/", methods=["POST"])
@packet_auth
@before_request
def sign(packet_id, info):
    packet = Packet.by_id(packet_id)

    if packet is not None and packet.is_open():
        was_100 = packet.is_100()
        if app.config["REALM"] == "csh":
            # Check if the CSHer is an upperclassman and if so, sign that row
            for sig in filter(lambda sig: sig.member == info["uid"], packet.upper_signatures):
                sig.signed = True
                app.logger.info("Member {} signed packet {} as an upperclassman".format(info["uid"], packet_id))
                packet_signed_notification(packet, info["uid"])
                return commit_sig(packet, was_100)

            # The CSHer is a misc so add a new row
            db.session.add(MiscSignature(packet=packet, member=info["uid"]))
            app.logger.info("Member {} signed packet {} as a misc".format(info["uid"], packet_id))
            packet_signed_notification(packet, info["uid"])
            return commit_sig(packet, was_100)
        else:
            # Check if the freshman is onfloor and if so, sign that row
            for sig in filter(lambda sig: sig.freshman_username == info["uid"], packet.fresh_signatures):
                sig.signed = True
                app.logger.info("Freshman {} signed packet {}".format(info["uid"], packet_id))
                packet_signed_notification(packet, info["uid"])
                return commit_sig(packet, was_100)

    app.logger.warn("Failed to add {}'s signature to packet {}".format(info["uid"], packet_id))
    return "Error: Signature not valid.  Reason: Unknown"


@app.route("/api/v1/subscribe/", methods=["POST"])
@packet_auth
@before_request
def subscribe(info):
    data = request.form
    if app.config["REALM"] == "csh":
        subscription = NotificationSubscription(token=data['token'], member=info["uid"])
    else:
        subscription = NotificationSubscription(token=data['token'], freshman_username=info["uid"])
    db.session.add(subscription)
    db.session.commit()
    return "Token subscribed for " + info["uid"]


@app.route("/api/v1/report/", methods=["POST"])
@packet_auth
@before_request
def report(info):
    form_results = request.form
    send_report_mail(form_results, get_rit_name(info['uid']))
    return "Success: " + get_rit_name(info['uid']) + " sent a report"


def commit_sig(packet, was_100):
    db.session.commit()
    if not was_100 and packet.is_100():
        packet_100_percent_notification(packet)
        notify_slack(packet.freshman.name)

    return "Success: Signed Packet: " + packet.freshman_username
