import random

from os.path import abspath, dirname, join


def get_funfact(abbr, data={}):
    try:
        return random.choice(data[abbr])
    except KeyError:
        try:
            here = abspath(dirname(__file__))
            with open(join(here, abbr + '.txt')) as f:
                facts = f.read()
        except IOError:
            return 'This state is not fun and therefore has no funfacts.'
        facts = filter(None, facts.splitlines())
        data[abbr] = facts
        return random.choice(data[abbr])

