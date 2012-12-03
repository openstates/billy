from collections import defaultdict

from .base import BaseTestCase


class DistrictsTestCase(BaseTestCase):

    abbr = 'ex'
    url_tmpl = '/api/v1/districts/{abbr}/'
    url_args = dict(abbr=abbr)

    def test(self):
        expected = districts = list(self.db.districts.find(
            {'abbr': self.abbr}))

        legislators = self.db.legislators.find(
            {'state': self.abbr}, fields={
                '_id': 0,
                'leg_id': 1,
                'chamber': 1,
                'district': 1,
                'full_name': 1})

        leg_dict = defaultdict(list)
        for leg in legislators:
            leg_dict[(leg.pop('chamber'), leg.pop('district'))].append(leg)
        for dist in districts:
            dist['legislators'] = leg_dict[(dist['chamber'], dist['name'])]
            # Rename the id for the api.
            dist['id'] = dist.pop('_id')

        self.assertEquals(self.json, expected)


class ChamberDistrictsTestCase(BaseTestCase):

    abbr = 'ex'
    chamber = 'lower'
    url_tmpl = '/api/v1/districts/{abbr}/{chamber}/'
    url_args = dict(abbr=abbr, chamber=chamber)

    def test(self):
        expected = districts = list(self.db.districts.find(
            {'abbr': self.abbr, 'chamber': self.chamber}))

        legislators = self.db.legislators.find(
            {'state': self.abbr, 'chamber': self.chamber},
            fields={
                '_id': 0,
                'leg_id': 1,
                'chamber': 1,
                'district': 1,
                'full_name': 1})

        leg_dict = defaultdict(list)
        for leg in legislators:
            leg_dict[(leg.pop('chamber'), leg.pop('district'))].append(leg)
        for dist in districts:
            dist['legislators'] = leg_dict[(dist['chamber'], dist['name'])]
            # Rename the id for the api.
            dist['id'] = dist.pop('_id')

        self.assertEquals(self.json, expected)
