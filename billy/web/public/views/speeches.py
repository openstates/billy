"""
    views specific to events
"""
from django.shortcuts import render
from django.http import Http404, HttpResponse
from django.contrib.sites.models import Site

import billy
from billy.models import db, Metadata

from .utils import templatename


def speeches(request, abbr, event_id):
    event = db.events.find_one({
        '_id': event_id
    })

    speeches = db.speeches.find({
        "event_id": event_id
    }).sort("sequence", 1)

    return render(request, templatename('speeches'),
                  dict(abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       speeches=speeches,
                       event=event,
                       nav_active='events'))
