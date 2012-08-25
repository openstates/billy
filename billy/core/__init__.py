from billy.conf import settings
import pymongo

db = None

def _configure_db(host, port, db_name):
    global db
    conn = pymongo.Connection(host, port)
    db = conn[db_name]

_configure_db(settings.MONGO_HOST, settings.MONGO_PORT,
              settings.MONGO_DATABASE)
