import re
import itertools
import subprocess
import collections


def url_xpath(url, path):
    import requests
    import lxml.html
    doc = lxml.html.fromstring(requests.get(url).text)
    return doc.xpath(path)


def convert_pdf(filename, type='xml'):
    commands = {'text': ['pdftotext', '-layout', filename, '-'],
                'text-nolayout': ['pdftotext', filename, '-'],
                'xml': ['pdftohtml', '-xml', '-stdout', filename],
                'html': ['pdftohtml', '-stdout', filename]}
    try:
        pipe = subprocess.Popen(commands[type], stdout=subprocess.PIPE,
                                close_fds=True).stdout
    except OSError as e:
        raise EnvironmentError("error running %s, missing executable? [%s]" %
                               ' '.join(commands[type]), e)
    data = pipe.read()
    pipe.close()
    return data


def pdf_to_lxml(filename, type='html'):
    import lxml.html
    text = convert_pdf(filename, type)
    return lxml.html.fromstring(text)


def clean_spaces(s):
    return re.sub('\s+', ' ', s, flags=re.U).strip()


class PlaintextColumns(object):
    '''
    Parse plain text columns like this into a table:

    cols = """
        Austin             Errington      Lawson, L        Pryor
        Bartlett           Forestal       Macer            Riecken
        Battles            GiaQuinta      Moed             Shackleford
        Bauer              Goodin         Moseley          Smith, V
        Brown,C            Hale           Niezgodsk        Stemler
        Candelaria Reardon Harris         Pelath           Summers
        DeLaney            Kersey         Pierce           VanDenburgh
        Dvorak             Klinker        Porter
    """

    Usage:

    >>> table = PlaintextColumns(cols)

    >>> table.rows().next()
    ('Austin', 'Errington', 'Lawson, L', 'Pryor')

    >>> table.cols().next()

    ('Austin',
     'Bartlett',
     'Battles',
     'Bauer',
     'Brown,C',
     'Candelaria Reardon',
     'DeLaney',
     'Dvorak')

    >>> list(table.cells())
    ['Austin', 'Errington', 'Lawson, L', ...]
    '''
    def __init__(self, text, threshold=3):
        '''Threshold is how many times a column boundary (an integer offset
        from the beginning of the line) must be found in order to qualify
        as a boundary and not an outlier.
        '''
        self.text = text.strip()
        self.threshold = threshold

    def _get_column_ends(self):
        '''Guess where the ends of the columns lie.
        '''
        ends = collections.Counter()
        for line in self.text.splitlines():
            for matchobj in re.finditer('\s{2,}', line.lstrip()):
                ends[matchobj.end()] += 1
        return ends

    def _get_column_boundaries(self):
        '''Use the guessed ends to guess the boundaries of the plain
        text columns.
        '''
        # Try to figure out the most common column boundaries.
        ends = self._get_column_ends()
        if not ends:
            # If there aren't even any nontrivial sequences of whitespace
            # dividing text, there may be just one column. In which case,
            # Return a single span, effectively the whole line.
            return [slice(None, None)]

        most_common = []
        threshold = self.threshold
        for k, v in collections.Counter(ends.values()).most_common():
            if k >= threshold:
                most_common.append(k)

        if most_common:
            boundaries = []
            for k, v in ends.items():
                if v in most_common:
                    boundaries.append(k)
        else:
            # Here there weren't enough boundaries to guess the most common
            # ones, so just use the apparent boundaries. In other words, we
            # have only 1 row. Potentially a source of inaccuracy.
            boundaries = ends.keys()

        # Convert the boundaries into a list of span slices.
        boundaries.sort()
        last_boundary = boundaries[-1]
        boundaries = zip([0] + boundaries, boundaries)
        boundaries = list(itertools.starmap(slice, boundaries))

        # And get from the last boundary to the line ending.
        boundaries.append(slice(last_boundary, None))
        return boundaries

    @property
    def boundaries(self):
        _boundaries = getattr(self, '_boundaries', None)
        if _boundaries is not None:
            return _boundaries
        self._boundaries = _boundaries = self._get_column_boundaries()
        return _boundaries

    def getcells(self, line):
        '''Using self.boundaries, extract cells from the given line.
        '''
        for boundary in self.boundaries:
            cell = line.lstrip()[boundary].strip()
            if cell:
                for cell in re.split('\s{3,}', cell):
                    yield cell
            else:
                yield None

    def rows(self):
        '''Returns an iterator of row tuples.
        '''
        for line in self.text.splitlines():
            yield tuple(self.getcells(line))

    def cells(self):
        '''Returns an interator of all cells in the table.
        '''
        for line in self.text.splitlines():
            for cell in self.getcells(line):
                yield cell

    def cols(self):
        '''Returns an interator of column tuples.
        '''
        return itertools.izip(*list(self.rows()))

    __iter__ = cells
