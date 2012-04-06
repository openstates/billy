import sys
from billy.conf import settings
from billy.commands import BaseCommand


class Oysterize(BaseCommand):
    name = 'textextract'
    help = 'test text extraction on a document'

    def add_args(self):
        self.add_argument('module', help='module to load text extractor from')
        self.add_argument('filename', help='file to test text extraction on')

    def handle(self, args):
        # inject scraper paths so scraper module can be found
        for newpath in settings.SCRAPER_PATHS:
            sys.path.insert(0, newpath)
        module = __import__(args.module)

        extract_text = module.extract_text

        print extract_text({}, open(args.filename).read())
