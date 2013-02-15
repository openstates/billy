from itertools import islice

import pymongo

from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.utils.html import strip_tags
from django.template.defaultfilters import truncatewords

from billy.models import db
from billy.utils import get_domain


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))


class GenericListFeed(Feed):

    def get_object(self, request, **kwargs):
        try:
            collection = getattr(db, kwargs['collection_name'])
        except KeyError:
            collection = getattr(db, self.collection_name)

        try:
            obj = collection.find_one(kwargs['_id'])
        except KeyError:
            obj = collection.find_one(kwargs['abbr'])

        if obj is None:
            raise FeedDoesNotExist
        return obj

    def link(self, obj):
        return obj.get_absolute_url()

    def items(self, obj):
        attr = getattr(obj, self.query_attribute)
        if callable(attr):
            kwargs = {'limit': 100}
            sort = getattr(self, 'sort', None)
            if sort is not None:
                kwargs['sort'] = sort
            return attr(**kwargs)
        else:
            return attr


class VotesListFeed(GenericListFeed):
    collection_name = 'legislators'
    query_attribute = 'votes_manager'
    sort = [('date', pymongo.DESCENDING)]

    def title(self, obj):
        s = u"{0}: Votes by {1}."
        return s.format(get_domain(), obj.display_name())

    description = title

    def item_description(self, item):
        template = u'''
        <b>motion:</b> {0}</br>
        <b>bill description:</b> {1}
        '''
        return template.format(item['motion'], item.bill()['title'])

    def item_title(self, item):
        return '%s (%s)' % (
            item.bill()['bill_id'],
            item['date'].strftime('%B %d, %Y'))


class NewsListFeed(GenericListFeed):
    collection_name = 'legislators'
    query_attribute = 'feed_entries'

    def title(self, obj):
        s = u"{0}: News stories mentioning {1}."
        return s.format(get_domain(), obj.display_name())

    description = title

    def item_link(self, item):
        return item['link']

    def item_description(self, item):
        return truncatewords(strip_tags(item['summary']), 100)

    def item_title(self, item):
        published = item.published()
        if published is not None:
            published = published.strftime('%B %d, %Y')
        else:
            published = ''
        return '%s (%s)' % (item['title'], published)


class EventsFeed(GenericListFeed):
    collection_name = 'metadata'
    query_attribute = 'events'

    def title(self, obj):
        s = u"{0}: {1} legislative events."
        return s.format(get_domain(), obj.display_name())

    description = title

    def item_description(self, item):
        return truncatewords(item['description'], 100)

    def item_title(self, item):
        return item['when'].strftime('%B %d, %Y')
