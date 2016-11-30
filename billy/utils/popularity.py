import datetime
from billy.core import db


class Counter(object):

    def __init__(self, db, collection_name='popularity_counts'):
        self.counts = getattr(db, collection_name)

    def inc(self, type_name, obj_id, **kwargs):
        self.counts.update({
            'type': type_name, 'obj_id': obj_id,
            'date': datetime.datetime.utcnow().date().toordinal()},
            {'$inc': {'count': 1}, '$set': kwargs},
            upsert=True, w=0, j=False)

    def top(self, type_name, n=1, days=None, with_counts=False, **kwargs):
        kwargs['type'] = type_name
        if days:
            kwargs['date'] = {
                '$gt': datetime.datetime.utcnow().date().toordinal() - days}

        if with_counts:
            extract = lambda o: (o['obj_id'], o['count'])
        else:
            extract = lambda o: o['obj_id']
        return [extract(o) for o in
                self.counts.find(kwargs, {'_id': 0, 'obj_id': 1, 'count': 1})
                .sort([('count', -1)]).limit(n)]


counter = Counter(db)
