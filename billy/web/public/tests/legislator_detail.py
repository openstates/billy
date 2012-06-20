

import requests

from billy.models import db


def test_gets(states):
    for leg in db.legislators.find({}, ['_id']):
        requests.get('http://127.0.0.1:8000/ca/legislator/%s/' % leg['_id'])


if __name__ == '__main__':

    import sys

    test_gets(sys.argv[1:])
