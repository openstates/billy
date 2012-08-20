"""
    views specific to committees
"""
from django.shortcuts import render
from django.http import Http404
from django.template.response import TemplateResponse

from djpjax import pjax

from billy.utils import popularity
from billy.models import db, Metadata, DoesNotExist

from .utils import templatename, mongo_fields


@pjax()
def committees(request, abbr):
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    chamber = request.GET.get('chamber', 'both')
    if chamber in ('upper', 'lower'):
        chamber_name = meta['%s_chamber_name' % chamber]
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

    chambers = {'upper': meta['upper_chamber_name'],
               }
    if meta.committees({'chamber': 'joint'}).count():
        chambers['joint'] = 'Joint'
    if 'lower_chamber_name' in meta:
        chambers['lower'] = meta['lower_chamber_name']

    fields = mongo_fields('committee', 'subcommittee', 'members', 'state',
                          'chamber')

    sort_key = request.GET.get('key', 'committee')
    sort_order = int(request.GET.get('order', 1))

    committees = meta.committees_legislators(spec, fields=fields,
                                 sort=[(sort_key, sort_order)])

    sort_order = -sort_order

    return TemplateResponse(request, templatename('committees'),
                  dict(chamber=chamber, committees=committees, abbr=abbr,
                       metadata=meta, chamber_name=chamber_name,
                   chamber_select_template=templatename('chamber_select_form'),
                   chamber_select_collection='committees',
                   chamber_select_chambers=chambers,
                   committees_table_template=templatename('committees_table'),
                   show_chamber_column=show_chamber_column,
                   sort_order=sort_order, statenav_active='committees'))


def committee(request, abbr, committee_id):
    committee = db.committees.find_one({'_id': committee_id})
    if committee is None:
        raise Http404

    popularity.counter.inc('committees', committee_id, abbr=abbr)

    return render(request, templatename('committee'),
                  dict(committee=committee, abbr=abbr,
                       metadata=Metadata.get_object(abbr),
                       sources=committee['sources'],
                       statenav_active='committees'))
