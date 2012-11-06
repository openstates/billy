import os
import uuid
import json

from billy.scrape import Scraper, SourcedObject
from billy.core import settings


class TranscriptScraper(Scraper):

    scraper_type = 'transcripts'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/transcript.json')

        with open(schema_path) as f:
            schema = json.load(f)
        schema['properties'][settings.LEVEL_FIELD] = {'maxLength': 2,
                                                      'minLength': 2,
                                                      'type': 'string'}
        return schema

    def scrape(self, chamber, session):
        raise NotImplementedError("TranscriptScrapers must define a"
                                  " scrape method")

    def save_event(self, event):
        self.log("save_event %s %s: %s" % (event['when'],
                                           event['type'],
                                           event['description']))
        self.save_object(event)


class Transcript(SourcedObject):
    def __init__(self, session, when, type,
                 description, **kwargs):

        super(Transcript, self).__init__('transcript', **kwargs)
        self['session'] = session
        self['when'] = when
        self['type'] = type
        self['description'] = description
        self['speeches'] = []
        self.update(kwargs)

    def get_filename(self):
        return "%s.json" % str(uuid.uuid1())
