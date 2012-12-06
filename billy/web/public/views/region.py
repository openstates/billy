"""
    views that are specific to a region
"""
import re
import urllib
from collections import defaultdict

from django.shortcuts import redirect, render
from django.http import Http404
from django.template.defaultfilters import striptags

from billy.core import settings
from billy.models import db, Metadata, DoesNotExist, Bill
from billy.models.pagination import CursorPaginator
from ..forms import get_region_select_form
from .utils import templatename, ListViewBase


def region_selection(request):
    '''Handle submission of the region selection form in the base template. '''
    form = get_region_select_form(request.GET)
    abbr = form.data.get('abbr')
    if not abbr or len(abbr) != 2:
        return redirect('homepage')
    return redirect('region', abbr=abbr)


def region(request, abbr):
    '''
    Context:
        - abbr
        - metadata
        - sessions
        - chambers
        - joint_committee_count
        - nav_active

    Templates:
        - bill/web/public/region.html
    '''
    report = db.reports.find_one({'_id': abbr})
    try:
        meta = Metadata.get_object(abbr)
    except DoesNotExist:
        raise Http404

    # count legislators
    legislators = meta.legislators({'active': True}, {'party': True,
                                                      'chamber': True})
    # Maybe later, mapreduce instead?
    party_counts = defaultdict(lambda: defaultdict(int))
    for leg in legislators:
        if 'chamber' in leg:    # exclude lt. governors
            party_counts[leg['chamber']][leg['party']] += 1

    chambers = []

    for chamber_type, chamber in meta['chambers'].iteritems():
        res = {}

        # chamber metadata
        res['type'] = chamber_type
        res['title'] = chamber['title']
        res['name'] = chamber['name']

        # legislators
        res['legislators'] = {
            'count': sum(party_counts[chamber_type].values()),
            'party_counts': dict(party_counts[chamber_type]),
        }

        # committees
        res['committees_count'] = meta.committees({'chamber': chamber_type}
                                                 ).count()

        res['latest_bills'] = meta.bills({'chamber': chamber_type}).sort(
            [('action_dates.first', -1)]).limit(2)
        res['passed_bills'] = meta.bills({'chamber': chamber_type}).sort(
            [('action_dates.passed_' + chamber_type, -1)]).limit(2)

        chambers.append(res)

    joint_committee_count = meta.committees({'chamber': 'joint'}).count()

    # add bill counts to session listing
    sessions = meta.sessions()
    for s in sessions:
        try:
            s['bill_count'] = (
                report['bills']['sessions'][s['id']]['upper_count']
                + report['bills']['sessions'][s['id']]['lower_count'])
        except KeyError:
            # there's a chance that the session had no bills
            s['bill_count'] = 0

    return render(request, templatename('region'),
                  dict(abbr=abbr, metadata=meta, sessions=sessions,
                       chambers=chambers,
                       joint_committee_count=joint_committee_count,
                       nav_active='home'))


def search(request, abbr):
    '''
    Context:
        - search_text
        - abbr
        - metadata
        - found_by_id
        - bill_results
        - more_bills_available
        - legislators_list
        - more_legislators_available
        - nav_active

    Tempaltes:
        - billy/web/public/search_results_no_query.html
        - billy/web/public/search_results_bills_legislators.html
        - billy/web/public/bills_list_row_with_abbr_and_session.html
    '''
    if not request.GET:
        return render(request, templatename('search_results_no_query'),
                      {'abbr': abbr})

    search_text = request.GET['search_text']

    # First try to get by bill_id.
    if re.search(r'\d', search_text):
        url = '/%s/bills?' % abbr
        url += urllib.urlencode([('search_text', search_text)])
        return redirect(url)

    else:
        found_by_id = False
        kwargs = {}
        if abbr != 'all':
            kwargs['abbr'] = abbr
        bill_results = Bill.search(search_text, **kwargs)

        # add sorting
        bill_results = bill_results.sort([('action_dates.last', -1)])

        # Limit the bills if it's a search.
        more_bills_available = (5 < bill_results.count())
        bill_results = bill_results.limit(5)

        # See if any legislator names match.
        spec = {'full_name': {'$regex': search_text, '$options': 'i'}}
        if abbr != 'all':
            spec[settings.LEVEL_FIELD] = abbr
        legislator_results = db.legislators.find(spec)
        more_legislators_available = (5 < legislator_results.count())
        legislator_results = legislator_results.limit(5)

    if abbr != 'all':
        metadata = Metadata.get_object(abbr)
    else:
        metadata = None

    return render(
        request, templatename('search_results_bills_legislators'),
        dict(search_text=search_text,
             abbr=abbr,
             metadata=metadata,
             found_by_id=found_by_id,
             bill_results=bill_results,
             more_bills_available=more_bills_available,
             legislators_list=legislator_results,
             more_legislators_available=more_legislators_available,
             column_headers_tmplname=None,  # not used
             rowtemplate_name=templatename('bills_list_row_with'
                                           '_abbr_and_session'),
             show_chamber_column=True,
             nav_active=None))


class ShowMoreLegislators(ListViewBase):
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
        - billy/web/public/object_list.html
        - billy/web/public/legislators_list_row.html
    '''
    template_name = templatename('object_list')
    rowtemplate_name = templatename('legislators_list_row')
    nav_active = None
    column_headers_tmplname = templatename('legislators_list_headers')
    description_template = '''
        <a href={{metadata.get_absolute_url}}>{{metadata.name}}</a>
        legislator names containing "{{request.GET.search_text}}"'''
    title_template = striptags(description_template)

    def get_queryset(self):
        abbr = self.kwargs['abbr']
        search_text = self.request.GET['search_text']

        # See if any legislator names match.
        spec = {'full_name': {'$regex': search_text, '$options': 'i'}}
        if abbr != 'all':
            spec[settings.LEVEL_FIELD] = abbr
        legislator_results = db.legislators.find(spec)
        return CursorPaginator(legislator_results, show_per_page=10,
                               page=int(self.request.GET.get('page', 1)))
