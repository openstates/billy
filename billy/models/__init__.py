import pdb
from functools import partial 

from django.conf import settings
from billy.models.customfields import *


from mongoengine import *

connect(settings.MONGO_DATABASE, 
        host=settings.MONGO_HOST, port=settings.MONGO_PORT)

def embedded_document_list(class_or_name):
    return ListField(EmbeddedDocumentField(class_or_name))

class Source(Document):
    url = StringField()

    def __unicode__(self):
        return self.url


class Term(EmbeddedDocument):

    meta = {
        'allow_inheritance': False,
        }

    name = StringField()
    end_year = IntField()
    start_year = IntField()


class SessionDetail(EmbeddedDocument):

    meta = {
        'allow_inheritance': False,
        }

    display_name = StringField()
    _scraped_name = StringField()


class Sponsor(Document):
    type = StringField()
    name = StringField()
    chamber = StringField()
    leg_id = StringField()
    
    @property
    def legislator(self):
        return Legislator.objects.get(_id=self.leg_id)


class State(Document):

    meta = {
        'collection': 'metadata',
        'allow_inheritance': False,
        }

    _id   = StringField()
    _type = StringField()

    name  = StringField()
    level = StringField()
    abbreviation  = StringField()
    latest_update = DateTimeField()
    feature_flags = ListField()
    legislature_name = StringField()
    lower_chamber_name = StringField()
    upper_chamber_term = IntField()
    upper_chamber_name = StringField()
    lower_chamber_term = IntField()
    lower_chamber_title = StringField()
    upper_chamber_title = StringField()
    terms = embedded_document_list('Term')
    session_details = embedded_document_list('SessionDetail')

    _ignored_scraped_sessions = ListField()


class Action(EmbeddedDocument):
    date = DateTimeField()
    type = ListField()
    actor = StringField()
    action = StringField()


class BillVersion(EmbeddedDocument):
    url = StringField()
    name = StringField()


class BillDocument(Document):
    url = StringField()
    name = StringField()


class Bill(Document):

    meta = {
        'collection': 'bills',
        'allow_inheritance': False,
        }

    _id = StringField()
    _type = StringField()
    _term = StringField()
    _keywords = ListField(StringField())
    _all_ids = ListField(StringField())

    type = ListField(StringField())
    title = StringField()
    
    level = StringField()
    country = StringField()
    chamber = StringField()
    bill_id = StringField()
    updated_at = DateTimeField()
    created_at = DateTimeField()
    alternate_titles = ListField()

    state = CrossReferenceField(State)
    votes = embedded_document_list('Vote')
    actions = embedded_document_list('Action')
    sources = embedded_document_list('Source')
    sponsors = embedded_document_list('Sponsor')
    versions = embedded_document_list('BillVersion')
    documents = embedded_document_list('BillDocument')

    session_id = StringField(db_field='session')
    @property
    def session(self):
        session = self.state.session_details[self.session_id]
        session.id = self.session_id
        return session



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
    sources = embedded_document_list('Source')

class Committee(Document):

    meta = {
    'collection': 'committees',
    'allow_inheritance': False,
    }

    _id = StringField()
    _type = StringField()
    level = StringField()
    country = StringField()
    members = ListField()
    chamber = StringField()
    _all_ids = ListField()
    committee = StringField()
    created_at = DateTimeField()
    updated_at = DateTimeField()
    state = CrossReferenceField('State')
    sources = embedded_document_list('Source')


class Vote(Document):

    date = DateTimeField()
    _type = StringField()
    vote_id = StringField()

    type = StringField()
    motion = StringField()
    passed = BooleanField()
    chamber = StringField()

    no_count    = IntField()
    yes_count   = IntField()
    other_count = IntField()

    no_votes    = embedded_document_list('Voter')
    yes_votes   = embedded_document_list('Voter')
    other_votes = embedded_document_list('Voter')

    sources = embedded_document_list('Source')

class Voter(Document):
    name = StringField()
    legislator = CrossReferenceField('Legislator')

    def __unicode__(self):
        return self.name



if __name__ == "__main__":
	import pdb
	pdb.set_trace()