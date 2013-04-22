from billy.scrape import Scraper, SourcedObject


class LegislatorScraper(Scraper):

    scraper_type = 'legislators'

    def scrape(self, chamber, term):
        """
        Grab all the legislators who served in a given term. Must be
        overridden by subclasses.

        Should raise a :class:`NoDataForPeriod` exception if the year is
        invalid.
        """
        raise NotImplementedError('LegislatorScrapers must define a '
                                  'scrape method')

    save_legislator = Scraper.save_object


class Person(SourcedObject):
    def __init__(self, full_name, first_name='', last_name='',
                 middle_name='', **kwargs):
        """
        Create a Person.

        Note: the :class:`~billy.scrape.legislators.Legislator` class
        should be used when dealing with legislators.

        :param full_name: the person's full name
        :param first_name: the first name of this legislator (if specified)
        :param last_name: the last name of this legislator (if specified)
        :param middle_name: a middle name or initial of this legislator
          (if specified)
        """
        super(Person, self).__init__('person', **kwargs)
        self['full_name'] = full_name
        self['first_name'] = first_name
        self['last_name'] = last_name
        self['middle_name'] = middle_name
        self['suffixes'] = kwargs.get('suffixes', '')
        self['roles'] = []
        self['offices'] = []

    def add_role(self, role, term, start_date=None, end_date=None,
                 **kwargs):
        """
        Examples:

        leg.add_role('member', term='2009', chamber='upper',
                     party='Republican', district='10th')
        """
        self['roles'].append(dict(role=role, term=term,
                                  start_date=start_date,
                                  end_date=end_date, **kwargs))

    def add_office(self, type, name, address=None, phone=None, fax=None,
                   email=None, **kwargs):
        """
        Allowed office types:
            capitol
            district
        """
        office_dict = dict(type=type, address=address, name=name, phone=phone,
                           fax=fax, email=email, **kwargs)
        self['offices'].append(office_dict)

    def get_filename(self):
        role = self['roles'][0]
        filename = "%s_%s.json" % (role['term'], self['full_name'])
        return filename.encode('ascii', 'replace')

    def __unicode__(self):
        return self['full_name']


class Legislator(Person):
    def __init__(self, term, chamber, district, full_name,
                 first_name='', last_name='', middle_name='',
                 party='', **kwargs):
        """
        Create a Legislator.

        :param term: the term for this legislator
        :param chamber: the chamber in which this legislator served,
          'upper' or 'lower'
        :param district: the district this legislator is representing, as given
           e.g. 'District 2', '7th', 'District C'.
        :param full_name: the full name of this legislator
        :param first_name: the first name of this legislator (if specified)
        :param last_name: the last name of this legislator (if specified)
        :param middle_name: a middle name or initial of this legislator
          (if specified)
        :param party: the party this legislator belongs to (if specified)

        .. note::

            please only provide the first_name, middle_name and last_name
            parameters if they are listed on the official web site; do not
            try to split the legislator's full name into components yourself.
        """
        super(Legislator, self).__init__(full_name, first_name,
                                         last_name, middle_name,
                                         **kwargs)
        self.add_role('member', term, chamber=chamber, district=district,
                      party=party)

    def get_filename(self):
        role = self['roles'][0]
        filename = "%s_%s_%s_%s.json" % (role['term'],
                                         role['chamber'],
                                         role['district'],
                                         self['full_name'])
        return filename.encode('ascii', 'replace')
