import os
import sys
from billy.core import db
from billy.importers.metadata import import_metadata


def load_metadata():
    db.metadata.drop()
    sys.path.append(os.path.dirname(__file__))
    import_metadata("ex")
    import_metadata("yz")


def load_bills():
    db.bills.drop()
    from .ex import bills
    for bill in bills.bills:
        db.bills.save(bill)


def load_legislators():
    db.legislators.drop()
    from .ex import legislators
    for legislator in legislators.legislators:
        db.legislators.save(legislator)
    from .yz import legislators
    for legislator in legislators.legislators:
        db.legislators.save(legislator)


def load_committees():
    db.committees.drop()
    from .ex import committees
    for committee in committees.committees:
        db.committees.save(committee)


def load_events():
    db.events.drop()
    from .ex import events
    for event in events.events:
        db.events.save(event)


def load_districts():
    db.districts.drop()
    from .ex import districts
    for district in districts.districts:
        db.districts.save(district)
