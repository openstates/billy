import sys
import time

from oyster.tasks import ExternalStoreTask
from superfastmatch import Client

from billy.conf import settings

for p in settings.SCRAPER_PATHS:
    sys.path.insert(0, p)

class SuperFastMatchTask(ExternalStoreTask):

    external_store = 'superfastmatch'
    sfm_client = Client('http://ec2-174-129-105-103.compute-1.amazonaws.com/')

    def upload_document(self, doc_id, filedata, metadata):
        # from {state}.fulltext import extract_text
        extract_text = __import__('%s.fulltext' % metadata['state'],
                                  fromlist=['extract_text']).extract_text
        _id = int(time.time()*10000)
        extracted = extract_text(filedata, metadata)
        self.sfm_client.add(1, _id, extracted, defer=True,
                            **metadata)
        return _id
