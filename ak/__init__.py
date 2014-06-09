from pupa.scrape import Jurisdiction, Organization, Post
from openstates.people import OpenstatesPersonScraper


class PersonScraper(OpenstatesPersonScraper):
    state = 'ak'


house = Organization('Alaska State House', classification='legislature', chamber='lower')
senate = Organization('Alaska State Senate', classification='legislature', chamber='upper')


class Alaska(Jurisdiction):
    division_id = "ocd-division/country:us/state:ak"
    classification = "government"
    name = "Alaska State Legislature"
    url = "http://w3.legis.state.ak.us/"

    scrapers = {
        "people": PersonScraper,
    }

    organizations = [house, senate]
    posts = ([Post(label=str(n), role='Representative', organization_id=house._id)
              for n in range(1, 41)] +
             [Post(label=chr(n), role='Senator', organization_id=senate._id)
              for n in range(65, 85)])
