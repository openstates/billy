from pupa.scrape import Jurisdiction, Organization
from openstates.base import OpenstatesBaseScraper
from openstates.people import OpenstatesPersonScraper
from openstates.bills import OpenstatesBillScraper

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

    # timezone
    # legislature_name
    # legislature_url
    # chambers.title
    # terms?

    # make orgs
    orgs = []
    for otype in ('upper', 'lower'):
        if otype in metadata['chambers']:
            org = Organization(metadata['name'] + ' ' + chamber_name(a_state, otype),
                               classification='legislature', chamber=otype)
            orgs.append(org)

    leg_sessions = []
    for td in metadata['terms']:
        for s in td['sessions']:
            session = {'identifier': s,
                       'name': metadata['session_details'][s]['display_name'],
                       'start_date': metadata['session_details'][s].get('start_date', ''),
                       'end_date': metadata['session_details'][s].get('end_date', ''),
                      }
            leg_sessions.append(session)

    # make scrapers
    class PersonScraper(OpenstatesPersonScraper):
        state = a_state
    class BillScraper(OpenstatesBillScraper):
        state = a_state

    class StateJuris(Jurisdiction):
        division_id = 'ocd-division/country:us/state:' + a_state
        classification = 'government'
        name = metadata['name']
        organizations = orgs

        scrapers = {'people': PersonScraper, 'bills': BillScraper}
        parties = [{'name': 'Republican'}, {'name': 'Democratic'}]
        legislative_sessions = leg_sessions

    return StateJuris
