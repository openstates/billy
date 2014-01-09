from __future__ import print_function
import os
import glob
import json
import logging
import datetime
from time import time
from collections import defaultdict

from billy.core import settings, db, elasticsearch
from billy.utils import (metadata, term_for_session, fix_bill_id,
                         JSONEncoderPlus)
from billy.utils.fulltext import bill_to_elasticsearch
from billy.importers.names import get_legislator_id
from billy.importers.filters import apply_filters

from billy.importers.subjects import SubjectCategorizer
from billy.importers.utils import (insert_with_id, update, prepare_obj,
                                   next_big_id, get_committee_id)

if hasattr(settings, "ENABLE_GIT") and settings.ENABLE_GIT:
    from dulwich.repo import Repo
    from dulwich.objects import Blob
    from dulwich.objects import Tree
    from dulwich.objects import Commit, parse_timezone


filters = settings.BILL_FILTERS
logger = logging.getLogger('billy')


def match_sponsor_ids(abbr, bill):
    for sponsor in bill['sponsors']:
        # use sponsor's chamber if specified
        sponsor['leg_id'] = get_legislator_id(abbr, bill['session'],
                                              sponsor.get('chamber',
                                                          bill['chamber']),
                                              sponsor['name'])
        if sponsor['leg_id'] is None:
            sponsor['leg_id'] = get_legislator_id(abbr, bill['session'], None,
                                                  sponsor['name'])
        if sponsor['leg_id'] is None:
            sponsor['committee_id'] = get_committee_id(abbr, bill['chamber'],
                                                       sponsor['name'])


def load_standalone_votes(data_dir):
    pattern = os.path.join(data_dir, 'votes', '*.json')
    paths = glob.glob(pattern)

    votes = defaultdict(list)

    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        # need to match bill_id already in the database
        bill_id = fix_bill_id(data.pop('bill_id'))

        votes[(data['bill_chamber'], data['session'], bill_id)].append(data)

    logger.info('imported %s vote files' % len(paths))
    return votes


def elasticsearch_push(bill):
    if settings.ENABLE_ELASTICSEARCH_PUSH:
        esdoc = bill_to_elasticsearch(bill)
        elasticsearch.index(index='billy', doc_type='bills', id=bill['_id'],
                            doc=esdoc)


git_active_repo = None
git_active_commit = None
git_active_tree = None
git_old_tree = None
HEAD = None


def git_add_bill(data):
    if not hasattr(settings, "ENABLE_GIT") or not settings.ENABLE_GIT:
        return

    global git_active_repo
    global git_active_tree
    global git_active_commit

    bill = json.dumps(data, cls=JSONEncoderPlus, sort_keys=True, indent=4)
    spam = Blob.from_string(bill)
    bid = str(data['_id'])
    git_active_repo.object_store.add_object(spam)
    git_active_tree[bid] = (0100644, spam.id)
    git_active_tree.check()
    print("added %s - %s" % (data['_id'], spam.id))


def git_commit(message):
    if not hasattr(settings, "ENABLE_GIT") or not settings.ENABLE_GIT:
        return

    print("Commiting import as '%s'" % message)

    global git_active_repo
    global git_active_tree
    global git_old_tree
    global git_active_commit
    global HEAD
    repo = git_active_repo

    if git_old_tree == git_active_tree.id:
        # We don't wait t commit twice.
        print("Nothing new here. Bailing out.")
        return

    c = git_active_commit
    c.tree = git_active_tree.id
    c.parents = [HEAD]
    repo.object_store.add_object(git_active_tree)
    c.author = c.committer = "Billy <billy@localhost>"
    c.commit_time = c.author_time = int(time())
    tz = parse_timezone("-0400")[0]
    c.commit_timezone = c.author_timezone = tz
    c.encoding = "UTF-8"
    c.message = message
    repo.object_store.add_object(c)
    repo.refs['refs/heads/master'] = c.id


def git_repo_init(gitdir):
    os.mkdir(gitdir)
    repo = Repo.init_bare(gitdir)
    blob = Blob.from_string("""Why, Hello there!

This is your friendly Legislation tracker, Billy here.

This is a git repo full of everything I write to the DB. This isn't super
useful unless you're debugging production issues.

Fondly,
   Bill, your local Billy instance.""")
    tree = Tree()
    tree.add("README", 0100644, blob.id)
    commit = Commit()
    commit.tree = tree.id
    author = "Billy <billy@localhost>"
    commit.author = commit.committer = author
    commit.commit_time = commit.author_time = int(time())
    tz = parse_timezone('-0400')[0]
    commit.commit_timezone = commit.author_timezone = tz
    commit.encoding = "UTF-8"
    commit.message = "Initial commit"
    repo.object_store.add_object(blob)
    repo.object_store.add_object(tree)
    repo.object_store.add_object(commit)
    repo.refs['refs/heads/master'] = commit.id


def git_prelod(abbr):
    if not hasattr(settings, "ENABLE_GIT") or not settings.ENABLE_GIT:
        return

    global git_active_repo
    global git_active_commit
    global git_active_tree
    global git_old_tree
    global HEAD

    gitdir = "%s/%s.git" % (settings.GIT_PATH, abbr)

    if not os.path.exists(gitdir):
        git_repo_init(gitdir)

    git_active_repo = Repo(gitdir)
    git_active_commit = Commit()
    HEAD = git_active_repo.head()
    commit = git_active_repo.commit(HEAD)
    tree = git_active_repo.tree(commit.tree)
    git_old_tree = tree.id
    git_active_tree = tree


def import_bill(data, standalone_votes, categorizer):
    """
        insert or update a bill

        data - raw bill JSON
        standalone_votes - votes scraped separately
        categorizer - SubjectCategorizer (None - no categorization)
    """
    abbr = data[settings.LEVEL_FIELD]

    # clean up bill_ids
    data['bill_id'] = fix_bill_id(data['bill_id'])
    if 'alternate_bill_ids' in data:
        data['alternate_bill_ids'] = [fix_bill_id(bid) for bid in
                                      data['alternate_bill_ids']]

    # move subjects to scraped_subjects
    # NOTE: intentionally doesn't copy blank lists of subjects
    # this avoids the problem where a bill is re-run but we can't
    # get subjects anymore (quite common)
    subjects = data.pop('subjects', None)
    if subjects:
        data['scraped_subjects'] = subjects

    # update categorized subjects
    if categorizer:
        categorizer.categorize_bill(data)

    # companions
    for companion in data['companions']:
        companion['bill_id'] = fix_bill_id(companion['bill_id'])
        # query based on companion
        spec = companion.copy()
        spec[settings.LEVEL_FIELD] = abbr
        if not spec['chamber']:
            spec.pop('chamber')
        companion_obj = db.bills.find_one(spec)
        if companion_obj:
            companion['internal_id'] = companion_obj['_id']
        else:
            logger.warning('Unknown companion: {chamber} {session} {bill_id}'
                           .format(**companion))

    # look for a prior version of this bill
    bill = db.bills.find_one({settings.LEVEL_FIELD: abbr,
                              'session': data['session'],
                              'chamber': data['chamber'],
                              'bill_id': data['bill_id']})

    # keep doc ids consistent
    doc_matcher = DocumentMatcher(abbr)
    if bill:
        doc_matcher.learn_ids(bill['versions'] + bill['documents'])
    doc_matcher.set_ids(data['versions'] + data['documents'])

    # match sponsor leg_ids
    match_sponsor_ids(abbr, data)

    # process votes ############

    # pull votes off bill
    bill_votes = data.pop('votes', [])

    # grab the external bill votes if present
    if metadata(abbr).get('_partial_vote_bill_id'):
        # this is a hack initially added for Rhode Island where we can't
        # determine the full bill_id, if this key is in the metadata
        # we just use the numeric portion, not ideal as it won't work
        # where HB/SBs overlap, but in RI they never do
        # pull off numeric portion of bill_id
        numeric_bill_id = data['bill_id'].split()[1]
        bill_votes += standalone_votes.pop((data['chamber'], data['session'],
                                            numeric_bill_id), [])
    else:
        # add loaded votes to data
        bill_votes += standalone_votes.pop((data['chamber'], data['session'],
                                            data['bill_id']), [])

    # do id matching and other vote prep
    if bill:
        prepare_votes(abbr, data['session'], bill['_id'], bill_votes)
    else:
        prepare_votes(abbr, data['session'], None, bill_votes)

    # process actions ###########

    dates = {'first': None, 'last': None, 'passed_upper': None,
             'passed_lower': None, 'signed': None}

    vote_flags = {
        "bill:passed",
        "bill:failed",
        "bill:veto_override:passed",
        "bill:veto_override:failed",
        "amendment:passed",
        "amendment:failed",
        "committee:passed",
        "committee:passed:favorable",
        "committee:passed:unfavorable",
        "committee:passed:failed"
    }
    already_linked = set()
    remove_vote = set()

    for action in data['actions']:
        adate = action['date']

        def _match_committee(name):
            return get_committee_id(abbr, action['actor'], name)

        def _match_legislator(name):
            return get_legislator_id(abbr,
                                     data['session'],
                                     action['actor'],
                                     name)

        resolvers = {
            "committee": _match_committee,
            "legislator": _match_legislator
        }

        if "related_entities" in action:
            for entity in action['related_entities']:
                try:
                    resolver = resolvers[entity['type']]
                except KeyError as e:
                    # We don't know how to deal.
                    logger.error("I don't know how to sort a %s" % e)
                    continue

                id = resolver(entity['name'])
                entity['id'] = id

        # first & last dates
        if not dates['first'] or adate < dates['first']:
            dates['first'] = adate
        if not dates['last'] or adate > dates['last']:
            dates['last'] = adate

        # passed & signed dates
        if (not dates['passed_upper'] and action['actor'] == 'upper'
                and 'bill:passed' in action['type']):
            dates['passed_upper'] = adate
        elif (not dates['passed_lower'] and action['actor'] == 'lower'
                and 'bill:passed' in action['type']):
            dates['passed_lower'] = adate
        elif (not dates['signed'] and 'governor:signed' in action['type']):
            dates['signed'] = adate

        # vote-action matching
        action_attached = False
        # only attempt vote matching if action has a date and is one of the
        # designated vote action types
        if set(action['type']).intersection(vote_flags) and action['date']:
            for vote in bill_votes:
                if not vote['date']:
                    continue

                delta = abs(vote['date'] - action['date'])
                if (delta < datetime.timedelta(hours=20) and
                        vote['chamber'] == action['actor']):
                    if action_attached:
                        # multiple votes match, we can't guess
                        action.pop('related_votes', None)
                    else:
                        related_vote = vote['vote_id']
                        if related_vote in already_linked:
                            remove_vote.add(related_vote)

                        already_linked.add(related_vote)
                        action['related_votes'] = [related_vote]
                        action_attached = True

    # remove related_votes that we linked to multiple actions
    for action in data['actions']:
        for vote in remove_vote:
            if vote in action.get('related_votes', []):
                action['related_votes'].remove(vote)

    # save action dates to data
    data['action_dates'] = dates

    data['_term'] = term_for_session(abbr, data['session'])

    alt_titles = set(data.get('alternate_titles', []))

    for version in data['versions']:
        # Merge any version titles into the alternate_titles list
        if 'title' in version:
            alt_titles.add(version['title'])
        if '+short_title' in version:
            alt_titles.add(version['+short_title'])
    try:
        # Make sure the primary title isn't included in the
        # alternate title list
        alt_titles.remove(data['title'])
    except KeyError:
        pass
    data['alternate_titles'] = list(alt_titles)
    data = apply_filters(filters, data)

    if not bill:
        insert_with_id(data)
        elasticsearch_push(data)
        git_add_bill(data)
        save_votes(data, bill_votes)
        return "insert"
    else:
        if update(bill, data, db.bills):
            elasticsearch_push(bill)
        git_add_bill(bill)
        save_votes(bill, bill_votes)
        return "update"


def import_bills(abbr, data_dir):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'bills', '*.json')

    git_prelod(abbr)

    counts = {
        "update": 0,
        "insert": 0,
        "total": 0
    }

    votes = load_standalone_votes(data_dir)
    try:
        categorizer = SubjectCategorizer(abbr)
    except Exception as e:
        logger.debug('Proceeding without subject categorizer: %s' % e)
        categorizer = None

    paths = glob.glob(pattern)
    for path in paths:
        with open(path) as f:
            data = prepare_obj(json.load(f))

        counts["total"] += 1
        ret = import_bill(data, votes, categorizer)
        counts[ret] += 1

    logger.info('imported %s bill files' % len(paths))

    for remaining in votes.keys():
        logger.debug('Failed to match vote %s %s %s' % tuple([
            r.encode('ascii', 'replace') for r in remaining]))

    populate_current_fields(abbr)

    git_commit("Import Update")

    return counts


def populate_current_fields(abbr):
    """
    Set/update _current_term and _current_session fields on all bills
    for a given location.
    """
    meta = db.metadata.find_one({'_id': abbr})
    current_term = meta['terms'][-1]
    current_session = current_term['sessions'][-1]

    for bill in db.bills.find({settings.LEVEL_FIELD: abbr}):
        if bill['session'] == current_session:
            bill['_current_session'] = True
        else:
            bill['_current_session'] = False

        if bill['session'] in current_term['sessions']:
            bill['_current_term'] = True
        else:
            bill['_current_term'] = False

        db.bills.save(bill, safe=True)


def prepare_votes(abbr, session, bill_id, scraped_votes):
    # if bill already exists, try and preserve vote_ids
    vote_matcher = VoteMatcher(abbr)

    if bill_id:
        existing_votes = list(db.votes.find({'bill_id': bill_id}))
        if existing_votes:
            vote_matcher.learn_ids(existing_votes)

    vote_matcher.set_ids(scraped_votes)

    # link votes to committees and legislators
    for vote in scraped_votes:

        # committee_ids
        if 'committee' in vote:
            committee_id = get_committee_id(abbr, vote['chamber'],
                                            vote['committee'])
            vote['committee_id'] = committee_id

        # vote leg_ids
        vote['_voters'] = []
        for vtype in ('yes_votes', 'no_votes', 'other_votes'):
            svlist = []
            for svote in vote[vtype]:
                id = get_legislator_id(abbr, session, vote['chamber'], svote)
                svlist.append({'name': svote, 'leg_id': id})
                vote['_voters'].append(id)

            vote[vtype] = svlist


def save_votes(bill, votes):
    # doesn't delete votes if none were scraped this time
    if not votes:
        return

    # remove all existing votes for this bill
    db.votes.remove({'bill_id': bill['_id']}, safe=True)

    # save the votes
    for vote in votes:
        vote['_id'] = vote['vote_id']
        vote['bill_id'] = bill['_id']
        vote[settings.LEVEL_FIELD] = bill[settings.LEVEL_FIELD]
        vote['session'] = bill['session']
        db.votes.save(vote, safe=True)


class GenericIDMatcher(object):

    def __init__(self, abbr):
        self.abbr = abbr
        self.ids = {}

    def _reset_sequence(self):
        self.seq_for_key = defaultdict(int)

    def _get_next_id(self):
        return next_big_id(self.abbr, self.id_letter, self.id_collection)

    def nondup_key_for_item(self, item):
        # call user's key_for_item
        key = self.key_for_item(item)
        # running count of how many of this key we've seen
        seq_num = self.seq_for_key[key]
        self.seq_for_key[key] += 1
        # append seq_num to key to avoid sharing key for multiple items
        return key + (seq_num,)

    def learn_ids(self, item_list):
        """ read in already set ids on objects """
        self._reset_sequence()
        for item in item_list:
            key = self.nondup_key_for_item(item)
            self.ids[key] = item[self.id_key]

    def set_ids(self, item_list):
        """ set ids on an object, using internal mapping then new ids """
        self._reset_sequence()
        for item in item_list:
            key = self.nondup_key_for_item(item)
            item[self.id_key] = self.ids.get(key) or self._get_next_id()


class VoteMatcher(GenericIDMatcher):
    id_letter = 'V'
    id_collection = 'vote_ids'
    id_key = 'vote_id'

    def key_for_item(self, vote):
        return (vote['motion'], vote['chamber'], vote['date'],
                vote['yes_count'], vote['no_count'], vote['other_count'])


class DocumentMatcher(GenericIDMatcher):
    id_letter = 'D'
    id_collection = 'document_ids'
    id_key = 'doc_id'

    def key_for_item(self, document):
        # URL is good enough as a key
        return (document['url'],)
