from billy.conf import settings
from billy import db
from billy.models import base
import pymongo


def setup():
    host = settings.MONGO_HOST
    port = settings.MONGO_PORT
    settings.MONGO_DATABASE += '_test'
    db_name = settings.MONGO_DATABASE

    db._db = pymongo.Connection(host, port)[db_name]
    base.db = db._db


def teardown():
    host = settings.MONGO_HOST
    port = settings.MONGO_PORT
    db_name = settings.MONGO_DATABASE

    assert db_name.endswith('_test')

    pymongo.Connection(host, port).drop_database(db_name)
