from pupa.scrape import Jurisdiction, Organization
from openstates.base import OpenstatesBaseScraper
from openstates.people import OpenstatesPersonScraper
from openstates.events import OpenstatesEventScraper
from openstates.bills import OpenstatesBillScraper

POSTS = {
    # ca - big
    # il - big
    # ma - weird districts
    # mn - weird districts
    # nh - weird districts
    'ak': {'lower': range(1, 41), 'upper': (chr(n) for n in range(65, 85))},
    'al': {'lower': range(1, 106), 'upper': range(1, 36)},
    'ar': {'lower': range(1, 101), 'upper': range(1, 36)},
    'az': {'lower': range(1, 31), 'upper': range(1, 31)},
    'co': {'lower': range(1, 66), 'upper': range(1, 36)},
    'ct': {'lower': range(1, 152), 'upper': range(1, 37)},
    'de': {'lower': range(1, 42), 'upper': range(1, 22)},
    'fl': {'lower': range(1, 121), 'upper': range(1, 41)},
    'ga': {'lower': range(1, 181), 'upper': range(1, 57)},
    'hi': {'lower': range(1, 52), 'upper': range(1, 27)},
    'ia': {'lower': range(1, 101), 'upper': range(1, 51)},
    'id': {'lower': range(1, 36), 'upper': range(1, 36)},
    'in': {'lower': range(1, 101), 'upper': range(1, 51)},
    'ks': {'lower': range(1, 126), 'upper': range(1, 41)},
    'ky': {'lower': range(1, 101), 'upper': range(1, 39)},
    'la': {'lower': range(1, 106), 'upper': range(1, 41)},
    'me': {'lower': range(1, 152), 'upper': range(1, 36)},
    'mi': {'lower': range(1, 111), 'upper': range(1, 39)},
    'mo': {'lower': range(1, 164), 'upper': range(1, 35)},
    'ms': {'lower': range(1, 123), 'upper': range(1, 53)},
    'mt': {'lower': range(1, 101), 'upper': range(1, 51)},
    'nc': {'lower': range(1, 121), 'upper': range(1, 51)},
    'ne': {'upper': range(1, 50)},
    'nj': {'lower': range(1, 41), 'upper': range(1, 41)},
    'nm': {'lower': range(1, 71), 'upper': range(1, 43)},
    'nv': {'lower': range(1, 43), 'upper': range(1, 22)},
    'ok': {'lower': range(1, 102), 'upper': range(1, 49)},
    'ri': {'lower': range(1, 76), 'upper': range(1, 39)},
    'sc': {'lower': range(1, 125), 'upper': range(1, 47)},
    'sd': {'lower': range(1, 36), 'upper': range(1, 36)},
    'tx': {'lower': range(1, 151), 'upper': range(1, 32)},
    'ut': {'lower': range(1, 76), 'upper': range(1, 30)},
    'wa': {'lower': range(1, 50), 'upper': range(1, 50)},
    'wv': {'lower': range(1, 68), 'upper': range(1, 18)},
    'wy': {'lower': range(1, 61), 'upper': range(1, 31)},
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
            executive = Organization(metadata['name'] + ' Executive Branch',
                                     classification='executive')
            yield executive

            self._legislature = legislature
            self._executive = executive

            if a_state != 'ne':
                for otype in ('upper', 'lower'):
                    if otype in metadata['chambers']:
                        org = Organization(metadata['name'] + ' ' + chamber_name(a_state, otype),
                                           classification=otype, parent_id=legislature._id)
                        districts = osbs.api('districts/{}/{}?'.format(a_state, otype))
                        for district in districts:
                            org.add_post(district['name'], metadata['chambers'][otype]['title'])
                        #for post in POSTS[a_state][otype]:
                        #    org.add_post(str(post), metadata['chambers'][otype]['title'])
                        yield org
            else:
                for post in POSTS[a_state]['upper']:
                    self._legislature.add_post(str(post), metadata['chambers']['upper']['title'])

            yield legislature


    return StateJuris
