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
            for k, v in params.items():
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


# Source: https://gist.github.com/mishari/5ecfccd219925c04ac32
# DC and PR were found by point-and-click, using "What's here?" on Google Maps
# US is maximum extent of all listed states
GEO_BOUNDS = {
  "US": [
    [-124.836097717285, 17.811],
    [-65.221, 49.3844909667969]
  ],
  "AL": [
    [-88.4731369018555, 30.1375217437744],
    [-84.8882446289062, 35.0080299377441]
  ],
  "AR": [
    [-94.6178131103516, 33.0041046142578],
    [-89.6422424316406, 36.4996032714844]
  ],
  "AZ": [
    [-114.818359375, 31.3321762084961],
    [-109.045196533203, 37.0042610168457]
  ],
  "CA": [
    [-124.482009887695, 32.5295219421387],
    [-114.13077545166, 42.0095024108887]
  ],
  "CO": [
    [-109.060256958008, 36.9924240112305],
    [-102.041580200195, 41.0023612976074]
  ],
  "CT": [
    [-73.7277755737305, 40.9667053222656],
    [-71.7869873046875, 42.0505905151367]
  ],
  "DC": [
    [-77.119760, 38.791647],
    [-76.909397, 38.995551]
  ],
  "DE": [
    [-75.7890472412109, 38.4511260986328],
    [-74.9846343994141, 39.8394355773926]
  ],
  "FL": [
    [-87.6349029541016, 24.3963069915771],
    [-79.9743041992188, 31.0009689331055]
  ],
  "GA": [
    [-85.6051712036133, 30.3557567596436],
    [-80.7514266967773, 35.0008316040039]
  ],
  "IA": [
    [-96.6397171020508, 40.3755989074707],
    [-90.1400604248047, 43.5011367797852]
  ],
  "ID": [
    [-117.243034362793, 41.9880561828613],
    [-111.043563842773, 49.000846862793]
  ],
  "IL": [
    [-91.513053894043, 36.9701309204102],
    [-87.0199203491211, 42.5083045959473]
  ],
  "IN": [
    [-88.0997085571289, 37.7717399597168],
    [-84.7845764160156, 41.7613716125488]
  ],
  "KS": [
    [-102.0517578125, 36.9930801391602],
    [-94.5882034301758, 40.0030975341797]
  ],
  "KY": [
    [-89.5715103149414, 36.4967155456543],
    [-81.9645385742188, 39.1474609375]
  ],
  "LA": [
    [-94.0431518554688, 28.9210300445557],
    [-88.817008972168, 33.019458770752]
  ],
  "MA": [
    [-73.5081481933594, 41.1863288879395],
    [-69.8615341186523, 42.8867149353027]
  ],
  "MD": [
    [-79.4871978759766, 37.8856391906738],
    [-75.0395584106445, 39.7229347229004]
  ],
  "ME": [
    [-71.0841751098633, 42.9561233520508],
    [-66.9250717163086, 47.4598426818848]
  ],
  "MI": [
    [-90.4186248779297, 41.6960868835449],
    [-82.122802734375, 48.3060646057129]
  ],
  "MN": [
    [-97.2392654418945, 43.4994277954102],
    [-89.4833831787109, 49.3844909667969]
  ],
  "MO": [
    [-95.7741470336914, 35.9956817626953],
    [-89.0988388061523, 40.6136360168457]
  ],
  "MS": [
    [-91.6550140380859, 30.1477890014648],
    [-88.0980072021484, 34.9960556030273]
  ],
  "MT": [
    [-116.050003051758, 44.3582191467285],
    [-104.039558410645, 49.0011100769043]
  ],
  "NC": [
    [-84.3218765258789, 33.7528762817383],
    [-75.4001159667969, 36.5880393981934]
  ],
  "ND": [
    [-104.049270629883, 45.9350357055664],
    [-96.5543899536133, 49.0004920959473]
  ],
  "NE": [
    [-104.053520202637, 39.9999961853027],
    [-95.3080520629883, 43.0017013549805]
  ],
  "NH": [
    [-72.55712890625, 42.6970405578613],
    [-70.534065246582, 45.3057823181152]
  ],
  "NJ": [
    [-75.5633926391602, 38.7887535095215],
    [-73.8850555419922, 41.3574256896973]
  ],
  "NM": [
    [-109.050178527832, 31.3323001861572],
    [-103.000862121582, 37.0001411437988]
  ],
  "NV": [
    [-120.005729675293, 35.0018730163574],
    [-114.039642333984, 42.0022087097168]
  ],
  "NY": [
    [-79.7625122070312, 40.4773979187012],
    [-71.8527069091797, 45.0158615112305]
  ],
  "OH": [
    [-84.8203430175781, 38.4031982421875],
    [-80.5189895629883, 42.3232383728027]
  ],
  "OK": [
    [-103.002571105957, 33.6191940307617],
    [-94.4312133789062, 37.0021362304688]
  ],
  "OR": [
    [-124.703544616699, 41.9917907714844],
    [-116.463500976562, 46.2991027832031]
  ],
  "PA": [
    [-80.5210876464844, 39.7197647094727],
    [-74.6894989013672, 42.5146903991699]
  ],
  "PR": [
    [-67.945, 17.881],
    [-65.221, 18.515]
  ],
  "RI": [
    [-71.9070053100586, 41.055534362793],
    [-71.1204681396484, 42.018856048584]
  ],
  "SC": [
    [-83.35400390625, 32.0333099365234],
    [-78.4992980957031, 35.2155418395996]
  ],
  "SD": [
    [-104.05770111084, 42.4798889160156],
    [-96.4363327026367, 45.9454536437988]
  ],
  "TN": [
    [-90.310302734375, 34.9829788208008],
    [-81.6468963623047, 36.6781196594238]
  ],
  "TX": [
    [-106.645652770996, 25.8370609283447],
    [-93.5078201293945, 36.5007057189941]
  ],
  "UT": [
    [-114.053932189941, 36.9979667663574],
    [-109.041069030762, 42.0013885498047]
  ],
  "VA": [
    [-83.6754150390625, 36.5407867431641],
    [-75.2312240600586, 39.4660148620605]
  ],
  "VT": [
    [-73.437744140625, 42.7269325256348],
    [-71.4653549194336, 45.0166664123535]
  ],
  "WA": [
    [-124.836097717285, 45.5437202453613],
    [-116.917427062988, 49.00244140625]
  ],
  "WI": [
    [-92.8881149291992, 42.491943359375],
    [-86.2495422363281, 47.3025016784668]
  ],
  "WV": [
    [-82.6447448730469, 37.2014808654785],
    [-77.7190246582031, 40.638801574707]
  ],
  "WY": [
    [-111.05689239502, 40.9948768615723],
    [-104.052154541016, 45.0034217834473]
  ]
}
