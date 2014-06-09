from pupa.scrape import Jurisdiction, Organization, Post
from openstates.people import OpenstatesPersonScraper


class PersonScraper(OpenstatesPersonScraper):
    state = 'nc'


house = Organization('North Carolina State House', classification='legislature', chamber='lower')
senate = Organization('North Carolina State Senate', classification='legislature', chamber='upper')


class NorthCarolina(Jurisdiction):
    division_id = "ocd-division/country:us/state:nc"
    classification = "government"
    name = "North Carolina General Assembly"
    url = "http://ncleg.net"

    scrapers = {
        "people": PersonScraper,
    }
    parties = [{'name': 'Republican'}, {'name': 'Democratic'}]

    organizations = [house, senate]
    posts = ([Post(label=str(n), role='Representative', organization_id=house._id)
              for n in range(1, 121)] +
             [Post(label=str(n), role='Senator', organization_id=senate._id)
              for n in range(1, 51)])
