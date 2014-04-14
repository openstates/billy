from pupa.scrape import Legislator
from .base import OpenstatesBaseScraper


class OpenstatesPersonScraper(OpenstatesBaseScraper):
    def scrape_legislator(self, legislator_id):
        old = self.api('legislators/' + legislator_id + '?')
        old.pop('country', None)
        old.pop('level', None)

        new = Legislator(name=old['full_name'], image=old['photo_url'])
        return new

    def scrape(self):
        method = 'legislators/?state={}&fields=id'.format(self.state)
        for result in self.api(method):
            yield self.scrape_legislator(result['id'])
