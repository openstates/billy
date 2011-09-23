import os

MONGO_HOST = 'localhost'
MONGO_PORT = 27017
MONGO_DATABASE = 'billy'

API_BASE_URL = 'http://openstates.org/api/v1/'

SCRAPER_PATHS = []

BILLY_DATA_DIR = os.path.join(os.getcwd(), 'data')
BILLY_CACHE_DIR = os.path.join(os.getcwd(), 'cache')
BILLY_ERROR_DIR = os.path.join(os.getcwd(), 'errors')
BILLY_MANUAL_DATA_DIR = os.path.join(os.getcwd(), 'manual_data')

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

BILLY_LEVEL_FIELDS = {
    'country': ('country',),
    'state': ('state', 'country'),
}

SCRAPELIB_TIMEOUT = 600
SCRAPELIB_RETRY_ATTEMPTS = 3
SCRAPELIB_RETRY_WAIT_SECONDS = 20
