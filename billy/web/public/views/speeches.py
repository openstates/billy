"""
    views specific to events
"""
from django.shortcuts import render

from billy.core import settings
from billy.models import db, Metadata

from .utils import templatename


def speeches_by_event(request, abbr, event_id):
    event = db.events.find_one({
        '_id': event_id,
        settings.LEVEL_FIELD: abbr
    })

    speeches = db.speeches.find({
        "event_id": event_id,
        settings.LEVEL_FIELD: abbr
    }).sort("sequence", 1)

    return render(request, templatename('speeches_by_event'),
                  dict(abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       speeches=speeches,
                       event=event))


def speeches(request, abbr):
    events = db.events.find({
        settings.LEVEL_FIELD: abbr,
    }).sort('when')

    return render(request, templatename('speeches'),
                  dict(abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       speeches=speeches,
                       events=events))
