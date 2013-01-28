"""
    views specific to events
"""
import json
import urllib
import datetime
import operator
from icalendar import Calendar, Event

from django.shortcuts import render
from django.http import Http404, HttpResponse

import billy
from billy.core import settings
from billy.models import db, Metadata
from billy.utils import JSONEncoderPlus, get_domain

from .utils import templatename


def event_ical(request, abbr, event_id):
    event = db.events.find_one({'_id': event_id})
    if event is None:
        raise Http404

    x_name = "X-BILLY"

    cal = Calendar()
    cal.add('prodid', '-//Sunlight Labs//billy//')
    cal.add('version', billy.__version__)

    cal_event = Event()
    cal_event.add('summary', event['description'])
    cal_event['uid'] = "%s@%s" % (event['_id'], get_domain())
    cal_event.add('priority', 5)
    cal_event.add('dtstart', event['when'])
    cal_event.add('dtend', (event['when'] + datetime.timedelta(hours=1)))
    cal_event.add('dtstamp', event['updated_at'])

    if "participants" in event:
        for participant in event['participants']:
            name = participant['participant']
            cal_event.add('attendee', name)
            if "id" in participant and participant['id']:
                cal_event.add("%s-ATTENDEE-ID" % (x_name), participant['id'])

    if "related_bills" in event:
        for bill in event['related_bills']:
            if "bill_id" in bill and bill['bill_id']:
                cal_event.add("%s-RELATED-BILL-ID" % (x_name), bill['bill_id'])

    cal.add_component(cal_event)
    return HttpResponse(cal.to_ical(), content_type="text/calendar")


def event(request, abbr, event_id):
    '''
    Context:
        - abbr
        - metadata
        - event
        - sources
        - gcal_info
        - gcal_string
        - nav_active

    Templates:
        - billy/web/public/event.html
    '''
    event = db.events.find_one({'_id': event_id})
    if event is None:
        raise Http404

    fmt = "%Y%m%dT%H%M%SZ"

    start_date = event['when'].strftime(fmt)
    duration = datetime.timedelta(hours=1)
    ed = (event['when'] + duration)
    end_date = ed.strftime(fmt)

    gcal_info = {
        "action": "TEMPLATE",
        "text": event['description'].encode('utf-8'),
        "dates": "%s/%s" % (start_date, end_date),
        "details": "",
        "location": event['location'].encode('utf-8'),
        "trp": "false",
        "sprop": "http://%s/" % get_domain(),
        "sprop": "name:billy"
    }
    gcal_string = urllib.urlencode(gcal_info)

    return render(request, templatename('event'),
                  dict(abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       event=event,
                       sources=event['sources'],
                       gcal_info=gcal_info,
                       gcal_string=gcal_string,
                       nav_active='events'))


def _get_events(abbr, year, month):
    '''Get events that occur during the specified year-month. The month
    is 0-based to match the input from javascript.
    '''
    spec = {
        settings.LEVEL_FIELD: abbr,
    }

    # Update the spec with month/year specific data.
    month = int(month)

    # Increment the month to account for 0-based months in javascript.
    month += 1

    year = int(year)
    next_month = month + 1
    if month == 12:
        next_month = 1
    month_start = datetime.datetime(month=month, year=year, day=1)
    month_end = datetime.datetime(month=next_month, year=year, day=1)
    spec['when'] = {'$gte': month_start, '$lt': month_end}

    events = list(db.events.find(spec))
    events.sort(key=operator.itemgetter('when'))
    return events


def events_json_for_date(request, abbr, year, month):
    events = _get_events(abbr, year, month)
    content = json.dumps(list(events), cls=JSONEncoderPlus)
    return HttpResponse(content)


def events_html_for_date(request, abbr, year, month):
    '''
    Context:
        now: current timedelta
        events: list of events

    Templates:
        - billy/web/public/events.html
    '''
    events = _get_events(abbr, year, month)
    display_date = datetime.datetime(year=int(year), month=int(month) + 1,
                                     day=1)
    return render(request, templatename('events_list'),
                  dict(abbr=abbr,
                       display_date=display_date,
                       metadata=Metadata.get_object(abbr),
                       events=events,
                       nav_active='events'))


def events(request, abbr, year=None, month=None):
    if year and month:
        if month == "0":
            month = 1
        display_date = datetime.datetime(year=int(year), month=int(month),
                                         day=1)
    else:
        display_date = datetime.datetime.now()
    return render(request, templatename('events'),
                  dict(abbr=abbr,
                       display_date=display_date,
                       metadata=Metadata.get_object(abbr),
                       nav_active='events'))
