from billy.scrape import Scraper, SourcedObject


class CommitteeScraper(Scraper):

    scraper_type = 'committees'

    def scrape(self, chamber, term):
        raise NotImplementedError('CommitteeScrapers must define a '
                                  'scrape method')

    save_committee = Scraper.save_object


class Committee(SourcedObject):
    def __init__(self, chamber, committee, subcommittee=None,
                 **kwargs):
        """
        Create a Committee.

        :param chamber: the chamber this committee is associated with ('upper',
            'lower', or 'joint')
        :param committee: the name of the committee
        :param subcommittee: the name of the subcommittee (optional)
        """
        super(Committee, self).__init__('committee', **kwargs)
        self['chamber'] = chamber
        self['committee'] = committee
        self['subcommittee'] = subcommittee
        self['members'] = kwargs.get('members', [])

    def add_member(self, legislator, role='member', **kwargs):
        """
        Add a member to the committee object.

        :param legislator: name of the legislator
        :param role: role that legislator holds in the committee
            (eg. chairman) default: 'member'
        """
        self['members'].append(dict(name=legislator, role=role,
                                    **kwargs))

    def get_filename(self):
        name = self['committee']
        if self.get('subcommittee', None):
            name += '_%s' % self['subcommittee']

        return "%s_%s.json" % (self['chamber'], name.replace('/', ','))

    def __unicode__(self):
        name = self['committee']
        sub = self.get('subcommittee', None)
        if sub:
            name += ': %s' % sub
        return name
