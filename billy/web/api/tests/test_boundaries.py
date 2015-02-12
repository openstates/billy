from .base import BaseTestCase


class BoundaryTestCase(BaseTestCase):

    abbr = 'ma'
    url_tmpl = '/api/v1/districts/boundary/{boundary_id}/'
    url_args = dict(
        abbr=abbr,
        boundary_id="ocd-division/country:us/state:oh/sldl:3"
    )

    def test_boundary(self):
        expected_keys = set([
            u'name', u'region', u'chamber', u'shape', u'division_id',
            u'abbr', u'boundary_id', u'num_seats', u'id', u'bbox'])
        self.assertEquals(set(self.json), expected_keys)
