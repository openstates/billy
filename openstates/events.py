from pupa.scrape import Event
from .base import OpenstatesBaseScraper
import dateutil.parser
import datetime as dt
import pytz


class OpenstatesEventScraper(OpenstatesBaseScraper):

    def _date_parse(self, x):
        return pytz.timezone(self.jurisdiction.timezone).localize(
            dateutil.parser.parse(x)
        ) if x else None

    def scrape(self):
        method = 'events/?state={}&dtstart=1776-07-04'.format(self.state)
        self.events = self.api(method)
        seen = set()
        for event in self.events:
            e = Event(name=event.pop('description'),
                      classification=event.pop('type'),
                      location=event.pop('location'),
                      timezone=event.pop('timezone'),
                      start_time=self._date_parse(event.pop('when')),
                      end_time=self._date_parse(event.pop('end')),)
            if len(e.name) >= 300:
                e.name = e.name[:290]

            if len(e.location['name']) >= 100:
                e.location['name'] = e.location['name'][:90]

            composite_key = (e.name, e.description, e.start_time)
            if composite_key in seen:
                print("Duplicate found: %s/%s/%s" % (composite_key))
                continue

            seen.add(composite_key)

            for source in event.pop('sources'):
                if 'retrieved' in source:
                    source.pop('retrieved')
                e.add_source(**source)

            if e.sources == []:
                continue

            ignore = ['country', 'level', 'state', 'created_at', 'updated_at',
                      '+location_url', 'session', 'id', '+chamber', '+agenda',
                      '+cancelled', '+media_contact', '+contact', '+details']
            # +agenda:
            #   Agenda on old (very old) OpenStates data is actually a string
            #   and not any sort of structured data we can use in the items
            #   schema, and is only present for a handful of events.

            for i in ignore:
                if i in event:
                    event.pop(i)

            for link in ['+link', 'link']:
                if link in event:
                    e.add_source(url=event.pop(link))

            for p in event.pop('participants', []):
                type_ = {
                    "committee": "organization",
                    "legislator": "person",
                    None: None,
                }[p.get('participant_type')]

                if type_ is None:
                    # Garbage data.
                    continue

                e.add_participant(name=p['participant'],
                                  note=p['type'],
                                  type=type_,)

            for b in event.pop('related_bills', []):
                item = e.add_agenda_item(
                    b.pop('description', b.pop('+description', None)))

                item.add_bill(bill=b['bill_id'],
                              note=b.pop('type', b.pop('+type', None)))

            for document in event.pop('documents', []):
                e.add_document(url=document['url'],
                               note=document['name'])

            assert event == {}, "Unknown fields: %s" % (
                ", ".join(event.keys())
            )

            yield e
