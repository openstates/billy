import os
import sys
from billy.core import db
from billy.importers.metadata import import_metadata


def load_metadata():
    db.metadata.drop()
    sys.path.append(os.path.dirname(__file__))
    print sys.path[-1]
    import_metadata("ex")
    import_metadata("yz")
