import os
from billy.core import db
from billy.importers.metadata import import_metadata


def load_metadata():
    db.metadata.drop()
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    import_metadata("ex", data_dir)
    import_metadata("yz", data_dir)
