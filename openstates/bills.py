from pupa.scrape import Bill
from .base import OpenstatesBaseScraper


action_types = {
    'bill:introduced': 'introduction',
    'bill:reading:1': 'reading-1',
    'bill:reading:2': 'reading-2',
    'bill:reading:3': 'reading-3',
    'bill:passed': 'passage',
    'bill:failed': 'failure',
    'bill:withdrawn': 'withdrawal',
    'committee:referred': 'committee-referral',
    'committee:passed': 'committee-passage',
    'committee:passed:favorable': 'committee-passage-favorable',
    'committee:passed:unfavorable': 'committee-passage-unfavorable',
    'committee:failed': 'committee-failure',
    'governor:received': 'executive-received',
    'governor:signed': 'executive-signature',
    'governor:vetoed': 'executive-veto',
    'amendment:introduced': 'amendment-introduction',
    'amendment:passed': 'amendment-passage',
    'amendment:withdrawn': 'amendment-withdrawal',
    'amendment:failed': 'amendment-failure',
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
        # TODO: subjects?
        old.pop('subjects')
        # TODO: votes
        old.pop('votes')

        new = Bill(old.pop('bill_id'), old.pop('session'), old.pop('title'),
                   chamber=old.pop('chamber'), classification=old.pop('type'))

        for title in old.pop('alternate_titles'):
            new.add_title(title)

        for doc in old.pop('documents'):
            new.add_document_link(doc['name'], doc['url'])

        for doc in old.pop('versions'):
            new.add_version_link(doc['name'], doc['url'], media_type=doc['mimetype'])

        for subj in old.pop('scraped_subjects', []):
            new.add_subject(subj)

        for spon in old.pop('sponsors'):
            if spon.get('committee_id') is not None:
                entity_type = 'committee'
            elif spon.get('leg_id') is not None:
                entity_type = 'person'
            else:
                entity_type = None
            # TODO: use sponsorship ids to do matching
            new.add_sponsorship(spon['name'], spon['type'], entity_type,
                                spon['type'] == 'primary')

        for act in old.pop('actions'):
            new.add_action(act['action'], act['date'][:10], chamber=act['actor'],
                           classification=[action_types[c] for c in act['type'] if c != 'other'])
            # TODO: related_entities

        for comp in old.pop('companions', []):
            # TODO: fix this
            new.add_related_bill(comp['bill_id'], comp['session'], comp['relation_type'])


        # generic OpenStates stuff
        for id in old.pop('all_ids'):
            new.add_identifier(id, scheme='openstates')

        for source in old.pop('sources'):
            new.add_source(**source)

        assert not old, old.keys()

        return new


    def scrape(self):
        method = 'metadata/{}?'.format(self.state)
        self.metadata = self.api(method)

        method = 'bills/?state={}&fields=id'.format(self.state)
        for result in self.api(method):
            yield self.scrape_bill(result['id'])
