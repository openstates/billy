import os
import uuid
import json

from billy.scrape import Scraper, SourcedObject
from billy.core import settings


class SpeechScraper(Scraper):

    scraper_type = 'speeches'

    def _get_schema(self):
        schema_path = os.path.join(os.path.split(__file__)[0],
                                   '../schemas/speech.json')

        with open(schema_path) as f:
            schema = json.load(f)
        schema['properties'][settings.LEVEL_FIELD] = {'maxLength': 2,
                                                      'minLength': 2,
                                                      'type': 'string'}
        return schema

    def scrape(self, chamber, session):
        raise NotImplementedError("SpeechScrapers must define a"
                                  " scrape method")

    def save_speech(self, speech):
        self.log("save_speech %s %s %s" % (speech['when'],
                                           speech['attribution'],
                                           speech['sequence']))
        self.save_object(speech)


class Speech(SourcedObject):
    def __init__(self, session, docid, when, sequence,
                 attribution, text, **kwargs):
        super(Speech, self).__init__('speech', **kwargs)
        self['session'] = session
        self['document_id'] = docid
        self['when'] = when
        self['attribution'] = attribution
        self['text'] = text
        self['sequence'] = sequence
        self['type'] = 'speech'
        self.update(kwargs)

    def get_filename(self):
        return "%s.json" % str(uuid.uuid1())
