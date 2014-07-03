from pupa.scrape import Legislator, Committee, Membership
from .base import OpenstatesBaseScraper


class OpenstatesPersonScraper(OpenstatesBaseScraper):

    _committees = {}
    _people = {}
    _roles = set()

    def get_term_years(self, term_name=None):
        if term_name is None:
            return self.metadata['terms'][-1]['start_year'], self.metadata['terms'][-1]['end_year']
        for term in self.metadata['terms']:
            if term['name'] == term_name:
                return term['start_year'], term['end_year']

    def process_role(self, role, leg_id):
        start, end = self.get_term_years(role['term'])
        if role['type'] == 'committee member':
            # leg_id, com_id, role, start, end
            self._roles.add((leg_id, role['committee_id'], role.get('position', 'member'),
                             start, end))
        elif role['type'] == 'member':
            pass
        else:
            raise Exception("unknown role type: " + role['type'])

    def scrape_legislator(self, legislator_id):
        old = self.api('legislators/' + legislator_id + '?')
        # just not needed
        id = old.pop('id')
        old.pop('created_at')
        old.pop('updated_at')
        old.pop('country', None)
        old.pop('level', None)
        old.pop('state')
        old.pop('leg_id')
        old.pop('active')
        # junk keys
        old.pop('suffix', None)
        old.pop('notice', None)
        old.pop('csrfmiddlewaretoken', None)

        # translated
        district = old.pop('district', None)
        chamber = old.pop('chamber', None)
        image = old.pop('photo_url', '')
        name = old.pop('full_name')
        party = old.pop('party')

        new = Legislator(name=name, district=district, chamber=chamber, party=party, image=image)

        # various ids
        id_types = {'votesmart_id': 'votesmart',
                    'transparencydata_id': 'influence-explorer',
                    'nimsp_id': 'nimsp',
                    'nimsp_candidate_id': 'nimsp-candidate',
                   }
        for idname, scheme in id_types.items():
            val = old.pop(idname, None)
            if val:
                new.add_identifier(val, scheme=scheme)
        for id in old.pop('all_ids'):
            new.add_identifier(id, scheme='openstates')
            self._people[id] = new

        # contact details
        email = old.pop('email', None)
        if email:
            new.add_contact_detail(type='email', value=email, note='')
        office_keys = {'fax': 'fax',
                       'phone': 'voice',
                       'email': 'email',
                       'address': 'address'}
        for office in old.pop('offices'):
            for key, type in office_keys.items():
                if office[key]:
                    new.add_contact_detail(type=type, value=office[key], note=office['name'])

        # links
        link = old.pop('url', None)
        if link:
            new.add_link(link)

        # sources
        for source in old.pop('sources'):
            new.add_source(**source)

        # roles
        for role in old.pop('roles'):
            self.process_role(role, leg_id=id)

        for role_list in old.pop('old_roles', {}).values():
            for role in role_list:
                self.process_role(role, leg_id=id)

        # ignore most of the names for now
        old.pop('first_name')
        old.pop('middle_name')
        old.pop('suffixes')
        old.pop('nickname', None)
        new.sort_name = old.pop('last_name')

        to_pop = []
        for key, val in old.items():
            if key.startswith('+'):
                new.extras[key[1:]] = val
                to_pop.append(key)
        for k in to_pop:
            old.pop(k)

        # ensure we got it all
        assert not old, old.keys()

        return new

    def scrape_committee(self, committee_id):
        old = self.api('committees/' + committee_id + '?')
        id = old.pop('id')
        old.pop('created_at')
        old.pop('updated_at')
        old.pop('country', None)
        old.pop('level', None)
        old.pop('state')
        old.pop('votesmart_id', None)

        com = old.pop('committee')
        sub = old.pop('subcommittee')
        parent_id = old.pop('parent_id')
        chamber = old.pop('chamber')
        if chamber == 'joint':
            chamber = ''

        if sub:
            if parent_id:
                parent = self._committees[parent_id]._id
                new = Committee(sub, chamber=chamber, parent_id=parent)
            else:
                new = Committee(com + ': ' + sub, chamber=chamber)
        else:
            new = Committee(com, chamber=chamber)
            assert parent_id is None

        # all_ids
        for id in old.pop('all_ids'):
            new.add_identifier(id, scheme='openstates')
            self._committees[id] = new

        # sources
        for source in old.pop('sources'):
            new.add_source(**source)

        # members
        start, end = self.get_term_years()
        for role in old.pop('members'):
            # leg_id, com_id, role, start, end
            self._roles.add((role['leg_id'], id, role['role'], start, end))

        assert not old, old.keys()

        return new


    def scrape(self):
        method = 'metadata/{}?'.format(self.state)
        self.metadata = self.api(method)

        method = 'legislators/?state={}&fields=id'.format(self.state)
        for result in self.api(method):
            yield self.scrape_legislator(result['id'])

        method = 'committees/?state={}&fields=id'.format(self.state)
        results = sorted(self.api(method), key=lambda x: x.get('parent_id', '') or '')
        for result in results:
            yield self.scrape_committee(result['id'])

        for leg_id, com_id, role, start, end in self._roles:

            # resolve OpenStates committee id to JSON ids
            if com_id in self._committees:
                com_id = self._committees[com_id]._id
            else:
                com_id = None

            if com_id and leg_id:
                yield Membership(person_id=self._people[leg_id]._id, organization_id=com_id,
                                 role=role, label=role, start_date=str(start), end_date=str(end))
            else:
                pass # TODO: missing com_id or leg_id
