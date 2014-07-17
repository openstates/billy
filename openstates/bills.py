from pupa.scrape import Bill, Vote
from .base import OpenstatesBaseScraper


action_types = {
    'bill:filed': 'filing',
    'bill:introduced': 'introduction',
    'bill:reading:1': 'reading-1',
    'bill:reading:2': 'reading-2',
    'bill:reading:3': 'reading-3',
    'bill:passed': 'passage',
    'bill:failed': 'failure',
    'bill:withdrawn': 'withdrawal',
    'bill:substituted': 'substitution',
    'committee:referred': 'committee-referral',
    'committee:passed': 'committee-passage',
    'committee:passed:favorable': 'committee-passage-favorable',
    'committee:passed:unfavorable': 'committee-passage-unfavorable',
    'committee:failed': 'committee-failure',
    'governor:received': 'executive-received',
    'governor:signed': 'executive-signature',
    'governor:vetoed': 'executive-veto',
    'governor:vetoed:line-item': 'executive-veto-line-item',
    'amendment:introduced': 'amendment-introduction',
    'amendment:passed': 'amendment-passage',
    'amendment:withdrawn': 'amendment-withdrawal',
    'amendment:failed': 'amendment-failure',
    'amendment:tabled': 'amendment-failure',
    'bill:veto_override:passed': 'veto-override-passage',
    'bill:veto_override:failed': 'veto-override-failure',
}


class OpenstatesBillScraper(OpenstatesBaseScraper):

    def scrape_bill(self, bill_id):
        old = self.api('bills/' + bill_id + '?')

        # not needed
        old.pop('id')
        old.pop('state')
        old.pop('level', None)
        old.pop('country', None)
        old.pop('created_at')
        old.pop('updated_at')
        old.pop('action_dates')
        old.pop('+fiscal_notes', None)
        # TODO: subjects?
        old.pop('subjects', [])

        classification = old.pop('type')

        if classification[0] in ['miscellaneous', 'jres', 'cres']:
            return

        if classification == ['memorial resolution'] and self.state == 'ar':
            classification = ['memorial']
        if classification == ['concurrent memorial resolution'] and self.state == 'ar':
            classification = ['concurrent memorial']

        if not old['title'] and self.state == 'me':
            old['title'] = '(unknown)'
        new = Bill(old.pop('bill_id'), old.pop('session'), old.pop('title'),
                   chamber=old.pop('chamber'), classification=classification,
                  )

        abstract = old.pop('summary', None)
        if abstract:
            new.add_abstract(abstract, note='')

        for title in old.pop('alternate_titles'):
            new.add_title(title)

        for doc in old.pop('documents'):
            new.add_document_link(doc['name'], doc['url'], on_duplicate='ignore')

        for doc in old.pop('versions'):
            new.add_version_link(doc['name'], doc['url'], media_type=doc['mimetype'])

        for subj in old.pop('scraped_subjects', []):
            new.add_subject(subj)

        for spon in old.pop('sponsors'):
            if spon.get('committee_id') is not None:
                entity_type = 'organization'
            elif spon.get('leg_id') is not None:
                entity_type = 'person'
            else:
                entity_type = ''
            # TODO: use sponsorship ids to do matching
            new.add_sponsorship(spon['name'], spon['type'], entity_type,
                                spon['type'] == 'primary')

        for act in old.pop('actions'):
            actor = act['actor']
            if actor == 'governor':
                actor = 'executive'
            elif actor == 'joint':
                actor = 'legislature'
            elif actor == 'other':
                actor = 'legislature'
            if act['action']:
                new.add_action(act['action'], act['date'][:10], chamber=actor,
                               classification=[action_types[c] for c in act['type'] if c != 'other'])
            # TODO: related_entities

        for comp in old.pop('companions', []):
            # TODO: fix this
            new.add_related_bill(comp['bill_id'], comp['session'], comp['relation_type'])


        # generic OpenStates stuff
        for id in old.pop('all_ids'):
            new.add_identifier(id, scheme='openstates')

        for source in old.pop('sources'):
            source.pop('retrieved', None)
            new.add_source(**source)

        to_extras = ['+status', '+final_disposition', '+volume_chapter', '+ld_number', '+referral',
                     '+companion'
                    ]
        for k in to_extras:
            v = old.pop(k, None)
            if v:
                new.extras[k[1:]] = v

        # votes
        vote_no = 1
        for vote in old.pop('votes'):
            vote.pop('id')
            vote.pop('state')
            vote.pop('bill_id')
            vote.pop('bill_chamber', None)
            vote.pop('+state', None)
            vote.pop('+country', None)
            vote.pop('+level', None)
            vote.pop('+vacant', None)
            vote.pop('+not_voting', None)
            vote.pop('+amended', None)
            vote.pop('+excused', None)
            vote.pop('+NV', None)
            vote.pop('+AB', None)
            vote.pop('+P', None)
            vote.pop('+V', None)
            vote.pop('+E', None)
            vote.pop('+EXC', None)
            vote.pop('+EMER', None)
            vote.pop('+present', None)
            vote.pop('+absent', None)
            vote.pop('+seconded', None)
            vote.pop('+moved', None)
            vote.pop('+vote_type', None)
            vote.pop('+actual_vote', None)
            vote.pop('+skip_votes', None)

            # TODO: use committee, vtype?
            vote.pop('committee', None)
            vote.pop('committee_id', None)
            vtype = vote.pop('type')

            # some states need identifiers for uniqueness
            identifier = ''
            if self.state in ('ak', 'az', 'co', 'fl', 'in', 'ks', 'ia'):
                identifier = vote['date'] + '-' + str(vote_no)
                vote_no += 1

            newvote = Vote(legislative_session=vote.pop('session'),
                           motion_text=vote.pop('motion'),
                           result='pass' if vote.pop('passed') else 'fail',
                           chamber=vote.pop('chamber'),
                           start_date=vote.pop('date'),
                           classification=[],
                           bill=new,
                           identifier=identifier)
            for vt in ('yes', 'no', 'other'):
                newvote.set_count(vt, vote.pop(vt + '_count'))
                for name in vote.pop(vt + '_votes'):
                    newvote.vote(vt, name['name'])
                    # TODO: leg_id needs to be used here at some point

            for source in vote.pop('sources'):
                source.pop('retrieved', None)
                newvote.add_source(**source)

            if not newvote.sources:
                newvote.sources = new.sources

            vote.pop('vote_id')

            assert not vote, vote.keys()
            yield newvote

        assert not old, old.keys()

        yield new


    def scrape(self):
        method = 'metadata/{}?'.format(self.state)
        self.metadata = self.api(method)

        for page in range(1, 100):
            method = 'bills/?state={}&fields=id&per_page=2000&page='.format(self.state)
            results = self.api(method)
            if not results:
                break
            for result in results:
                yield from self.scrape_bill(result['id'])
