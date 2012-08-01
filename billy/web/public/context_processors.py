

def user(request):
    if hasattr(request, 'user'):
        return {'user':request.user }
    return {}
