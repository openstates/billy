
from django.conf import settings

from mongoengine import *

connect(settings.MONGO_DATABASE, 
        host=settings.MONGO_HOST, port=settings.MONGO_PORT)

class State(Document):

    meta = {
    'collection': 'metadata',
    'allow_inheritance': False,
    }

    _id   = StringField()
    name  = StringField()
    _type = StringField()
    terms = ListField()
    level = StringField()
    abbreviation  = StringField()
    latest_update = DateTimeField()
    feature_flags = ListField()
    session_details  = DictField()
    legislature_name = StringField()
    lower_chamber_name = StringField()
    upper_chamber_term = IntField()
    upper_chamber_name = StringField()
    lower_chamber_term = IntField()
    lower_chamber_title = StringField()
    upper_chamber_title = StringField()
    _ignored_scraped_sessions = ListField()

class Bill(Document):

    meta = {
    'collection': 'bills',
    'allow_inheritance': False,
    }


    _id = StringField()
    type = ListField()
    votes = ListField()
    title = StringField()
    state = StringField()
    _type = StringField()
    _term = StringField()
    level = StringField()
    actions = ListField()
    sources = ListField()
    session = StringField()
    country = StringField()
    chamber = StringField()
    bill_id = StringField()
    sponsors = ListField()
    versions = ListField()
    _all_ids = ListField()
    documents = ListField()
    _keywords = ListField()
    updated_at = DateTimeField()
    created_at = DateTimeField()
    alternate_titles = ListField()

class Legislator(Document):

    meta = {
    'collection': 'legislators',
    'allow_inheritance': False,
    }


    url = StringField()
    _id = StringField()
    state = StringField()
    party = StringField()
    _type = StringField()
    roles = ListField()
    level = StringField()
    leg_id = StringField()
    active = BooleanField()
    sources = ListField()
    country = StringField()
    chamber = StringField()
    district = StringField()
    _all_ids = ListField()
    suffixes = StringField()
    last_name = StringField()
    full_name = StringField()
    photo_url = StringField()
    updated_at = DateTimeField()
    first_name = StringField()
    created_at = DateTimeField()
    middle_name = StringField()
    _scraped_name = StringField()

class Committee(Document):

    meta = {
    'collection': 'committee',
    'allow_inheritance': False,
    }

    _id = StringField()
    _type = StringField()
    level = StringField()
    state = StringField()
    country = StringField()
    sources = ListField()
    members = ListField()
    chamber = StringField()
    _all_ids = ListField()
    committee = StringField()
    created_at = DateTimeField()
    updated_at = DateTimeField()




if __name__ == "__main__":
	import pdb
	pdb.set_trace()