import re
from collections import defaultdict
from itertools import repeat
from operator import itemgetter

from billy.models import Metadata


repeat1 = repeat(1)


def include_fields(*field_names):
    return zip(field_names, repeat1)


def chamber(abbr, chamber):
    '''
    2-12-2012
    Per wireframes/spec, provide this info:

    - leg'r count
    - party breakdown
    - committee count
    - joint committee count
    - bill count
    '''
    res = {}

    state = Metadata.get_object(abbr)

    # Legislators
    legislators = state.legislators({'chamber': chamber, 'active': True},
                                    {'party': True})
    legislators = list(legislators)

    # Maybe later, mapreduce instead
    party_counts = defaultdict(int)
    for leg in legislators:
        party_counts[leg['party']] += 1

    res['legislators'] = {
        'count': len(legislators),
        'party_counts': dict(party_counts),
        }

    # Committees
    res['committees'] = {
        'count': state.committees({'chamber': chamber}).count(),
        'joint_count': state.committees({'chamber': 'joint'}).count(),
        }

    res['bills_count'] = state.bills({'chamber': chamber}).count()

    return res


def recent_actions(abbr):
    state = Metadata.get_object(abbr)
    bills = state.bills({'session': state.most_recent_session,
                         '$or': [{'actions.type': 'bill:passed',
                                  'actions.type': 'bill:introduced'}],
                         'type': 'bill'})
    bills_by_action = defaultdict(list)
    for bill in bills:
        for action in bill['actions']:
            actor = re.search(r'(upper|lower)', action['actor'])
            if actor:
                actor = actor.group()
            else:
                continue
            for type_ in action['type']:
                if type_ in ['bill:passed', 'bill:introduced']:
                    bills_by_action[(type_, actor)].append(
                                            (action['date'], bill))

    def f(type_, chamber):
        bills = list(sorted(bills_by_action[(type_, chamber)],
                     reverse=True, key=itemgetter(0)))[:2]
        return map(itemgetter(1), bills)

    res = dict(
        passed_upper=f('bill:passed', 'upper'),
        passed_lower=f('bill:passed', 'lower'),
        introduced_upper=f('bill:introduced', 'upper'),
        introduced_lower=f('bill:introduced', 'lower'))

    return res
