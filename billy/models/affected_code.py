from operator import itemgetter
from itertools import groupby
from collections import defaultdict


class _DetailsItem(dict):

    def display(self):
        method_name = self['source_id'] + '_display'
        method = getattr(self, method_name, self.generic_display)
        return method()

    def generic_display(self):
        chunks = []

        # If citation had "Title 1, chapter 6" as those first.
        if self.get('supernodes'):
            first = True
            for division, enum in self['supernodes']:
                # text = '%s <a href="%s">%s</a>'
                # chunks.append(text % (division, self['url'], enum))
                chunks.append(division + ' ' + enum)
                if first:
                    chunks.append(', ')
                    first = False

        # If the section currently exists, hyperlink it.
        if self.get('verb') != 'add' and self['url']:
            text = '<a href="{url}">{enum}</a>'
            chunks.append(text.format(**self))

        # Other wise no hyperlink.
        else:
            if self.get('supernodes'):
                chunks.append(', ')
                chunks.append(self['name'])
                chunks.append(' ')
            chunks.append(self['enum'])
        return ''.join(chunks)

    def session_laws_display(self):
        return self['enum']


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
        '''Subclasses can double-dispatch to specific display
        function for each source id.
        '''
        display_name = self.bill.metadata['laws']
        display_name = display_name.get(self.source, self.source)
        display_name = display_name['display_name']
        chunks = [display_name]

        # For a sequence of sections, use one section symbol.
        if len(self.details) == 1:
            if self.details[0]['name'] == 'section':
                chunks.append(' &sect; ')
            else:
                chunks.append(' ')

        # For a sequence of sections, use two section symbols.
        elif len(self.details) > 1:
            if all(deets['name'] == 'section' for deets in self.details):
                chunks.append(' &sect;&sect; ')
            else:
                chunks.append(' ')

        for detail in self.details:
            chunks.append(detail.display())
            chunks.append('; ')

        chunks[-1] = '.'

        return ''.join(chunks)

    def session_laws_display(self):
        chunks = []

        # Group them by year first.
        grouper = itemgetter('session_law_year')
        for year, details in groupby(self.details, grouper):
            chunks.append('Laws of %s, ' % year)

            # Then by chapter.
            grouper = itemgetter('supernodes')
            for supernodes, details in groupby(self.details, grouper):

                # If citation had "Title 1, chapter 6" as those first.
                first = True
                for division, enum in supernodes:
                    chunks.extend([division.rstrip('s'), ' ', enum])
                    if first:
                        chunks.append(', ')
                        first = False

                # Toss that last comma.
                chunks.pop()
                details = list(details)

                # For a sequence of sections, use one section symbol.
                if len(details) == 1:
                    if details[0]['name'] == 'section':
                        chunks.append(' &sect; ')
                    else:
                        chunks.append(' ')

                # For a sequence of sections, use two section symbols.
                elif len(details) > 1:
                    if all(deets['name'] == 'section' for deets in details):
                        chunks.append(' &sect;&sect; ')
                    else:
                        chunks.append(' ')

                for details_dict in details:
                    chunks.append(details_dict.display())
                    chunks.append(', ')

                chunks[-1] = '; '

        chunks[-1] = '.'
        return ''.join(chunks)


def affected_code(bill):

    data = dict(add=defaultdict(list),
                amend=defaultdict(list),
                repeal=defaultdict(list))

    # Map the wrapper class vover the details list.
    details = map(_DetailsItem, bill['+affected_code']['details'])

    # Group the details by verb.
    for verb, details in groupby(details, itemgetter('verb')):

        # Group the verb details by source.
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


