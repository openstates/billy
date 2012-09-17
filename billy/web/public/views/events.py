"""
    views specific to events
"""
import operator
import urllib
import datetime as dt
from icalendar import Calendar, Event

from django.shortcuts import render
from django.http import Http404, HttpResponse


import billy
from billy.models import db, Metadata
from billy.models.pagination import IteratorPaginator

from .utils import templatename, RelatedObjectsList


class EventsList(RelatedObjectsList):
    collection_name = 'metadata'
    sort_func = operator.itemgetter('when')
    sort_reversed = True
    paginator = IteratorPaginator
    query_attr = 'events'
    use_table = True
    rowtemplate_name = templatename('events_list_row')
    column_headers = ('Date', 'Description',)
    show_per_page = 15
    statenav_active = 'events'
    description_template = '{{obj.legislature_name}} Events'
    title_template = 'Events - {{obj.legislature_name}} - Open States'


def event_ical(request, abbr, event_id):
    event = db.events.find_one({'_id': event_id})
    if event is None:
        raise Http404
    cal = Calendar()
    cal.add('prodid', '-//Open States//openstates.org//')
    cal.add('version', billy.__version__)

    cal_event = Event()
    cal_event.add('summary', event['description'])
    cal_event['uid'] = "%s@openstates.org" % (event['_id'])
    cal_event.add('priority', 5)
    cal_event.add('dtstart', event['when'])
    cal_event.add('dtend', (event['when'] + dt.timedelta(hours=1)))
    cal_event.add('dtstamp', event['updated_at'])

    for participant in event['participants']:
        name = participant['participant']
        cal_event.add('attendee', name)

    cal.add_component(cal_event)
    return HttpResponse(cal.as_string(), content_type="text/calendar")


def event(request, abbr, event_id):
    event = db.events.find_one({'_id': event_id})
    if event is None:
        raise Http404

    fmt = "%Y%m%dT%H%M%SZ"

    start_date = event['when'].strftime(fmt)
    duration = dt.timedelta(hours=1)
    ed = (event['when'] + duration)
    end_date = ed.strftime(fmt)

    gcal_info = {
        "action": "TEMPLATE",
        "text": event['description'],
        "dates": "%s/%s" % (start_date, end_date),
        "details": "",
        "location": event['location'].encode('utf-8'),
        "trp": "false",
        "sprop": "http://openstates.org/%s/events/%s/" % (
            abbr,
            event_id
        ),
        "sprop": "name:Open States Event"
    }
    gcal_string = urllib.urlencode(gcal_info)

    return render(request, templatename('event'),
                  dict(abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       event=event,
                       sources=event['sources'],
                       gcal_info=gcal_info,
                       gcal_string=gcal_string,
                       statenav_active='events'))
