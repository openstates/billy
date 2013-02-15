import logging

from billy.scrape import Scraper, SourcedObject

logger = logging.getLogger('billy')


class BillScraper(Scraper):

    scraper_type = 'bills'

    def scrape(self, chamber, session):
        """
        Grab all the bills for a given chamber and session. Must be
        overridden by subclasses.

        Should raise a :class:`NoDataForPeriod` exception if it is
        not possible to scrape bills for the given session.
        """
        raise NotImplementedError('BillScrapers must define a scrape method')

    save_bill = Scraper.save_object


class Bill(SourcedObject):
    """
    Object representing a piece of legislation.

    See :class:`~billy.scrape.SourcedObject` for notes on
    extra attributes/fields.
    """

    def __init__(self, session, chamber, bill_id, title, **kwargs):
        """
        Create a new :obj:`Bill`.

        :param session: the session in which the bill was introduced.
        :param chamber: the chamber in which the bill was introduced:
          either 'upper' or 'lower'
        :param bill_id: an identifier assigned to this bill by the legislature
          (should be unique within the context of this chamber/session)
          e.g.: 'HB 1', 'S. 102', 'H.R. 18'
        :param title: a title or short description of this bill provided by
          the official source

        Any additional keyword arguments will be associated with this
        bill and stored in the database.
        """
        super(Bill, self).__init__('bill', **kwargs)
        self._seen_versions = set()
        self['session'] = session
        self['chamber'] = chamber
        self['bill_id'] = bill_id
        self['title'] = title
        self['sponsors'] = []
        self['votes'] = []
        self['versions'] = []
        self['actions'] = []
        self['documents'] = []
        self['alternate_titles'] = []
        self['companions'] = []

        if not 'type' in kwargs or not kwargs['type']:
            self['type'] = ['bill']
        elif isinstance(kwargs['type'], basestring):
            self['type'] = [kwargs['type']]
        else:
            self['type'] = list(kwargs['type'])

    def add_sponsor(self, type, name, **kwargs):
        """
        Associate a sponsor with this bill.

        :param type: the type of sponsorship, e.g. 'primary', 'cosponsor'
        :param name: the name of the sponsor as provided by the official source
        """
        self['sponsors'].append(dict(type=type, name=name, **kwargs))

    def add_document(self, name, url, mimetype=None, **kwargs):
        """
        Add a document or media item that is related to the bill.
        Use this method to add documents such as Fiscal Notes, Analyses,
        Amendments, or public hearing recordings.

        :param name: a name given to the document, e.g.
                     'Fiscal Note for Amendment LCO 6544'
        :param url: link to location of document or file
        :param mimetype: MIME type of the document

        If multiple formats of a document are provided, a good rule of
        thumb is to prefer text, followed by html, followed by pdf/word/etc.
        """
        d = dict(name=name, url=url, **kwargs)
        if mimetype:
            d['mimetype'] = mimetype
        self['documents'].append(d)

    def add_version(self, name, url, mimetype=None, on_duplicate='error',
                    **kwargs):
        """
        Add a version of the text of this bill.

        :param name: a name given to this version of the text, e.g.
                     'As Introduced', 'Version 2', 'As amended', 'Enrolled'
        :param url: the location of this version on the legislative website.
        :param mimetype: MIME type of the document
        :param on_duplicate: What to do if a duplicate is seen:
            error - default option, raises a ValueError
            ignore - add the document twice (rarely the right choice)
            use_new - use the new name, removing the old document
            use_old - use the old name, not adding the new document

        If multiple formats are provided, a good rule of thumb is to
        prefer text, followed by html, followed by pdf/word/etc.
        """
        if not mimetype:
            raise ValueError('mimetype parameter to add_version is required')
        if on_duplicate != 'ignore':
            if url in self._seen_versions:
                if on_duplicate == 'error':
                    raise ValueError('duplicate version url %s' % url)
                elif on_duplicate == 'use_new':
                    # delete the old version
                    self['versions'] = [v for v in self['versions']
                                        if v['url'] != url]
                elif on_duplicate == 'use_old':
                    return       # do nothing
            self._seen_versions.add(url)

        d = dict(name=name, url=url, mimetype=mimetype, **kwargs)
        self['versions'].append(d)

    def add_action(self, actor, action, date, type=None, committees=None,
                   legislators=None, **kwargs):
        """
        Add an action that was performed on this bill.

        :param actor: a string representing who performed the action.
          If the action is associated with one of the chambers this
          should be 'upper' or 'lower'. Alternatively, this could be
          the name of a committee, a specific legislator, or an outside
          actor such as 'Governor'.
        :param action: a string representing the action performed, e.g.
                       'Introduced', 'Signed by the Governor', 'Amended'
        :param date: the date/time this action was performed.
        :param type: a type classification for this action
        ;param committees: a committee or list of committees to associate with
                           this action
        """

        def _cleanup_list(obj, default):
            if not obj:
                obj = default
            elif isinstance(obj, basestring):
                obj = [obj]
            elif not isinstance(obj, list):
                obj = list(obj)
            return obj

        type = _cleanup_list(type, ['other'])
        committees = _cleanup_list(committees, [])
        legislators = _cleanup_list(legislators, [])

        if 'committee' in kwargs:
            raise ValueError("invalid param 'committee' passed to add_action, "
                             "must use committees")

        if isinstance(committees, basestring):
            committees = [committees]

        related_entities = []         # OK, let's work some magic.
        for committee in committees:
            related_entities.append({
                "type": "committee",
                "name": committee
            })

        for legislator in legislators:
            related_entities.append({
                "type": "legislator",
                "name": legislator
            })

        self['actions'].append(dict(actor=actor, action=action,
                                    date=date, type=type,
                                    related_entities=related_entities,
                                    **kwargs))

    def add_vote(self, vote):
        """
        Associate a :class:`~billy.scrape.votes.Vote` object with this
        bill.
        """
        self['votes'].append(vote)

    def add_title(self, title):
        """
        Associate an alternate title with this bill.
        """
        self['alternate_titles'].append(title)

    def add_companion(self, bill_id, session=None, chamber=None):
        """
        Associate another bill with this one.

        If session isn't set it will be set to self['session'].
        """
        companion = {'bill_id': bill_id,
                     'session': session or self['session'],
                     'chamber': chamber}
        self['companions'].append(companion)

    def get_filename(self):
        filename = "%s_%s_%s.json" % (self['session'], self['chamber'],
                                      self['bill_id'])
        return filename.encode('ascii', 'replace')

    def __unicode__(self):
        return "%s %s: %s" % (self['chamber'], self['session'],
                              self['bill_id'])
