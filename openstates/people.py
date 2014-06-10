from pupa.scrape import Legislator, Committee
from .base import OpenstatesBaseScraper


class OpenstatesPersonScraper(OpenstatesBaseScraper):

    _committees = {}

    def scrape_legislator(self, legislator_id):
        old = self.api('legislators/' + legislator_id + '?')
        # just not needed
        old.pop('id')
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
        photo = old.pop('photo_url')
        name = old.pop('full_name')
        party = old.pop('party')

        kwargs = {}
        if photo:
            kwargs['image'] = photo

        new = Legislator(name=name, district=district, chamber=chamber, party=party, **kwargs)

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

        # TODO: role stuff
        old.pop('roles')
        old.pop('old_roles', None)
        # TODO: name stuff
        old.pop('first_name')
        old.pop('last_name')
        old.pop('middle_name')
        old.pop('suffixes')
        old.pop('nickname', None)

        to_pop = []
        for key, val in old.items():
            if key.startswith('+'):
                new.extras[key[1:]] = val
                to_pop.append(key)
        for k in to_pop:
            old.pop(k)

        assert not old, old.keys()

        return new

    def scrape_committee(self, committee_id):
        old = self.api('committees/' + committee_id + '?')
        old.pop('id')
        old.pop('created_at')
        old.pop('updated_at')
        old.pop('country', None)
        old.pop('level', None)
        old.pop('state')
        old.pop('votesmart_id')

        com = old.pop('committee')
        sub = old.pop('subcommittee')
        parent_id = old.pop('parent_id')
        if sub:
            parent = self._committees[parent_id].id
            new = Committee(sub, chamber=old.pop('chamber'), parent_id=parent)
        else:
            new = Committee(com, chamber=old.pop('chamber'))
            assert parent_id is None

        # all_ids
        for id in old.pop('all_ids'):
            new.add_identifier(id, scheme='openstates')
            self._committees[id] = new

        # sources
        for source in old.pop('sources'):
            new.add_source(**source)

        assert not old, old.keys()


    def scrape(self):
        method = 'legislators/?state={}&fields=id'.format(self.state)
        for result in self.api(method):
            yield self.scrape_legislator(result['id'])

        method = 'committees/?state={}&fields=id'.format(self.state)
        results = sorted(self.api(method), key=lambda x: x.get('parent_id', '') or '')
        for result in results:
            yield self.scrape_committee(result['id'])
