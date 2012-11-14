import datetime

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods

from billy.core import user_db


def is_favorite(obj_id, obj_type, request, extra_spec=None):
    '''Query database; return true or false.
    '''
    if request.user.is_authenticated():
        spec = dict(obj_id=obj_id, obj_type=obj_type,
                    user_id=request.user.id)

        # Enable the bill search to pass in search terms.
        if extra_spec is not None:
            spec.update(extra_spec)

        doc = user_db.favorites.find_one(spec)

        if doc:
            return doc['is_favorite']

    return False


@login_required
@csrf_protect
@require_http_methods(["POST"])
def set_favorite(request):
    '''Follow/unfollow a bill, committee, legislator.
    '''
    if request.method == "POST":

        # Complain about bogus requests.
        resp400 = HttpResponse(status=400)
        valid_keys = set(['obj_id', 'obj_type', 'is_favorite', 'search_text'])
        if not set(request.POST) < valid_keys:
            return resp400
        valid_types = ['bill', 'legislator', 'committee', 'search']
        if request.POST['obj_type'] not in valid_types:
            return resp400

        # Create the spec.
        spec = dict(
            obj_type=request.POST['obj_type'],
            obj_id=request.POST['obj_id'],
            user_id=request.user.id
            )

        # Toggle the value of is_favorite.
        if request.POST['is_favorite'] == 'false':
            is_favorite = False
        if request.POST['is_favorite'] == 'true':
            is_favorite = True
        is_favorite = not is_favorite

        # Create the doc.
        doc = dict(
            is_favorite=is_favorite,
            timestamp=datetime.datetime.utcnow(),
            )
        doc.update(spec)

        # Create the doc if missing, else update based on the spec.
        user_db.favorites.update(spec, doc, upsert=True)

        return HttpResponse(status=200)
