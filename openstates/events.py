from pupa.scrape import Event
from .base import OpenstatesBaseScraper
import dateutil.parser

dparse = lambda x: dateutil.parser.parse(x) if x else None



class OpenstatesEventScraper(OpenstatesBaseScraper):

    def scrape(self):
        method = 'events/?state={}&dtstart=1776-07-04'.format(self.state)
        self.events = self.api(method)
        for event in self.events:
            e = Event(name=event.pop('description'),
                      classification=event.pop('type'),
                      location=event.pop('location'),
                      timezone=event.pop('timezone'),
                      start_time=dparse(event.pop('when')),
                      end_time=dparse(event.pop('end')),)

            for source in event.pop('sources'):
                e.add_source(**source)

            ignore = ['country', 'level', 'state', 'created_at', 'updated_at',
                      'session', 'id']

            for i in ignore:
                if i in event:
                    event.pop(i)

            for p in event.pop('participants', []):
                print(p)
                raise ValueError

            for b in event.pop('related_bills', []):
                print(b)
                raise ValueError

            for document in event.pop('documents', []):
                print(document)
                raise ValueError

            assert event == {}, "Unknown fields: %s" % (
                ", ".join(event.keys())
            )
            yield e
