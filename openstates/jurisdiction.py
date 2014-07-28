from pupa.scrape import Jurisdiction, Organization
from openstates.base import OpenstatesBaseScraper
from openstates.people import OpenstatesPersonScraper
from openstates.events import OpenstatesEventScraper
from openstates.bills import OpenstatesBillScraper

POSTS = {
    'ne': {'upper': range(1, 50)},
    'dc': {'upper': ['Ward 1', 'Ward 2', 'Ward 3', 'Ward 4', 'Ward 5', 'Ward 6', 'Ward 7',
                     'Ward 8', 'At-Large', 'Chairman']}
}

def chamber_name(state, chamber):
    if state in ('ne', 'dc', 'pr'):
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
                        yield org
            else:
                for post in POSTS[a_state]['upper']:
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
