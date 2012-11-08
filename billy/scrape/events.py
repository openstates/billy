import uuid

from billy.scrape import Scraper, SourcedObject


class EventScraper(Scraper):

    scraper_type = 'events'

    def scrape(self, chamber, session):
        raise NotImplementedError("EventScrapers must define a scrape method")

    save_event = Scraper.save_object


class Event(SourcedObject):
    def __init__(self, session, when, type,
                 description, location, end=None, **kwargs):
        super(Event, self).__init__('event', **kwargs)
        self.uuid = uuid.uuid1()  # If we need to save an event more than once

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
        kwargs.update({"bill_id": bill_id})
        self['related_bills'].append(kwargs)

    def add_participant(self,
                        type,
                        participant,
                        participant_type,
                        **kwargs):

        kwargs.update({'type': type,
                       'participant_type': participant_type,
                       'participant': participant})

        self['participants'].append(kwargs)

    def get_filename(self):
        return "%s.json" % str(self.uuid)

    def __unicode__(self):
        return "%s %s: %s" % (self['when'], self['type'], self['description'])
