from collections import namedtuple
import itertools
from django.http import Http404


PageLink = namedtuple('PageLink', 'string, page_number clickable')


class PaginatorBase(object):

    def __init__(self, page=1, show_per_page=20):
        self.skip = (page - 1) * show_per_page
        self.show_per_page = show_per_page
        self.current_page = page
        self.limit = show_per_page

    def _previous_pages_count(self):
        'A generator of previous page integers.'
        skip = self.skip
        if skip == 0:
            return 0
        count, remainder = divmod(skip, self.limit)
        return count

    def _subsequent_pages_count(self):
        count, remainder = divmod(self.count, self.limit)
        if remainder:
            count += 1
        return count

    def previous_pages_numbers(self):
        'A generator of previous page integers.'
        count = self._previous_pages_count() + 1
        for i in reversed(range(1, count)):
            yield i

    def subsequent_pages_numbers(self):
        for page in xrange(self.current_page + 1,
                           self._subsequent_pages_count() + 1):
            yield page

    @property
    def last_page(self):
        last_page, remainder = divmod(self.count, self.limit)
        if remainder:
            last_page += 1
        return last_page

    @property
    def next_page(self):
        return self.current_page + 1

    @property
    def previous_page(self):
        return self.current_page - 1

    @property
    def range_start(self):
        '''"Showing 40-50 of 234 results
                    ^
        '''
        start = (self.current_page - 1) * self.show_per_page
        return start + 1

    @property
    def range_end(self):
        '''"Showing 40 - 50 of 234 results
                         ^
        '''
        count = self.count
        range_end = self.range_start + self.limit - 1
        if count < range_end:
            range_end = count
        return range_end

    @property
    def total_count(self):
        '''"Showing 40 - 50 of 234 results
                               ^
        '''
        return self.count

    @property
    def has_next(self):
        return self.current_page != self.last_page

    @property
    def has_previous(self):
        return self.current_page != 1

    def pagination_data(self, max_number_of_links=7):
        '''Returns a generator of tuples (string, page_number, clickable),
        where `string` is the text of the html link, `page_number` is
        the number of the page the link points to, and `clickable` is
        a boolean indicating whether the link is clickable or not.
        '''
        div, mod = divmod(max_number_of_links, 2)
        if not mod == 1:
            msg = 'Max number of links must be odd, was %r.'
            raise ValueError(msg % max_number_of_links)

        midpoint = (max_number_of_links - 1) / 2
        current_page = self.current_page
        last_page = self.last_page

        if current_page > last_page:
            raise Http404('invalid page number')
            current_page = last_page

        show_link_firstpage = midpoint < current_page
        show_link_previouspage = 1 < current_page
        show_link_lastpage = current_page < (self.last_page - midpoint)
        show_link_nextpage = current_page < last_page

        extra_room_previous = midpoint - current_page
        if extra_room_previous < 0:
            extra_room_previous = 0
        if not show_link_firstpage:
            extra_room_previous += 1
        if not show_link_previouspage:
            extra_room_previous += 1

        extra_room_subsequent = current_page - last_page + midpoint
        extra_room_subsequent = max([extra_room_subsequent, 0])
        if not show_link_nextpage:
            extra_room_subsequent += 1
        if not show_link_lastpage:
            extra_room_subsequent += 1

        if self.current_page == 1:
            yield PageLink(string=1, page_number=1, clickable=False)
        else:
            # The  "first page" link.
            if show_link_firstpage:
                #[<<] [<] [7] [8] [9] 10 [11] ...'
                #  ^
                yield PageLink(string=u"\u00AB", page_number=1, clickable=True)

            if show_link_previouspage:
                # The "previous page" link.
                #[<<] [<] [7] [8] [9] 10 [11] ...'
                #      ^
                yield PageLink(string=u"\u2039",
                               page_number=self.previous_page,
                               clickable=True)

        # Up to `midpoint + extra_room_subsequent` previous page numbers.
        previous = itertools.islice(self.previous_pages_numbers(),
                                    midpoint + extra_room_subsequent)
        previous = list(previous)[::-1]

        for page_number in previous:
            yield PageLink(string=page_number,
                           page_number=page_number, clickable=True)

        # The current page, clickable.
        if current_page != 1:
            yield PageLink(string=current_page,
                           page_number=current_page, clickable=False)

        # Up to `midpoint + extra_room_previous` subsequent page numbers.
        subsequent_count = midpoint + extra_room_previous
        _subsequent_pages_count = self._subsequent_pages_count
        if _subsequent_pages_count < subsequent_count:
            subsequent_count = _subsequent_pages_count

        for page_number in itertools.islice(self.subsequent_pages_numbers(),
                                            subsequent_count):
            yield PageLink(string=page_number,
                           page_number=page_number, clickable=True)

        if show_link_nextpage:
            yield PageLink(string=u"\u203A",
                           page_number=current_page + 1,
                           clickable=True)

        if show_link_lastpage:
            yield PageLink(string=u"\u00BB",
                           page_number=last_page,
                           clickable=True)


class CursorPaginator(PaginatorBase):

    def __init__(self, cursor, *args, **kwargs):
        super(CursorPaginator, self).__init__(*args, **kwargs)
        self.cursor = cursor
        self.count = cursor.count()
        self._cached = False

    def __iter__(self):
        'The specific page of records.'
        if self._cached:
            for record in self._cache:
                yield record
            return

        else:
            cache = []
        for record in self.cursor.skip(self.skip).limit(self.limit):
            yield record
            cache.append(record)

        self._cached = True
        self._cache = cache


class BillSearchPaginator(PaginatorBase):

    def __init__(self, result, *args, **kwargs):
        super(BillSearchPaginator, self).__init__(*args, **kwargs)
        self.result = result
        self.count = len(result)
        self._cached = False

    def __iter__(self):
        'The specific page of records.'
        if self._cached:
            for record in self._cache:
                yield record
            return
        else:
            cache = []

        for record in self.result[self.skip:self.skip + self.limit]:
            yield record
            cache.append(record)

        self._cached = True
        self._cache = cache
