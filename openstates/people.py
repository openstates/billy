from pupa.scrape import Organization, Membership, Person
from pupa.utils import make_psuedo_id
from .base import OpenstatesBaseScraper

birthdays = {
    'ALL000035': '1965-03-20',
    'ALL000138': '0000',
}


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

    def process_role(self, new, role, leg_id, skip_member=False):
        start, end = self.get_term_years(role['term'])
        com_id = role.get('committee_id', None)
        if role['type'] == 'committee member':
            if com_id:
                self._roles.add((leg_id, com_id, role.get('position', 'member'), start, end))
        elif role['type'] == 'chair':
            if com_id:
                self._roles.add((leg_id, com_id, 'chair', start, end))
        elif role['type'] == 'member':
            if not skip_member:
                # add party & district for this old role
                district = role['district'].strip('(').strip(')').strip().replace('\u200b', '').lstrip('0')
                if 'Replication or Save Conflict' in district:
                    return
                if self.state in('ne', 'dc'):
                    role['chamber'] = 'legislature'
                new.add_term('member', role['chamber'], district=district,
                             start_date=str(start), end_date=str(end))
        elif role['type'] == 'Lt. Governor':
            pass # handle this!
        elif role['type'] in ('Senate President', 'Minority Whip', 'Majority Whip',
                              'Majority Floor Leader', 'Speaker Pro Tem', 'Majority Caucus Chair',
                              'Minority Caucus Chair', 'Minority Floor Leader', 'Speaker of the House',
                              'President Pro Tem',
                             ):
            pass # TODO: handle these!
        elif role['type'] == 'substitute':
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
        old.pop('office_address', None)
        old.pop('office_phone', None)

        # translated
        district = old.pop('district', None)
        chamber = old.pop('chamber', None)
        image = old.pop('photo_url', '')
        name = old.pop('full_name')
        party = old.pop('party', None)

        if party == 'Nonpartisan' or party == 'Unknown':
            party = None
        elif party == 'Democrat':
            party = 'Democratic'

        if self.state in('ne', 'dc'):
            chamber = 'legislature'

        if old['roles'] and 'Lt. Governor' in [x['type'] for x in old['roles']]:
            new = Person(name=name, district=district, party=party, image=image)
            self.jurisdiction._executive.add_post(
                'Lt. Governor',
                'lt-gov'
            )
            membership = Membership(
                person_id=new._id,
                role="Lt. Governor",
                organization_id=self.jurisdiction._executive._id
            )
            new._related.append(membership)
        else:
            new = Person(name=name, district=district, primary_org=chamber, party=party,
                         image=image)

        if id in birthdays:
            new.birth_date = birthdays[id]

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
                    if 'Office Hours' in office[key] and self.state == 'pa':
                        for x in office[key].split('Office Hours: '):
                            if x:
                                new.add_contact_detail(type=type, value=x, note=office['name'])
                    else:
                        new.add_contact_detail(type=type, value=office[key], note=office['name'])

        # links
        link = old.pop('url', None)
        if link:
            new.add_link(link)

        # sources
        for source in old.pop('sources'):
            source.pop('retrieved', None)
            source.pop('+page', None)
            new.add_source(**source)

        # roles
        for role in old.pop('roles'):
            self.process_role(new, role, leg_id=id, skip_member=True)

        for role_list in old.pop('old_roles', {}).values():
            for role in role_list:
                self.process_role(new, role, leg_id=id)

        # ignore most of the names for now
        old.pop('first_name')
        old.pop('middle_name')
        old.pop('suffixes')
        old.pop('nickname', None)
        new.sort_name = old.pop('last_name')

        # keys to keep
        to_extras = ['+occupation', '+twitter', '+facebook_url', '+sworn_in_date', '+profession',
                     '+secretary', '+office_hours', '+resident_county', '+district_name',
                     '+leg_status', '+legal_position', '+gender', '+title', '+start_year',
                     '+end_date', 'occupation', '+biography', '+oregon_member_id',
                    ]
        for k in to_extras:
            v = old.pop(k, None)
            if v:
                new.extras[k.replace('+', '')] = v

        # keys not to keep
        to_pop = ['+office_fax', '+phone', '+room', '+fax', '+email', '+url', '+photo', '+notice',
                  '+page', '+suffix', '+city', '+address', '+additional_info_url', '+contact_form',
                  '+fax_number', '+phone_number', '+business_phone', '+email_address', '+img_url',
                  '+office_phone', '+disctict_name', '+office_loc', '+leg_url', '+office',
                  '+district_address', '+capital_address', '+bis_phone', '+capital_phone',
                  '+org_info', '+role', '+other_phone', '+home_phone', '+zip', '+zipcode',
                  '+county', '+capitol_phone', '+image_url', '+header', '+town_represented',
                  '+full_address', '+capitol_address', '+website', '+district_phone',
                  '+district_offices', '+party', '+district', '+capitol_office', '+office_address',
                  '2008-2011',
                 ]
        for k in to_pop:
            old.pop(k, None)

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
        old.pop('+short_name', None)
        old.pop('+session', None)
        old.pop('+az_committee_id', None)

        com = old.pop('committee')
        sub = old.pop('subcommittee')
        parent_id = old.pop('parent_id')
        chamber = old.pop('chamber')
        if chamber == 'joint':
            chamber = ''
        if self.state in('ne', 'dc'):
            chamber = 'legislature'

        if sub:
            if parent_id:
                print(id, parent_id)
                parent = self._committees[parent_id]._id
                new = Organization(sub, parent_id=parent, classification='committee')
            else:
                new = Organization(com + ': ' + sub, chamber=chamber, classification='committee')
        else:
            new = Organization(com, chamber=chamber, classification='committee')
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
            if role['leg_id']:
                self._roles.add((role['leg_id'], id, role['role'], start, end))

        to_extras = ['+twitter', '+description', '+code', '+secretary', '+office_hours',
                     '+office_phone', '+meetings_info', '+status', '+aide', '+contact_info',
                     '+comm_type', 'comm_type', 'aide', 'contact_info', '+town_represented',
                     '+action_code',
                    ]
        for k in to_extras:
            v = old.pop(k, None)
            if v:
                new.extras[k.replace('+', '')] = v

        assert not old, old.keys()

        return new


    def scrape(self):
        method = 'metadata/{}?'.format(self.state)
        self.metadata = self.api(method)

        method = 'legislators/?state={}&fields=id&active=False'.format(self.state)
        for result in self.api(method):
            if result['id'] not in ('NJL000013',):
                yield self.scrape_legislator(result['id'])

        method = 'committees/?state={}&fields=id,parent_id'.format(self.state)
        results = sorted(self.api(method), key=lambda x: x.get('parent_id', '') or '')
        for result in results:
            yield self.scrape_committee(result['id'])

        for leg_id, com_id, role, start, end in self._roles:

            # resolve OpenStates committee id to JSON ids
            if com_id in self._committees:
                com_id = self._committees[com_id]._id
            else:
                continue

            if leg_id == 'NJL000013':
                leg_id = 'NJL000015'
            yield Membership(person_id=self._people[leg_id]._id, organization_id=com_id,
                             role=role, label=role, start_date=str(start), end_date=str(end))
