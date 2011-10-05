import time

from oyster.tasks import ExternalStoreTask
from superfastmatch import Client

class SuperFastMatchTask(ExternalStoreTask):

    external_store = 'superfastmatch'
    sfm_client = Client('http://ec2-174-129-105-103.compute-1.amazonaws.com/')

    def upload_document(self, doc_id, filedata, metadata):
        _id = int(time.time()*10000)
        self.sfm_client.add(1, _id, filedata, defer=True,
                            **metadata)
        return _id
