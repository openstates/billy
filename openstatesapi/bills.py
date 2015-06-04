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
    'amendment:amended': 'amendment-amended',
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
        old.pop('+bill_type',None)
        old.pop('+subject', None)
        old.pop('+scraped_subjects', None)
        old.pop('subjects', [])

        classification = old.pop('type')

        # ca weirdness
        if 'fiscal committee' in classification:
            classification.remove('fiscal committee')
        if 'urgency' in classification:
            classification.remove('urgency')
        if 'local program' in classification:
            classification.remove('local program')
        if 'tax levy' in classification:
            classification.remove('tax levy')

        if classification[0] in ['miscellaneous', 'jres', 'cres']:
            return

        if classification == ['memorial resolution'] and self.state == 'ar':
            classification = ['memorial']
        if classification == ['concurrent memorial resolution'] and self.state == 'ar':
            classification = ['concurrent memorial']
        if classification == ['joint session resolution'] and self.state == 'il':
            classification = ['joint resolution']
        if classification == ['legislative resolution'] and self.state == 'ny':
            classification = ['resolution']
        if classification == ['address'] and self.state == 'nh':
            classification = ['resolution']

        if not old['title'] and self.state == 'me':
            old['title'] = '(unknown)'

        chamber = old.pop('chamber')
        if self.state in ('ne', 'dc'):
            chamber = 'legislature'
        elif chamber in ('joint', 'conference'):
            chamber = 'legislature'

        new = Bill(old.pop('bill_id'), old.pop('session'), old.pop('title'),
                   chamber=chamber, classification=classification)

        abstract = old.pop('summary', None)
        if abstract:
            new.add_abstract(abstract, note='')

        for title in old.pop('alternate_titles'):
            new.add_title(title)

        for doc in old.pop('documents'):
            new.add_document_link(doc['name'], doc['url'], on_duplicate='ignore')

        for doc in old.pop('versions'):
            new.add_version_link(doc['name'], doc['url'], media_type=doc.pop('mimetype', ''))

        for subj in old.pop('scraped_subjects', []):
            if subj:
                new.add_subject(subj)

        for spon in old.pop('sponsors'):
            if spon.get('committee_id') is not None:
                entity_type = 'organization'
            elif spon.get('leg_id') is not None:
                entity_type = 'person'
            else:
                entity_type = ''
            new.add_sponsorship(spon['name'], spon['type'], entity_type,
                                spon['type'] == 'primary')

        for act in old.pop('actions'):
            actor = act['actor']
            if actor.lower() in ('governor', 'mayor', 'secretary of state'):
                actor = 'executive'
            elif actor.lower() == 'house' or (actor.lower().startswith('lower (') and self.state == 'ca'):
                actor = 'lower'
            elif actor.lower() in ('senate', 'upper`') or (actor.lower().startswith('upper (') and self.state == 'ca'):
                actor = 'upper'
            elif actor in ('joint', 'other', 'Data Systems', 'Speaker', 'clerk',
                           'Office of the Legislative Fiscal Analyst', 'Became Law w',
                           'conference') or (actor.lower().startswith('legislature (') and self.state == 'ca'):
                actor = 'legislature'

            if actor in ('committee', 'sponsor') and self.state == 'pr':
                actor = 'legislature'

            # nebraska & DC
            if actor in ('upper','council') and self.state in ('ne', 'dc'):
                actor = 'legislature'

            if act['action']:
                newact = new.add_action(act['action'], act['date'][:10], chamber=actor,
                                        classification=[action_types[c] for c in act['type'] if c != 'other'])
                for re in act.get('related_entities', []):
                    if re['type'] == 'committee':
                        re['type'] = 'organization'
                    elif re['type'] == 'legislator':
                        re['type'] = 'person'
                    newact.add_related_entity(re['name'], re['type'])

        for comp in old.pop('companions', []):
            if self.state in ('nj', 'ny', 'mn'):
                rtype = 'companion'
            new.add_related_bill(comp['bill_id'], comp['session'], rtype)

        for abid in old.pop('alternate_bill_ids', []) + old.pop('+alternate_bill_ids', []):
            new.add_identifier(abid)


        # generic OpenStates stuff
        for id in old.pop('all_ids'):
            new.add_identifier(id, scheme='openstates')

        for source in old.pop('sources'):
            source.pop('retrieved', None)
            new.add_source(**source)

        ext_title = old.pop('+extended_title', None)
        if ext_title:
            new.add_title(ext_title, note='Extended Title')
        official_title = old.pop('+official_title', None)
        if official_title:
            new.add_title(official_title, note='Official Title')

        to_extras = ['+status', '+final_disposition', '+volume_chapter', '+ld_number', '+referral',
                     '+companion', '+description', '+fiscal_note_probable:',
                     '+preintroduction_required:', '+drafter', '+category:', '+chapter',
                     '+requester', '+transmittal_date:', '+by_request_of', '+bill_draft_number:',
                     '+bill_lr', '+bill_url', '+rcs_num', '+fiscal_note', '+impact_clause', '+fiscal_notes',
                     '+short_title', '+type_', '+conference_committee', 'conference_committee',
                     '+companion_bill_ids', '+additional_information']
        for k in to_extras:
            v = old.pop(k, None)
            if v:
                new.extras[k.replace('+', '')] = v

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
            vote.pop('vote_id')
            vote.pop('+bill_chamber', None)
            vote.pop('+session', None)
            vote.pop('+bill_id', None)
            vote.pop('+bill_session', None)
            vote.pop('committee', None)
            vote.pop('committee_id', None)
            vtype = vote.pop('type', 'passage')

            if vtype == 'veto_override':
                vtype = ['veto-override']
            elif vtype == 'amendment':
                vtype = ['amendment-passage']
            elif vtype == 'other':
                vtype = ''
            else:
                vtype = ['bill-passage']

            # most states need identifiers for uniqueness, just do it everywhere
            identifier = vote['date'] + '-' + str(vote_no)
            vote_no += 1

            chamber = vote.pop('chamber')
            if chamber == 'upper' and self.state in ('ne', 'dc'):
                chamber = 'legislature'
            elif chamber == 'joint':
                chamber = 'legislature'

            newvote = Vote(legislative_session=vote.pop('session'),
                           motion_text=vote.pop('motion'),
                           result='pass' if vote.pop('passed') else 'fail',
                           chamber=chamber,
                           start_date=vote.pop('date'),
                           classification=vtype,
                           bill=new,
                           identifier=identifier)
            for vt in ('yes', 'no', 'other'):
                newvote.set_count(vt, vote.pop(vt + '_count'))
                for name in vote.pop(vt + '_votes'):
                    newvote.vote(vt, name['name'])

            for source in vote.pop('sources'):
                source.pop('retrieved', None)
                newvote.add_source(**source)

            if not newvote.sources:
                newvote.sources = new.sources

            to_extras = ['+record', '+method', 'method', '+filename', 'record', '+action',
                         '+location', '+rcs_num', '+type_', '+threshold', '+other_vote_detail',
                         '+voice_vote']
            for k in to_extras:
                v = vote.pop(k, None)
                if v:
                    newvote.extras[k.replace('+', '')] = v

            assert not vote, vote.keys()
            yield newvote

        assert not old, old.keys()

        yield new


    def scrape(self):
        method = 'metadata/{}?'.format(self.state)
        self.metadata = self.api(method)

        for page in range(1, 100):
            method = 'bills/?state={}&fields=id&per_page=2000&page={}'.format(self.state, page)
            results = self.api(method)
            if not results:
                break
            for result in results:
                yield from self.scrape_bill(result['id'])
