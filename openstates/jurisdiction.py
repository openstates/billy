from pupa.scrape import Jurisdiction, Organization
from openstates.base import OpenstatesBaseScraper
from openstates.people import OpenstatesPersonScraper
from openstates.events import OpenstatesEventScraper
from openstates.bills import OpenstatesBillScraper

POSTS = {
    'ne': range(1, 50),
    'dc': ['Ward 1', 'Ward 2', 'Ward 3', 'Ward 4', 'Ward 5', 'Ward 6', 'Ward 7', 'Ward 8',
           'At-Large', 'Chairman']
}

def chamber_name(state, chamber):
    if state in ('ne', 'dc'):
        raise ValueError(state)

    if chamber == 'lower':
        if state in ('ca', 'ny', 'wi'):
            return 'State Assembly'
        elif state in ('md', 'va', 'wv'):
            return 'House of Delegates'
        elif state == 'nv':
            return 'Assembly'
        elif state == 'nj':
            return 'General Assembly'
        else:
            return 'House of Representatives'   # 41 of these
    elif chamber == 'upper':
        if state in ('ca', 'ga', 'la', 'ms', 'ny', 'or', 'pa', 'wa', 'wi'):
            return 'State Senate'
        else:
            return 'Senate'


def make_jurisdiction(a_state):

    osbs = OpenstatesBaseScraper(None, None)
    metadata = osbs.api('metadata/{}?'.format(a_state))

    # chambers.title

    leg_sessions = []
    for td in metadata['terms']:
        for s in td['sessions']:
            session = {'identifier': s,
                       'name': metadata['session_details'][s]['display_name'],
                       'start_date': metadata['session_details'][s].get('start_date', '')[:10],
                       'end_date': metadata['session_details'][s].get('end_date', '')[:10],
                      }
            leg_sessions.append(session)

    # make scrapers
    class PersonScraper(OpenstatesPersonScraper):
        state = a_state
    class BillScraper(OpenstatesBillScraper):
        state = a_state
    class EventScraper(OpenstatesEventScraper):
        state = a_state

    class StateJuris(Jurisdiction):
        division_id = 'ocd-division/country:us/state:' + a_state
        classification = 'government'
        name = metadata['name']
        timezone = metadata['capitol_timezone']
        scrapers = {'people': PersonScraper,
                    'bills': BillScraper,
                   }
        parties = [{'name': 'Republican'},
                   {'name': 'Democratic'},
                   {'name': 'Independent'},
                   {'name': 'Green'},
                   {'name': 'Progressive'},
                   {'name': 'Democratic-Farmer-Labor'},
                   {'name': 'Republican/Democratic'},
                  ]
        legislative_sessions = leg_sessions

        def get_organizations(self):
            legislature = Organization(metadata['legislature_name'], classification='legislature')
            executive = Organization(metadata['name'] + ' Executive Branch',
                                     classification='executive')
            yield executive

            self._legislature = legislature
            self._executive = executive

            if a_state not in ('ne', 'dc'):
                for otype in ('upper', 'lower'):
                    if otype in metadata['chambers']:
                        org = Organization(metadata['name'] + ' ' + chamber_name(a_state, otype),
                                           classification=otype, parent_id=legislature._id)
                        districts = osbs.api('districts/{}/{}?'.format(a_state, otype))
                        for district in districts:
                            org.add_post(district['name'], metadata['chambers'][otype]['title'])

                        # old posts
                        if a_state == 'vt' and otype == 'lower':
                            old_posts = ['Washington-Chittenden-1', 'Addison-Rutland-1',
                                         'Bennington-5', 'Bennington-Rutland-1',
                                         'Caledonia-Washington-1', 'Chittenden-1-1',
                                         'Chittenden-1-2', 'Chittenden-3-1', 'Chittenden-3-10',
                                         'Chittenden-3-2', 'Chittenden-3-3', 'Chittenden-3-4',
                                         'Chittenden-3-5', 'Chittenden-3-6', 'Chittenden-3-7',
                                         'Chittenden-3-8', 'Chittenden-3-9', 'Chittenden-4',
                                         'Chittenden-8', 'Chittenden-9', 'Franklin-3',
                                         'Grand Isle-Chittenden-1-1', 'Lamoille-Washington-1',
                                         'Lamoille-4', 'Orange-Addison-1', 'Orange-Caledonia-1',
                                         'Orleans-Caledonia-1', 'Orleans-Franklin-1',
                                         'Rutland-1-1', 'Rutland-1-2', 'Rutland-7', 'Rutland-8',
                                         'Washington-3-1', 'Washington-3-2', 'Washington-3-3',
                                         'Windham-2', 'Windham-3-1', 'Windham-3-2', 'Windham-3-3',
                                         'Windham-Bennington-Windsor-1', 'Windham-Bennington-1',
                                         'Windsor-Rutland-1', 'Windsor-Rutland-2', 'Windsor-1-1',
                                         'Windsor-1-2', 'Windsor-3', 'Windsor-4', 'Windsor-6-1',
                                         'Windsor-6-2']
                            end_date = '2012-05-01'
                        elif a_state == 'vt' and otype == 'upper':
                            old_posts = ['Grand Isle']
                            end_date = '2012-05-01'
                        else:
                            old_posts = []

                        for p in old_posts:
                            org.add_post(p, metadata['chambers'][otype]['title'],
                                         end_date=end_date)

                        yield org
            else:
                for post in POSTS[a_state]:
                    self._legislature.add_post(str(post), metadata['chambers']['upper']['title'])


            yield legislature

    STATE_EVENT_BLACKLIST = set([
        "de",  # There is a scraper, but it appears it's never got any
        # real data. The OpenStates API returns no events (rightly so).
        # This should be removed once that's not true anymore.
        #   - PRT // Jul 28th, 2014.
    ])

    if ('events' in metadata['feature_flags'] and
            a_state not in STATE_EVENT_BLACKLIST):
        StateJuris.scrapers['events'] = EventScraper

    return StateJuris
