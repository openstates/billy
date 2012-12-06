import re
import logging

from billy.core import db
from billy.core import settings

# abbr, session : NameMatcher
__matchers = {}

# abbr : NameMatcher
__com_matchers = {}

logger = logging.getLogger('billy')


def get_legislator_id(abbr, session, chamber, name):
    try:
        matcher = __matchers[(abbr, session)]
    except KeyError:
        metadata = db.metadata.find_one({'_id': abbr})
        term = None
        for term in metadata['terms']:
            if session in term['sessions']:
                break
        else:
            raise Exception("bad session: " + session)

        matcher = NameMatcher(abbr, term['name'])

        __matchers[(abbr, session)] = matcher

    return matcher.match(name, chamber)


def attempt_committee_match(abbr, chamber, name):
    try:
        matcher = __com_matchers[abbr]
    except KeyError:
        matcher = __com_matchers[abbr] = CommitteeNameMatcher(abbr, None)

    return matcher.match(name, chamber)


class NameMatcher(object):
    """
    Match various forms of a name, provided they uniquely identify
    a person from everyone else we've seen.

    Given a legislator with the name:
     {'full_name': 'Michael J. Stephens', 'first_name': 'Michael',
      'last_name': 'Stephens', 'middle_name': 'Joseph'}
    we will match these forms:
     Michael J. Stephens
     Michael Stephens
     Stephens
     Stephens, Michael
     Stephens, M
     Stephens, Michael Joseph
     Stephens, Michael J
     Stephens, M J
     M Stephens
     M J Stephens
     Michael Joseph Stephens
     Stephens (M)

    If we add a second legislator with the name:
     {'full_name': 'Matthew J. Stephens', 'first_name': 'Matthew',
      'last_name': 'Stephens', 'middle_name': 'Joseph'}
    Then the forms
     Stephens, M
     Stephens, M J
     M Stephens
     M J Stephens
     Stephens (M)
    are no longer unique and will not be matched with either legislator.
    """

    def __init__(self, abbr, term):
        self._names = {'upper': {}, 'lower': {}, None: {}}
        self._codes = {'upper': {}, 'lower': {}, None: {}}
        self._manual = {'upper': {}, 'lower': {}, None: {}, 'joint': {}}
        self._abbr = abbr
        self._term = term

        roles_elemMatch = {settings.LEVEL_FIELD: abbr, 'type': 'member',
                           'term': term}
        old_roles_query = {'old_roles.%s' % term: {'$elemMatch':
                                                   {settings.LEVEL_FIELD: abbr,
                                                    'type': 'member'}}}

        for legislator in db.legislators.find({
            '$or': [{'roles': {'$elemMatch': roles_elemMatch}},
                    old_roles_query]}):

            if 'middle_name' not in legislator:
                legislator['middle_name'] = ''

            self._learn(legislator)

        self._learn_manual_matches()

    def _learn_manual_matches(self):
        rows = db.manual.name_matchers.find({
            "abbr": self._abbr,
            "type": "legislator"
        })

        for row in rows:
            (term, chamber, name, obj_id) = (
                row['term'], row['chamber'], row['name'], row['obj_id'])

            if (term == self._term or not term) and obj_id:
                self._manual[chamber][name] = obj_id
                # if the name is already in _manual[None] and isn't obj_id
                if self._manual[None].get(name, False) not in (False, obj_id):
                    self._manual[None][name] = None
                else:
                    self._manual[None][name] = obj_id

    def _normalize(self, name):
        """
        Normalizes a legislator name by stripping titles from the front,
        converting to lowercase and removing punctuation.
        """
        name = re.sub(
            r'^(Senator|Representative|Sen\.?|Rep\.?|'
            'Hon\.?|Right Hon\.?|Mr\.?|Mrs\.?|Ms\.?|L\'hon\.?|'
            'Assembly(member|man|woman)) ',
            '',
            name)
        return name.strip().lower().replace('.', '')

    def _learn(self, legislator):
        """
        Expects a dictionary with full_name, first_name, last_name and
        middle_name elements as key.

        While this can grow quickly, we should never be dealing with
        more than a few hundred legislators at a time so don't worry about
        it.
        """
        name, obj = legislator, legislator['_id']

        if (legislator['roles'] and legislator['roles'][0]['term'] ==
                self._term and legislator['roles'][0]['type'] == 'member'):
            chamber = legislator['roles'][0]['chamber']
        else:
            try:
                chamber = legislator['old_roles'][self._term][0].get('chamber')
            except KeyError:
                raise ValueError("no role in legislator %s [%s] for term %s" %
                                 (legislator['full_name'], legislator['_id'],
                                  self._term))

        if '_code' in name:
            code = name['_code']
            if code in self._codes[chamber] or code in self._codes[None]:
                raise ValueError("non-unique legislator code [%s] for %s" %
                                 (code, name['full_name']))
            self._codes[chamber][code] = obj
            self._codes[None][code] = obj

        # We throw possible forms of this name into a set because we
        # don't want to try to add the same form twice for the same
        # name
        forms = set()

        def add_form(form):
            forms.add(self._normalize(form))

        add_form(name['full_name'])
        add_form(name['_scraped_name'])
        add_form(name['last_name'])

        if name['first_name']:
            add_form("%s, %s" % (name['last_name'], name['first_name']))
            add_form("%s %s" % (name['first_name'], name['last_name']))
            add_form("%s, %s" % (name['last_name'], name['first_name'][0]))
            add_form("%s (%s)" % (name['last_name'], name['first_name']))
            add_form("%s %s" % (name['first_name'][0], name['last_name']))
            add_form("%s (%s)" % (name['last_name'], name['first_name'][0]))

            if name['middle_name']:
                add_form("%s, %s %s" % (name['last_name'], name['first_name'],
                                        name['middle_name']))
                add_form("%s, %s %s" % (name['last_name'],
                                        name['first_name'][0],
                                        name['middle_name']))
                add_form("%s %s %s" % (name['first_name'],
                                       name['middle_name'],
                                       name['last_name']))
                add_form("%s, %s %s" % (name['last_name'],
                                        name['first_name'][0],
                                        name['middle_name'][0]))
                add_form("%s %s %s" % (name['first_name'],
                                       name['middle_name'][0],
                                       name['last_name']))
                add_form("%s, %s %s" % (name['last_name'],
                                        name['first_name'],
                                        name['middle_name'][0]))
                add_form("%s, %s.%s." % (name['last_name'],
                                         name['first_name'][0],
                                         name['middle_name'][0]))

        for form in forms:
            form = self._normalize(form)
            if form in self._names[chamber]:
                self._names[chamber][form] = None
            else:
                self._names[chamber][form] = obj

            if form in self._names[None]:
                self._names[None][form] = None
            else:
                self._names[None][form] = obj

    def match(self, name, chamber=None):
        """
        If this matcher has uniquely seen a matching name, return its
        value. Otherwise, return None.

        If chamber is set then the search will be limited to legislators
        with matching chamber. If chamber is None then the search
        will be cross-chamber.
        """
        try:
            return self._manual[chamber][name]
        except KeyError:
            pass

        if chamber == 'joint':
            chamber = None

        try:
            return self._codes[chamber][name]
        except KeyError:
            pass

        if chamber not in self._names:
            logger.warning("Chamber %s is invalid for a legislator." % (
                chamber
            ))
            return None

        name = self._normalize(name)
        return self._names[chamber].get(name, None)


class CommitteeNameMatcher(object):
    def __init__(self, abbr, term):
        self._manual = {'upper': {}, 'lower': {}, None: {}, 'joint': {}}
        self._abbr = abbr
        self._term = term
        self._learn_manual_matches()

    def _learn_manual_matches(self):
        rows = db.manual.name_matchers.find({
            "abbr": self._abbr,
            "type": "committee"
        })

        for row in rows:
            (term, chamber, name, obj_id) = (row['term'], row['chamber'],
                                             row['name'], row['obj_id'])
            row['chamber'] = None  # In case the DB has gone wonky on us.

            if (term == self._term or not term or not self._term) and obj_id:
                self._manual[chamber][name] = obj_id
                if name in self._manual[None]:
                    self._manual[None][name] = None
                else:
                    self._manual[None][name] = obj_id

    def match(self, name, chamber):
        try:
            return self._manual[chamber][name]
        except KeyError:
            return None
