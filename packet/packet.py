import copy
from datetime import datetime
from functools import lru_cache

from sqlalchemy import exc

from packet.ldap import ldap_get_member, ldap_is_intromember
from .models import Freshman, UpperSignature, FreshSignature, MiscSignature, db, Packet


def sign(signer_username, freshman_username):
    if signer_username == freshman_username:
        return False

    freshman_signed = Freshman.query.filter_by(rit_username=freshman_username).first()
    if freshman_signed is None:
        return False
    packet = freshman_signed.current_packet()
    if packet is None or not packet.is_open():
        return False

    upper_signature = UpperSignature.query.filter(UpperSignature.member == signer_username,
                                                  UpperSignature.packet == packet).first()
    fresh_signature = FreshSignature.query.filter(FreshSignature.freshman_username == signer_username,
                                                  FreshSignature.packet == packet).first()

    if upper_signature:
        if ldap_is_intromember(ldap_get_member(signer_username)):
            return False
        upper_signature.signed = True
    elif fresh_signature:
        # Make sure only on floor freshmen can sign packets
        freshman_signer = Freshman.query.filter_by(rit_username=signer_username).first()
        if freshman_signer and not freshman_signer.onfloor:
            return False
        fresh_signature.signed = True
    else:
        db.session.add(MiscSignature(packet=packet, member=signer_username))
    db.session.commit()

    # Clear functions that read signatures cache
    get_number_signed.cache_clear()
    get_signatures.cache_clear()
    get_upperclassmen_percent.cache_clear()

    return True


def get_essays(freshman_username):
    packet = Freshman.query.filter_by(rit_username=freshman_username).first().current_packet()
    return {'eboard': packet.info_eboard,
            'events': packet.info_events,
            'achieve': packet.info_achieve}


def set_essays(freshman_username, eboard=None, events=None, achieve=None):
    packet = Freshman.query.filter_by(rit_username=freshman_username).first().current_packet()
    if eboard is not None:
        packet.info_eboard = eboard
    if events is not None:
        packet.info_events = events
    if achieve is not None:
        packet.info_achieve = achieve
    try:
        db.session.commit()
    except exc.SQLAlchemyError:
        return False
    return True


@lru_cache(maxsize=2048)
def get_signatures(freshman_username):
    """
    Gets a list of all signatures for the given member
    :param freshman_username:
    :return:
    """
    packet = Freshman.query.filter_by(rit_username=freshman_username).first().current_packet()

    eboard = db.session.query(UpperSignature.member, UpperSignature.signed, Freshman.rit_username) \
        .select_from(UpperSignature).join(Packet).join(Freshman) \
        .filter(UpperSignature.packet_id == packet.id, UpperSignature.eboard.is_(True)) \
        .order_by(UpperSignature.signed.desc()) \
        .distinct().all()

    upper_signatures = db.session.query(UpperSignature.member, UpperSignature.signed, Freshman.rit_username) \
        .select_from(UpperSignature).join(Packet).join(Freshman) \
        .filter(UpperSignature.packet_id == packet.id, UpperSignature.eboard.is_(False))\
        .order_by(UpperSignature.signed.desc())\
        .distinct().all()
    fresh_signatures = \
    db.session.query(FreshSignature.freshman_username, FreshSignature.signed, Freshman.rit_username, Freshman.name) \
        .select_from(Packet).join(FreshSignature).join(Freshman) \
        .filter(FreshSignature.packet_id == packet.id) \
        .order_by(FreshSignature.signed.desc()) \
        .distinct().all()

    misc_signatures = db.session.query(MiscSignature.member, Freshman.rit_username)\
        .select_from(MiscSignature).join(Packet).join(Freshman) \
        .filter(MiscSignature.packet_id == packet.id) \
        .distinct().all()

    return {'eboard': eboard,
            'upperclassmen': upper_signatures,
            'freshmen': fresh_signatures,
            'misc': misc_signatures}


def get_misc_signatures():
    packet_misc_sigs = {}
    try:
        result = db.engine.execute("SELECT packet.freshman_username "
                                   "AS username, count(signature_misc.member) "
                                   "AS signatures FROM packet "
                                   "RIGHT OUTER JOIN signature_misc "
                                   "ON packet.id = signature_misc.packet_id "
                                   "GROUP BY packet.freshman_username;")
        for packet in result:
            packet_misc_sigs[packet.username] = packet.signatures
    except exc.SQLAlchemyError:
        return packet_misc_sigs # TODO; more error checking
    return packet_misc_sigs


@lru_cache(maxsize=2048)
def get_number_signed(freshman_username, separated=False):
    return db.session.query(Packet).filter(Packet.freshman_username == freshman_username,
                                           Packet.start < datetime.now(), Packet.end > datetime.now())\
        .first().signatures_received(not separated)


@lru_cache(maxsize=4096)
def get_number_required(separated=False):
    return db.session.query(Packet) \
        .filter(Packet.start < datetime.now(), Packet.end > datetime.now()).first().signatures_required(not separated)


@lru_cache(maxsize=2048)
def get_upperclassmen_percent(username, onfloor=False):
    upperclassmen_required = get_number_required()
    if onfloor:
        upperclassmen_required -= 1

    upperclassmen_signature = get_number_signed(username)

    return upperclassmen_signature / upperclassmen_required * 100