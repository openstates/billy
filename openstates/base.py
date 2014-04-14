from pupa.scrape import Scraper
import os.path
import os


class OpenstatesBaseScraper(Scraper):

    def __init__(self, *args, **kwargs):
        super(OpenstatesPersonScraper, self).__init__(*args, **kwargs)

        self.apikey = os.getenv('SUNLIGHT_API_KEY')
        if self.apikey is None:
            fp = os.path.expanduser("~/.sunlight.key")
            try:
                with open(fp, 'r') as fd:
                    self.apikey = fd.read().strip()
            except IOError:
                pass

        if self.apikey is None:
            raise ValueError(
                "No API key found in `SUNLIGHT_API_KEY` envvar or "
                "~/.sunlight.key"
            )

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
