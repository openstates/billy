from pupa.scrape import Jurisdiction
from openstates.people import OpenstatesPersonScraper


class PersonScraper(OpenstatesPersonScraper):
    state = 'ak'


class Ak(Jurisdiction):
    jurisdiction_id = "ocd-jurisdiction/country:us/state:ak/legislature"
    name = "Alaska State Legislature"
    url = "http://w3.legis.state.ak.us/"
    scrapers = {
        "people": PersonScraper,
    }
    chambers = {
        'upper': {
        },
    }
