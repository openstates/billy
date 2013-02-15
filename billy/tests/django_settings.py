DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'billy_tests.db',
    }
}

INSTALLED_APPS = ('billy.web.api',)
SECRET_KEY = 'a-non-secret'
ROOT_URLCONF = 'billy.web.urls'
