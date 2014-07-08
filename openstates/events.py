from pupa.scrape import Event
from .base import OpenstatesBaseScraper
import dateutil.parser

dparse = lambda x: dateutil.parser.parse(x) if x else None



class OpenstatesEventScraper(OpenstatesBaseScraper):

    def scrape(self):
        method = 'events/?state={}&dtstart=1776-07-04'.format(self.state)
        self.events = self.api(method)
        for event in self.events:
            e = Event(name=event['description'],
                      location=event['location'],
                      start_time=dparse(event['when']),
                      end_time=dparse(event['end']),)
            for source in event['sources']:
                e.add_source(**source)
            yield e
