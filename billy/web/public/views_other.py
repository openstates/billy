"""
    views that are not state/object specific
"""

from billy import db

from django.shortcuts import render

def downloads(request):
    states = sorted(db.metadata.find(), key=lambda x:x['name'])
    return render(request, 'billy/web/public/downloads.html',
                  {'states': states})
