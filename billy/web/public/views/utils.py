import itertools

from django.views.generic import TemplateView
from django.http import Http404

from billy.models import db, Metadata, DoesNotExist


def templatename(name):
    return 'billy/web/public/%s.html' % name


def mongo_fields(*fields):
    fields = dict(zip(fields, itertools.repeat(1)))


class ListViewBase(TemplateView):
    '''Base class for VoteList, FeedList, etc.

    I tried using generic views for bill lists to cut down the
    boilerplate, but I'm not sure that has succeeded. One downside
    has been the reuse of what attempts to be a generic sort of
    template but in reality has become an awful monster template,
    named "object_list.html." Possibly more tuning needed.
    '''

    template_name = templatename('object_list')

    def get_context_data(self, *args, **kwargs):
        super(ListViewBase, self).get_context_data(*args, **kwargs)
        context = {}
        context.update(column_headers=self.column_headers,
                       rowtemplate_name=self.rowtemplate_name,
                       description_template=self.description_template,
                       object_list=self.get_queryset(),
                       statenav_active=self.statenav_active,
                       abbr=self.kwargs['abbr'],
                       metadata=Metadata.get_object(self.kwargs['abbr']),
                       url=self.request.path,
                       use_table=getattr(self, 'use_table', False))

        # Include the kwargs to enable references to url paramaters.
        context.update(**kwargs)
        return context


class RelatedObjectsList(ListViewBase):
    '''A generic list view where there's a main object, like a
    legislator or state, and we want to display all of the main
    object's "sponsored_bills" or "introduced_bills." This class
    basically hacks the ListViewBase to add the main object into
    the template context so it can be used to generate a phrase like
    'showing all sponsored bills for Wesley Chesebro.'
    '''
    def get_context_data(self, *args, **kwargs):
        context = super(RelatedObjectsList, self).get_context_data(
                                                        *args, **kwargs)
        context.update(obj=self.get_object())
        return context

    def get_object(self):
        try:
            return self.obj
        except AttributeError:
            pass

        try:
            collection_name = self.kwargs['collection_name']
        except KeyError:
            collection_name = self.collection_name

        collection_name = {
            'state': 'metadata',
            }.get(collection_name, collection_name)

        try:
            _id = self.kwargs['_id']
        except KeyError:
            _id = self.kwargs['abbr']

        # Get the related object.
        collection = getattr(db, collection_name)

        try:
            obj = collection.find_one(_id)
        except DoesNotExist:
            raise Http404

        self.obj = obj
        return obj

    def get_queryset(self):

        get = self.request.GET.get

        # Setup the paginator arguments.
        show_per_page = getattr(self, 'show_per_page', 10)
        show_per_page = int(get('show_per_page', show_per_page))
        page = int(get('page', 1))
        if 100 < show_per_page:
            show_per_page = 100

        objects = getattr(self.get_object(), self.query_attr)

        # The related collection of objects might be a
        # function or a manager class.
        # This is to work around a pain-point in models.py.
        if callable(objects):
            kwargs = {}
            sort = getattr(self, 'sort', None)
            if sort is not None:
                kwargs['sort'] = sort
            objects = objects(**kwargs)

        # Apply any specified sorting.
        sort_func = getattr(self, 'sort_func', None)
        sort_reversed = bool(getattr(self, 'sort_reversed', None))
        if sort_func:
            objects = sorted(objects, key=sort_func,
                             reverse=sort_reversed)

        paginator = self.paginator(objects, page=page,
                                   show_per_page=show_per_page)
        return paginator
