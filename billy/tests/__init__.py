from billy.conf import settings
from billy import db
import pymongo

def setup():
    host = settings.MONGO_HOST
    port = settings.MONGO_PORT
    db_name = settings.MONGO_DATABASE + '_test'

    db._db = pymongo.Connection(host, port)[db_name]

def teardown():
    host = settings.MONGO_HOST
    port = settings.MONGO_PORT
    db_name = settings.MONGO_DATABASE + '_test'

    pymongo.Connection(host, port).drop_database(db_name)
