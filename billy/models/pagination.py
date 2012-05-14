from collections import namedtuple
import itertools


PageLink = namedtuple('PageLink', 'token, page_number inactive')


class Paginator(object):

    def __init__(self, cursor, current_page=1, show_per_page=20):

        self.skip = (current_page - 1) * show_per_page
        self._cursor_count = cursor.count()
        self._cached = False

        self.current_page = current_page
        self.limit = show_per_page
        self.cursor = cursor

    def __iter__(self):
        'The specific page of records.'
        if self._cached:
            for record in self._cache:
                yield record
        else:
            cache = []
        for record in self.cursor.skip(self.skip).limit(self.limit):
            cache.append(record)
            yield record
        self._cached = True
        self._cache = cache

    def _previous_pages_count(self):
        'A generator of previous page integers.'
        skip = self.skip
        if skip == 0:
            return 0
        pages, remainder = divmod(skip, self.limit)
        return pages

    def _subsequent_pages_count(self):
        pages, remainder = divmod(self._cursor_count, self.limit)
        return pages

    def previous_pages_numbers(self):
        'A generator of previous page integers.'
        count = self._previous_pages_count() + 1
        for i in reversed(range(1, count)):
            yield i

    def subsequent_pages_numbers(self):
        first = self.current_page + 1
        for i in xrange(self._subsequent_pages_count()):
            yield i + first

    @property
    def last_page(self):
        last_page, _ = divmod(self._cursor_count, self.limit)
        return last_page

    @property
    def next_page(self):
        return self.current_page + 1

    @property
    def previous_page(self):
        return self.current_page - 1

    def pages_linkdata(self, max_number_of_links=11):

        div, mod = divmod(max_number_of_links, 2)
        if not mod == 1:
            msg = 'Max number of links must be odd, was %r.'
            raise ValueError(msg % max_number_of_links)

        midpoint = (max_number_of_links - 1) / 2
        current_page = self.current_page
        last_page = self.last_page

        show_link_firstpage = midpoint < current_page
        show_link_previouspage = 1 < current_page
        show_link_lastpage = current_page < (self._cursor_count - midpoint)
        show_link_nextpage = current_page < last_page

        extra_room_previous = midpoint - current_page
        if extra_room_previous < 0:
            extra_room_previous = 0
        extra_room_subsequent = current_page - (last_page - midpoint)
        if extra_room_subsequent < 0:
            extra_room_subsequent = 0

        if self.current_page == 1:
            yield PageLink(token=1, page_number=1, inactive=True)
        else:
            # The  "first page" link.
            if show_link_firstpage:
                #[<<] [<] [7] [8] [9] 10 [11] ...'
                #  ^
                yield PageLink(token=u"\u00AB", page_number=1, inactive=False)

            if show_link_previouspage:
                # The "previous page" link.
                #[<<] [<] [7] [8] [9] 10 [11] ...'
                #      ^
                yield PageLink(token=u"\u2039",
                               page_number=self.previous_page,
                               inactive=False)

        # Up to `midpoint + extra_room_subsequent` previous page numbers.
        previous = itertools.islice(self.previous_pages_numbers(),
                                    midpoint + extra_room_subsequent)
        previous = list(previous)[::-1]

        for page_number in previous:
            yield PageLink(token=page_number,
                           page_number=page_number, inactive=False)

        # The current page, inactive.
        yield PageLink(token=current_page,
                       page_number=current_page, inactive=True)

        # Up to `midpoint + extra_room_previous` subsequent page numbers.
        subsequent_count = midpoint + extra_room_previous
        print 'SUB', subsequent_count
        for page_number in itertools.islice(self.subsequent_pages_numbers(),
                                            subsequent_count):
            yield PageLink(token=page_number,
                           page_number=page_number, inactive=False)

        if show_link_nextpage:
            yield PageLink(token=u"\u203A",
                           page_number=current_page + 1,
                           inactive=False)

        if show_link_lastpage:
            yield PageLink(token=u"\u00BB",
                           page_number=last_page,
                           inactive=False)
