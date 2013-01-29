import datetime
import urllib

from django.core import urlresolvers
from django.template.defaultfilters import slugify, truncatewords

from billy.core import mdb as db, settings
from billy.utils import get_domain
from .base import Document
from .metadata import Metadata
from .utils import CachedAttribute


class Event(Document):

    collection = db.events

    @property
    def metadata(self):
        return Metadata.get_object(self[settings.LEVEL_FIELD])

    def bill_objects(self):
        '''Returns a cursor of full bill objects for any bills that have
        ids. Not in use anyware as of 12/18/12, but handy to have around.
        '''
        bills = []
        for bill in self['related_bills']:
            if 'id' in bill:
                bills.append(bill['id'])
        return db.bills.find({"_id": {"$in": bills}})

    def bills(self):
        '''Aliases the inaccesible underscore names and mislabed "bill_id"
        field on event['related_bills'], which points to the mongo id,
        whereas everywhere else bill_id refers to the human id like "HB 123."

        The names were updated by 1f24792 on 12/18/12.
        '''
        for bill in self['related_bills']:
            yield bill

    def committees(self):
        committees = []
        for committee in self['participants']:
            if 'id' in committee:
                _id = committee['id']
                if _id:
                    committees.append(_id)

        return db.committees.find({"_id": {"$in": committees}})

    @CachedAttribute
    def committees_dict(self):
        return dict((cmt['_id'], cmt) for cmt in self.committees())

    def get_absolute_url(self):
        slug = slugify(truncatewords(self['description'], 10))
        url = urlresolvers.reverse('event', args=[self[settings.LEVEL_FIELD],
                                                  self['_id']])
        return '%s%s/' % (url, slug)

    def host(self):
        '''Return the host committee.
        '''
        _id = None
        for participant in self['participants']:
            if participant['type'] == 'host':
                if set(['participant_type', 'id']) < set(participant):
                    # This event uses the id keyname "id".
                    if participant['participant_type'] == 'committee':
                        _id = participant['id']
                        if _id is None:
                            continue
                        return self.committees_dict.get(_id)
                else:
                    return participant['participant']

    def other_committees(self):
        comms = self.committees_dict.values()
        comms.remove(self.host())
        return comms

    def host_chairs(self):
        '''Returns a list of members that chair the host committee,
        including "co-chair" and "chairperson." This could concievalby
        yield a false positive if the person's title is 'dunce chair'.
        '''
        chairs = []
        # Host is guaranteed to be a committe or none.
        host = self.host()
        if host is None:
            return
        for member, full_member in host.members_objects:
            if 'chair' in member.get('role', '').lower():
                chairs.append((member, full_member))
        return chairs

    def host_has_multiple_chairs(self):
        '''True or false: are there multiple chairs in the host committee?
        '''
        return 1 < len(self.host_chairs())

    def host_members(self):
        '''Return the members of the host committee.
        '''
        host = self.host()
        if host is None:
            return
        for member, full_member in host.members_objects:
            yield full_member

    def gcal_string(self):

        dt_format = "%Y%m%dT%H%M%SZ"
        start_date = self['when'].strftime(dt_format)
        duration = datetime.timedelta(hours=1)
        end_data = (self['when'] + duration)
        end_date = end_data.strftime(dt_format)

        gcal_info = {
            "action": "TEMPLATE",
            "text": self['description'].encode('utf-8'),
            "dates": "%s/%s" % (start_date, end_date),
            "details": "",
            "location": self['location'].encode('utf-8'),
            "trp": "false",
            "sprop": "http://%s/" % get_domain(),
            "sprop": "name:billy"
        }
        gcal_string = urllib.urlencode(gcal_info)
        return gcal_string
