import os

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'billy'
MONGO_USER_DATABASE = 'billy_userdata'

BOUNDARY_SERVICE_URL = 'http://localhost:8001/1.0/'
BOUNDARY_SERVICE_SETS = 'sldl-14,sldu-14,nh-12'
ENABLE_ELASTICSEARCH = False
ENABLE_ELASTICSEARCH_PUSH = False
ELASTICSEARCH_HOST = '127.0.0.1:9200'
ELASTICSEARCH_TIMEOUT = 10   # seconds

API_BASE_URL = 'http://127.0.0.1:8000/api/v1/'

SCRAPER_PATHS = []

BILLY_DATA_DIR = os.path.join(os.getcwd(), 'data')
BILLY_CACHE_DIR = os.path.join(os.getcwd(), 'cache')
BILLY_MANUAL_DATA_DIR = os.path.join(os.getcwd(), 'manual_data')

ENABLE_DOCUMENT_VIEW = {}

BILL_FILTERS = {}
LEGISLATOR_FILTERS = {}
EVENT_FILTERS = {}

BILLY_SUBJECTS = [
    'Agriculture and Food',
    'Animal Rights and Wildlife Issues',
    'Arts and Humanities',
    'Budget, Spending, and Taxes',
    'Business and Consumers',
    'Campaign Finance and Election Issues',
    'Civil Liberties and Civil Rights',
    'Commerce',
    'Crime',
    'Drugs',
    'Education',
    'Energy',
    'Environmental',
    'Executive Branch',
    'Family and Children Issues',
    'Federal, State, and Local Relations',
    'Gambling and Gaming',
    'Government Reform',
    'Guns',
    'Health',
    'Housing and Property',
    'Immigration',
    'Indigenous Peoples',
    'Insurance',
    'Judiciary',
    'Labor and Employment',
    'Legal Issues',
    'Legislative Affairs',
    'Military',
    'Municipal and County Issues',
    'Nominations',
    'Other',
    'Public Services',
    'Recreation',
    'Reproductive Issues',
    'Resolutions',
    'Science and Medical Research',
    'Senior Issues',
    'Sexual Orientation and Gender Issues',
    'Social Issues',
    'State Agencies',
    'Technology and Communication',
    'Trade',
    'Transportation',
    'Welfare and Poverty']

PARTY_DETAILS = {
    'Democratic': {'noun': 'Democrat', 'abbreviation': 'D'},
    'Republican': {'noun': 'Republican', 'abbreviation': 'R'},
    'Independent': {'noun': 'Independent', 'abbreviation': 'I'},
}

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': "%(asctime)s %(levelname)s %(name)s: %(message)s",
            'datefmt': '%H:%M:%S'
        }
    },
    'handlers': {
        'default': {'level': 'DEBUG',
                    'class': 'billy.ext.ansistrm.ColorizingStreamHandler',
                    'formatter': 'standard'},
    },
    'loggers': {
        '': {
            'handlers': ['default'], 'level': 'DEBUG', 'propagate': True
        },
        'scrapelib': {
            'handlers': ['default'], 'level': 'INFO', 'propagate': False
        },
        'requests': {
            'handlers': ['default'], 'level': 'WARN', 'propagate': False
        },
        'boto': {
            'handlers': ['default'], 'level': 'WARN', 'propagate': False
        },
    },
}


LEVEL_FIELD = 'state'

SCRAPELIB_RPM = 60
SCRAPELIB_TIMEOUT = 60
SCRAPELIB_RETRY_ATTEMPTS = 3
SCRAPELIB_RETRY_WAIT_SECONDS = 20

AWS_KEY = ''
AWS_SECRET = ''
AWS_BUCKET = ''
