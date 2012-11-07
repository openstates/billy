import os
import uuid
import json

from billy.scrape import Scraper, SourcedObject
from billy.core import settings


class TranscriptionScraper(Scraper):

    scraper_type = 'transcriptions'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/transcription.json')

        with open(schema_path) as f:
            schema = json.load(f)
        schema['properties'][settings.LEVEL_FIELD] = {'maxLength': 2,
                                                      'minLength': 2,
                                                      'type': 'string'}
        return schema

    def scrape(self, chamber, session):
        raise NotImplementedError("TranscriptionScrapers must define a"
                                  " scrape method")

    def save_transcription(self, transcript):
        self.log("save_transcript %s %s: %s" % (transcript['when'],
                                                transcript['type'],
                                                transcript['description']))
        self.save_object(transcript)


class Transcription(SourcedObject):
    def __init__(self, session, when, type,
                 attribution, text, **kwargs):

        super(Transcript, self).__init__('transcript', **kwargs)
        self['session'] = session
        self['when'] = when
        self['attribution'] = who
        self['text'] = text
        self['type'] = type
        self.update(kwargs)

    def get_filename(self):
        return "%s.json" % str(uuid.uuid1())
