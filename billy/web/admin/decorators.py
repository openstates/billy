from django.contrib.auth.decorators import user_passes_test


def debug_or_superuser(user):
    return (user.is_active and user.is_superuser)

is_superuser = user_passes_test(debug_or_superuser, login_url='/djadmin/login/')
