from pupa.scrape import Legislator
from .base import OpenstatesBaseScraper


class OpenstatesPersonScraper(OpenstatesBaseScraper):
    def scrape_legislator(self, legislator_id):
        old = self.api('legislators/' + legislator_id + '?')
        old.pop('country', None)
        old.pop('level', None)
        district = old.pop('district', None)
        chamber = old.pop('chamber', None)
        photo = old.get('photo_url')

        kwargs = {}
        if photo:
            kwargs['image'] = photo

        new = Legislator(name=old['full_name'], district=district, chamber=chamber, **kwargs)
        for source in old.pop('sources'):
            new.add_source(**source)

        return new

    def scrape(self):
        method = 'legislators/?state={}&fields=id'.format(self.state)
        for result in self.api(method):
            yield self.scrape_legislator(result['id'])
