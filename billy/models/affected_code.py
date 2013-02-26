from operator import itemgetter
from itertools import groupby
from collections import defaultdict


class _DetailsItem(dict):

    def display(self):
        chunks = []
        if self.get('supernodes'):
            add_of = False
            for division, enum in self['supernodes'][::-1]:
                text = '%s <a href="%s">%s</a>'
                chunks.append(text % (division, self['url'], enum))
                if add_of:
                    chunks.append('of')
                    add_of = True

        if self.get('verb') != 'add' and self['url']:
            text = '<a href="{url}">{enum}</a>'
            chunks.append(text.format(**self))
        else:
            if self.get('supernodes'):
                chunks.append(', ')
                chunks.append(self['name'])
            chunks.append(self['enum'])
        return ' '.join(chunks)


class SourceChanges(object):
    '''Models a list of affected_code details dicts grouped by the source
    (i.e., code or session_law, etc.) they would modify.
    '''
    def __init__(self, bill, source, details):
        self.source = source
        self.details = details
        self.bill = bill

    def display(self):
        method = getattr(self, self.source + '_display', self.generic_display)
        return method()

    def generic_display(self):
        display_name = self.bill.metadata['laws']
        display_name = display_name.get(self.source, self.source)
        display_name = display_name['display_name']
        chunks = [display_name]
        if len(self.details) == 1:
            chunks.append(' &sect; ')
        elif len(self.details) > 1:
            chunks.append(' &sect;&sect; ')
        for detail in self.details:
            chunks.append(detail.display())
            chunks.append('; ')

        chunks[-1] = '.'
        if 4 < len(chunks):
            chunks.insert(-3, ', and ')
            del chunks[-3]

        return ''.join(chunks)


def affected_code(bill):

    data = dict(add=defaultdict(list),
                amend=defaultdict(list),
                repeal=defaultdict(list))
    details = map(_DetailsItem, bill['+affected_code']['details'])
    for verb, details in groupby(details, itemgetter('verb')):
        print verb
        by_source = groupby(details, itemgetter('source_id'))
        for source, details in by_source:

            if source not in data[verb]:
                source_changes = SourceChanges(bill, source, list(details))
                data[verb][source] = source_changes
            else:
                source_changes = data[verb][source]
                source_changes.details += list(details)

    # Kill defaultdict.
    for key in list(data):
        data[key] = dict(data[key])
    return data


