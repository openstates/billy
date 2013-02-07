"""
    views specific to committees
"""
from django.shortcuts import render
from django.http import Http404
from django.template.response import TemplateResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from djpjax import pjax

from billy.core import settings
from billy.utils import popularity
from billy.models import db, Metadata, DoesNotExist

from .utils import templatename, mongo_fields


EVENT_PAGE_COUNT = 10


@pjax()
def committees(request, abbr):
    '''
    Context:
        chamber
        committees
        abbr
        metadata
        chamber_name
        chamber_select_template
        chamber_select_collection
        chamber_select_chambers
        committees_table_template
        show_chamber_column
        sort_order
        nav_active

    Templates:
        - billy/web/public/committees.html
        - billy/web/public/committees-pjax.html
        - billy/web/public/chamber_select_form.html
        - billy/web/public/committees_table.html
    '''
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    chamber = request.GET.get('chamber', 'both')
    if chamber in ('upper', 'lower'):
        chamber_name = meta['chambers'][chamber]['name']
        spec = {'chamber': chamber}
        show_chamber_column = False
    elif chamber == 'joint':
        chamber_name = 'Joint'
        spec = {'chamber': 'joint'}
        show_chamber_column = False
    else:
        chamber = 'both'
        spec = {}
        show_chamber_column = True
        chamber_name = ''

    chambers = dict((k, v['name']) for k, v in meta['chambers'].iteritems())
    if meta.committees({'chamber': 'joint'}).count():
        chambers['joint'] = 'Joint'

    fields = mongo_fields('committee', 'subcommittee', 'members',
                          settings.LEVEL_FIELD, 'chamber')

    sort_key = request.GET.get('key', 'committee')
    sort_order = int(request.GET.get('order', 1))

    committees = meta.committees_legislators(spec, fields=fields,
                                             sort=[(sort_key, sort_order)])

    sort_order = -sort_order

    return TemplateResponse(
        request, templatename('committees'),
        dict(chamber=chamber, committees=committees, abbr=abbr, metadata=meta,
             chamber_name=chamber_name,
             chamber_select_template=templatename('chamber_select_form'),
             chamber_select_collection='committees',
             chamber_select_chambers=chambers,
             committees_table_template=templatename('committees_table'),
             show_chamber_column=show_chamber_column, sort_order=sort_order,
             nav_active='committees'))


@ensure_csrf_cookie
def committee(request, abbr, committee_id):
    '''
    Context:
        - committee
        - abbr
        - metadata
        - sources
        - nav_active
        - events

    Tempaltes:
        - billy/web/public/committee.html
        - billy/web/public/developer_committee.html
    '''
    committee = db.committees.find_one({'_id': committee_id})
    if committee is None:
        raise Http404

    events = db.events.find({
        settings.LEVEL_FIELD: abbr,
        "participants.id": committee_id
    }).sort("when", -1)
    events = list(events)
    if len(events) > EVENT_PAGE_COUNT:
        events = events[:EVENT_PAGE_COUNT]

    popularity.counter.inc('committees', committee_id, abbr=abbr)

    return render(request, templatename('committee'),
                  dict(committee=committee, abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       sources=committee['sources'],
                       nav_active='committees',
                       events=events))
