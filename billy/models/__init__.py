from .base import db, feeds_db, _model_registry_by_collection, DoesNotExist
from .metadata import Metadata
from .bills import Bill
from .events import Event
from .legislators import Legislator
from .committees import Committee
from .reports import Report
from .feeds import FeedEntry

from pymongo.son_manipulator import SONManipulator

__all__ = [db, Metadata, Bill, Event, Legislator, DoesNotExist, Committee,
           Report, FeedEntry]


class Transformer(SONManipulator):
    def transform_outgoing(self, son, collection,
                           mapping=_model_registry_by_collection):
        try:
            return mapping[collection.name](son)
        except KeyError:
            return son

transformer = Transformer()
db.add_son_manipulator(transformer)
feeds_db.add_son_manipulator(transformer)
