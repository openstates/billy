from billy.conf import settings
settings.MONGO_DATABASE += '_test'
from billy import db
from billy.models import base
import pymongo


def teardown():
    host = settings.MONGO_HOST
    port = settings.MONGO_PORT
    db_name = settings.MONGO_DATABASE

    assert db_name.endswith('_test')

    pymongo.Connection(host, port).drop_database(db_name)
