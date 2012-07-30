===================
Billy Configuration
===================

Billy has a global configuration object at :data:`billy.conf.settings` that is used in scraping, import, and serving the API.

All billy scripts attempt to load a :mod:`billy_settings` module which should
either be on the import path or in the working directory, this file can
contain overrides and custom settings.  As of 0.9.2 if no :mod:`billy_settings`
module can be located a warning message will be printed to the console.

.. module:: billy.conf

Default Settings
================

:data:`MONGO_HOST`
    Host or IP address of MongoDB server. (default: "localhost")
:data:`MONGO_PORT`
    Port for MongoDB server. (default: "27017")
:data:`MONGO_DATABASE`
    MongoDB database name. (default: "billy")
:data:`API_BASE_URL`
    Public URL that the API can be accessed at.
:data:`SCRAPER_PATHS`
    Paths that scraper modules are stored under, will be added to ``sys.path`` when
    attempting to load scrapers.
:data:`BILLY_DATA_DIR`
    Directory where scraped data should be stored.  (default: "<cwd>/data")
:data:`BILLY_CACHE_DIR`
    Directory where scraper cache should be stored.  (default: "<cwd>/cache")
:data:`BILLY_ERROR_DIR`
    Directory where scraper error dumps should be stored.  (default: "<cwd>/errors")
:data:`BILLY_MANUAL_DATA_DIR`
    Directory where manual data files for matched ids/subjects are stored.  (default: "<cwd>/manual_data")
:data:`BILLY_SUBJECTS`
    List of valid subject names
:data:`SCRAPELIB_TIMEOUT`
    Value (in seconds) for url retrieval timeout.  (default: 600)
:data:`SCRAPELIB_RETRY_ATTEMPTS`
    Number of retries to make if an unexpected failure occurs when downloading a URL.  (default: 3)
:data:`SCRAPELIB_RETRY_WAIT_SECONDS`
    Number of seconds to wait between initial attempt and first retry.  (default: 20)


Command-Line Overrides
======================

Most available scripts can override the above default settings with command line switches:

.. option:: --mongo_host <mongo_host>

    Override :data:`MONGO_HOST`

.. option:: --mongo_port <mongo_port>

    Override :data:`MONGO_PORT`

.. option:: --mongo_db <mongo_db>

    Override :data:`MONGO_DATABASE`

.. option:: -d <data_dir>, --data_dir <data_dir>

    Override :data:`BILLY_DATA_DIR`

.. option:: --cache_dir <cache_dir>

    Override :data:`BILLY_CACHE_DIR`

.. option:: --error_dir <error_dir>

    Override :data:`BILLY_ERROR_DIR`

.. option:: --manual_data_dir <manual_data_dir>

    Override :data:`BILLY_MANUAL_DATA_DIR`

.. option:: --retries <retries>

    Override :data:`SCRAPELIB_RETRY_ATTEMPTS`

.. option:: --retry_wait <retry_wait>

    Override :data:`SCRAPELIB_RETRY_WAIT_SECONDS`
