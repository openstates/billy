"""
    views specific to events
"""
import json
import urllib
import datetime
from icalendar import Calendar, Event

from django.shortcuts import render
from django.http import Http404, HttpResponse
from django.contrib.sites.models import Site
from django.template.response import TemplateResponse

from djpjax import pjax

import billy
from billy.core import settings
from billy.models import db, Metadata
from billy.utils import JSONEncoderPlus

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
    cal_event['uid'] = "%s@%s" % (event['_id'], Site.objects.all()[0].domain)
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
        "sprop": "http://%s/" % Site.objects.all()[0].domain,
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

@pjax()
def events(request, abbr):
    '''
    Context:
      - XXX: FIXME

    Templates:
        - billy/web/public/events.html
    '''
    recent_events = db.events.find({
        settings.LEVEL_FIELD: abbr
    }).sort("when", -1)
    events = recent_events[:30]
    recent_events.rewind()
    now = datetime.datetime.now()

    return TemplateResponse(request,
                  templatename('events'),
                  dict(abbr=abbr,
                       now=now,
                       metadata=Metadata.get_object(abbr),
                       events=events,
                       nav_active='events',
                       recent_events=recent_events))


def events_json_for_date(request, abbr, year, month):
    spec = {
        settings.LEVEL_FIELD: abbr,
        }

    # # Update the spec with month/year specific data.
    # month = int(month)
    # year = int(year)
    # next_month = month + 1
    # if month == 12:
    #     next_month = 1
    # month_start = datetime.datetime(month=month, year=year, day=1)
    # month_end = datetime.datetime(month=next_month, year=year, day=1)
    # spec['when'] = {'$gte': month_start, '$lt': month_end}

    events = db.events.find(spec)
    content = json.dumps(list(events), cls=JSONEncoderPlus)
    return HttpResponse(content)
