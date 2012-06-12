import operator
from itertools import islice

from django.contrib.syndication.views import Feed, FeedDoesNotExist
from django.utils.html import strip_tags

from billy.models import db


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
            obj = collection.find_one(kwargs['id'])
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
            return attr()
        else:
            return attr


class BillsFeed(GenericListFeed):

    def item_title(self, item):
        return item['bill_id']

    def item_description(self, item):
        return item['title']


class SponsoredBillsFeed(BillsFeed):
    query_attribute = 'sponsored_bills'

    def title(self, obj):
        return u"OpenStates.org: Bills sponsored by " + obj.display_name()

    description = title


class BillsPassedLowerFeed(BillsFeed):
    query_attribute = 'bills_passed_lower'
    collection_name = 'metadata'

    def title(self, obj):
        s = u"OpenStates.org: Bills that have passed in the {0} {1}"
        return s.format(obj.display_name(), obj['lower_chamber_name'])

    description = title


class BillsPassedUpperFeed(BillsFeed):
    query_attribute = 'bills_passed_upper'
    collection_name = 'metadata'

    def title(self, obj):
        s = u"OpenStates.org: Bills that have passed in the {0} {1}"
        return s.format(obj.display_name(), obj['upper_chamber_name'])

    description = title


class BillsIntroducedLowerFeed(BillsFeed):
    query_attribute = 'bills_introduced_lower'
    collection_name = 'metadata'

    def title(self, obj):
        s = u"OpenStates.org: Bills introduced in the {0} {1}."
        return s.format(obj.display_name(), obj['lower_chamber_name'])

    description = title


class BillsIntroducedUpperFeed(BillsFeed):
    query_attribute = 'bills_introduced_upper'
    collection_name = 'metadata'

    def title(self, obj):
        s = u"OpenStates.org: Bills introduced in the {0} {1}."
        return s.format(obj.display_name(), obj['upper_chamber_name'])

    description = title


class BillsBySubjectFeed(BillsFeed):
    collection_name = 'metadata'

    def get_object(self, request, **kwargs):
        self.request = request
        self.kwargs = kwargs
        obj = super(BillsBySubjectFeed, self).get_object(request, **kwargs)
        return obj

    def title(self, obj):
        s = u"OpenStates.org: Bills related to {0}."
        return s.format(self.kwargs['subject'])

    def items(self, obj):
        return db.bills.find(
            {'state': self.kwargs['abbr'], 'subjects': self.kwargs['subject']})


class VotesListFeed(GenericListFeed):
    collection_name = 'legislators'
    query_attribute = 'votes_manager'

    def title(self, obj):
        s = u"OpenStates.org: Votes by {0}."
        return s.format(obj.display_name())

    description = title

    def item_description(self, item):
        template = u'''
        <b>motion:</b> {0}</br>
        <b>bill description:</b> {1}
        '''
        return template.format(item['motion'], item.bill['title'])

    def item_title(self, item):
        return '%s (%s)' % (
            item.bill['bill_id'],
            item['date'].strftime('%B %d, %Y'))

    def items(self, obj):
        return sorted(obj.votes_manager,
                      key=operator.itemgetter('date'),
                      reverse=True)


class NewsListFeed(GenericListFeed):
    collection_name = 'legislators'
    query_attribute = 'feed_entries'

    def title(self, obj):
        s = u"OpenStates.org: News stories mentioning {0}."
        return s.format(obj.display_name())

    description = title

    def item_link(self, item):
        return item['link']

    def item_description(self, item):
        return strip_tags(item['summary'])

    def item_title(self, item):
        return '%s (%s)' % (
            item['title'],
            item.published().strftime('%B %d, %Y'))

