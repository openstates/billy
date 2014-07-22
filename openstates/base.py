from pupa.scrape import Scraper
import os.path
import os


class OpenstatesBaseScraper(Scraper):
    """
    This is the OpenStates base Pupa scraper.

    This is used to centralize the OpenStates scrapers into a single place,
    and offload as much as we can here.
    """

    def __init__(self, *args, **kwargs):
        super(OpenstatesBaseScraper, self).__init__(*args, **kwargs)

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
        """
        Preform an API call against `method`. Return the parsed json
        data.
        """
        url = 'http://openstates.org/api/v1/{}{}apikey={}'.format(
            method,
            "&" if "?" in method else "?",
            self.apikey
        )
        try:
            return self.get(url).json()
        except ValueError:
            raise ValueError('error retrieving ' + url)
