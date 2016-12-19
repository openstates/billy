"""
    views specific to events
"""
import json
import datetime
import operator
from icalendar import Calendar, Event

from django.shortcuts import render
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from djpjax import pjax

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
    cal.add('prodid', '-//Open States//billy//')
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
    return render(request, templatename('event'),
                  dict(abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       events=[event],
                       event=event,
                       event_template=templatename('_event'),
                       events_list_template=templatename('events-pjax'),
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


@pjax()
def events(request, abbr):
    year = request.GET.get('year')
    month = request.GET.get('month')
    if year and month:
        if month == "0":
            month = 1

        month = int(month)
        display_date = datetime.datetime(year=int(year), month=month, day=1)
    else:
        display_date = datetime.datetime.now()

    # Compensate for js dates.
    events = _get_events(abbr, display_date.year, display_date.month - 1)
    return TemplateResponse(
        request, templatename('events'),
        dict(abbr=abbr, display_date=display_date,
             metadata=Metadata.get_object(abbr), events=events,
             event_template=templatename('_event'),
             events_list_template=templatename('events-pjax'),
             nav_active='events'))
