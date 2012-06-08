from .base import db, _model_registry_by_collection, DoesNotExist
from .metadata import Metadata
from .bills import Bill
from .events import Event
from .legislators import Legislator
from .committees import Committee
from .reports import Report
from .feeds import FeedEntry

from pymongo.son_manipulator import SONManipulator

class Transformer(SONManipulator):
    def transform_outgoing(self, son, collection,
                           mapping=_model_registry_by_collection):
        try:
            return mapping[collection.name](son)
        except KeyError:
            return son

db.add_son_manipulator(Transformer())
