import os
import uuid
import json

from billy.scrape import Scraper, SourcedObject


class EventScraper(Scraper):

    scraper_type = 'events'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/event.json')

        with open(schema_path) as f:
            schema = json.load(f)

        return schema

    def scrape(self, chamber, session):
        raise NotImplementedError("EventScrapers must define a scrape method")

    def save_event(self, event):
        self.log("save_event %s %s: %s" % (event['when'],
                                           event['type'],
                                           event['description']))
        self.save_object(event)


class Event(SourcedObject):
    def __init__(self, session, when, type,
                 description, location, end=None, **kwargs):
        super(Event, self).__init__('event', **kwargs)
        self['session'] = session
        self['when'] = when
        self['type'] = type
        self['description'] = description
        self['end'] = end
        self['participants'] = []
        self['location'] = location
        self['documents'] = []
        self['related_bills'] = []
        self.update(kwargs)

    def add_document(self, name, url, type=None, mimetype=None, **kwargs):
        d = dict(name=name, url=url, **kwargs)
        if mimetype:
            d['mimetype'] = mimetype
        if not type:
            type = "other"
        d['type'] = type
        self['documents'].append(d)

    def add_related_bill(self, bill_id, **kwargs):
        kwargs.update({ "bill_id" : bill_id })
        self['related_bills'].append(kwargs)

    def add_participant(self, type, participant, **kwargs):
        kwargs.update({'type': type, 'participant': participant})
        self['participants'].append(kwargs)

    def get_filename(self):
        return "%s.json" % str(uuid.uuid1())
