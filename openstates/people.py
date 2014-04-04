from pupa.scrape import Scraper, Legislator


class OpenstatesPersonScraper(Scraper):

    def api(self, method):
        url = 'http://openstates.org/api/v1/' + method + '&apikey=' + self.apikey
        return self.get(url).json()

    def scrape(self, apikey=None):
        if apikey:
            self.apikey = apikey
        if not self.apikey:
            print('apikey not set')
            return

        # TODO: change this to just get ids, then scrape legislator can take an id
        # and get the data it it leaving behind here
        method = 'legislators/?state={}&fields=id'.format(self.state)
        for result in self.api(method):
            yield self.scrape_legislator(result['id'])

    def scrape_legislator(self, legislator_id):
        old = self.api('legislators/' + legislator_id + '?')
        old.pop('country', None)
        old.pop('level', None)

        new = Legislator(name=old['full_name'], image=old['photo_url'])
        return new
