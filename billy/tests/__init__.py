from billy.conf import settings
# modify the db name upon initial import (this file has to run first)
settings.MONGO_DATABASE += '_test'
import pymongo


def teardown():
    host = settings.MONGO_HOST
    port = settings.MONGO_PORT
    db_name = settings.MONGO_DATABASE

    assert db_name.endswith('_test')

    pymongo.Connection(host, port).drop_database(db_name)
