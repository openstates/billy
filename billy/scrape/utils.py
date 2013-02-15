import subprocess
import re


def url_xpath(url, path):
    import scrapelib
    import lxml.html
    doc = lxml.html.fromstring(scrapelib.urlopen(url))
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
