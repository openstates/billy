from django.conf import settings
from django.contrib.auth.decorators import user_passes_test


def debug_or_superuser(user):
    return settings.DEBUG or (user.is_active and user.is_superuser)

is_superuser = user_passes_test(debug_or_superuser)
