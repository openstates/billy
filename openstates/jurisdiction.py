from pupa.scrape import Jurisdiction, Organization
from openstates.base import OpenstatesBaseScraper
from openstates.people import OpenstatesPersonScraper
from openstates.events import OpenstatesEventScraper
from openstates.bills import OpenstatesBillScraper

POSTS = {
    'ak': {'lower': range(1, 41), 'upper': (chr(n) for n in range(65, 85))},
    'al': {'lower': range(1, 106), 'upper': range(1, 36)},
    'az': {'lower': range(1, 31), 'upper': range(1, 31)},
    'ar': {'lower': range(1, 101), 'upper': range(1, 36)},
    # ca - big
    'co': {'lower': range(1, 66), 'upper': range(1, 36)},
    'ct': {'lower': range(1, 152), 'upper': range(1, 37)},
    'de': {'lower': range(1, 42), 'upper': range(1, 22)},
    'fl': {'lower': range(1, 121), 'upper': range(1, 41)},
    'ga': {'lower': range(1, 181), 'upper': range(1, 57)},
    'hi': {'lower': range(1, 52), 'upper': range(1, 27)},
    'id': {'lower': range(1, 36), 'upper': range(1, 36)},
    # il - big
    'in': {'lower': range(1, 101), 'upper': range(1, 51)},
    'ia': {'lower': range(1, 101), 'upper': range(1, 51)},
    'ks': {'lower': range(1, 126), 'upper': range(1, 41)},
    'ky': {'lower': range(1, 101), 'upper': range(1, 39)},
    'la': {'lower': range(1, 106), 'upper': range(1, 41)},
    'me': {'lower': range(1, 152), 'upper': range(1, 36)},
    # ma - weird districts
    'mi': {'lower': range(1, 111), 'upper': range(1, 39)},
    # mn - weird districts
    'ms': {'lower': range(1, 123), 'upper': range(1, 53)},
    'mo': {'lower': range(1, 164), 'upper': range(1, 35)},
    'mt': {'lower': range(1, 101), 'upper': range(1, 51)},
    'ne': {'upper': range(1, 50)},


    'nc': {'lower': range(1, 121), 'upper': range(1, 51)},
    'tx': {'lower': range(1, 151), 'upper': range(1, 32)},
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
                    #'events': EventScraper,
                   }
        parties = [{'name': 'Republican'},
                   {'name': 'Democratic'},
                   {'name': 'Independent'},
                   {'name': 'Green'},
                  ]
        legislative_sessions = leg_sessions

        def get_organizations(self):
            legislature = Organization(metadata['legislature_name'], classification='legislature')
            yield legislature
            executive = Organization(metadata['name'] + ' Executive Branch',
                                     classification='executive')
            yield executive

            self._legislature = legislature
            self._executive = executive

            for otype in ('upper', 'lower'):
                if otype in metadata['chambers']:
                    org = Organization(metadata['name'] + ' ' + chamber_name(a_state, otype),
                                       classification=otype, parent_id=legislature._id)
                    for post in POSTS[a_state][otype]:
                        org.add_post(str(post), metadata['chambers'][otype]['title'])
                    yield org

    return StateJuris
