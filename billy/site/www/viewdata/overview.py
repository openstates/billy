import pdb

from collections import defaultdict

from billy import db

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

    # Legislators
    legislators = db.legislators.find({'state': abbr, 'chamber': chamber}, 
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
        'count': db.committees.find({'state': abbr, 'chamber': chamber}).count(),
        'joint_count': db.committees.find({'state': abbr, 'chamber': 'joint'}).count(),
        }

    res['bills_count'] = db.bills.find({'state': abbr, 'chamber': chamber}).count()

    return res


def bills(state, chamber):
    '''
    '''
    #db.bills.find({'state': 'de' }, {'bill_id': 1, 'actions': {'$slice': 1}}).sort('actions.1.date', -1).limit(10)
