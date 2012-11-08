import uuid

from billy.scrape import Scraper, SourcedObject


class SpeechScraper(Scraper):

    scraper_type = 'speeches'

    def scrape(self, chamber, session):
        raise NotImplementedError("SpeechScrapers must define a"
                                  " scrape method")

    def save_speech(self, speech):
        self.save_object(speech)


class Speech(SourcedObject):
    def __init__(self, session, docid, when, sequence,
                 attribution, text, **kwargs):
        super(Speech, self).__init__('speech', **kwargs)
        self['session'] = session
        self['record_id'] = docid
        self['when'] = when
        self['attribution'] = attribution
        self['text'] = text
        self['sequence'] = sequence
        self['type'] = 'speech'
        self.update(kwargs)

    def get_filename(self):
        return "%s.json" % str(uuid.uuid1())

    def __unicode__(self):
        return '%s %s %s' % (self['when'], self['attribution'],
                             self['sequence'])
