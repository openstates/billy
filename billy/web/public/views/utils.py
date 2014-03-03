import itertools
import re
import urllib

from django.views.generic import TemplateView
from django.http import Http404
from django.template import Template, Context

from billy.models import db, Metadata


def templatename(name):
    return 'billy/web/public/%s.html' % name


def mongo_fields(*fields):
    fields = dict(zip(fields, itertools.repeat(1)))
    # FIXED the return value was being assigned.
    return fields


def normalize_whitespace(s):
    return re.sub(ur'\s+', ' ', s)


class ListViewBase(TemplateView):
    '''Base class for VoteList, FeedList, etc.

    I tried using generic views for bill lists to cut down the
    boilerplate, but I'm not sure that has succeeded. One downside
    has been the reuse of what attempts to be a generic sort of
    template but in reality has become an awful monster template,
    named "object_list.html." Possibly more tuning needed.

    Context:
        - column_headers
        - rowtemplate_name
        - description_template
        - object_list
        - nav_active
        - abbr
        - metadata
        - url
        - use_table
    '''

    template_name = templatename('object_list')
    nav_active = None

    def get_context_data(self, *args, **kwargs):
        super(ListViewBase, self).get_context_data(*args, **kwargs)

        abbr = self.kwargs['abbr']
        if abbr == 'all':
            metadata = None
        else:
            metadata = Metadata.get_object(abbr)

        context = {}
        context.update(column_headers_tmplname=self.column_headers_tmplname,
                       rowtemplate_name=self.rowtemplate_name,
                       description_template=self.description_template,
                       object_list=self.get_queryset(),
                       nav_active=self.nav_active,
                       abbr=abbr,
                       metadata=metadata,
                       url=self.request.path,
                       use_table=getattr(self, 'use_table', False))

        # Include the kwargs to enable references to url paramaters.
        context.update(**kwargs)

        # Get the formatted page title and description.
        # Wait to render until get_object has been called in subclasses.
        if not getattr(self, 'defer_rendering_title', False):
            for attr in ('title', 'description'):
                if attr not in context:
                    context[attr] = self._render(attr, context,
                                                 request=self.request)

        # Add the correct path to paginated links. Yuck.
        if self.request.GET:
            params = dict(self.request.GET.items())
            if 'page' in params:
                del params['page']
            for k, v in params.iteritems():
                params[k] = unicode(v).encode('utf8')
            context.update(get_params=urllib.urlencode(params))

        return context

    def _render(self, attr, context, **extra_context):
        try:
            template = getattr(self, '%s_template' % attr)
        except AttributeError:
            return
        template = Template(normalize_whitespace(template))
        context.update(**extra_context)
        context = Context(context)
        return template.render(context)


class RelatedObjectsList(ListViewBase):
    '''A generic list view where there's a main object, like a
    legislator or metadata, and we want to display all of the main
    object's "sponsored_bills" or "introduced_bills." This class
    basically hacks the ListViewBase to add the main object into
    the template context so it can be used to generate a phrase like
    'showing all sponsored bills for Wesley Chesebro.'

    Context:
        - obj
        - collection_name

    Templates:
        - defined in subclasses
    '''
    defer_rendering_title = True

    def get_context_data(self, *args, **kwargs):
        context = super(RelatedObjectsList, self).get_context_data(*args,
                                                                   **kwargs)
        context.update(
            obj=self.get_object(),
            collection_name=self.collection_name)

        # Get the formatted page title and description.
        for attr in ('title', 'description'):
            if attr not in context:
                context[attr] = self._render(attr, context)

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

        try:
            _id = self.kwargs['_id']
        except KeyError:
            _id = self.kwargs['abbr']

        if _id == 'all':
            return None

        # Get the related object.
        collection = getattr(db, collection_name)

        obj = collection.find_one(_id)

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

        obj = self.get_object()
        if obj is None:
            raise Http404('RelatedObjectsList.get_object returned None.')
        objects = getattr(obj, self.query_attr)

        # The related collection of objects might be a
        # function or a manager class.
        # This is to work around a pain-point in models.py.
        if callable(objects):
            kwargs = {}
            sort = getattr(self, 'mongo_sort', None)
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

    def _render(self, attr, context):
        try:
            template = getattr(self, '%s_template' % attr)
        except AttributeError:
            return
        template = Template(normalize_whitespace(template))
        context = Context(context)
        return template.render(context)
