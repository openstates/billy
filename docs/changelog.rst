scrapelib changelog
===================

0.9.3
-----
    * force tests to use a test database
    * --mongo_host, --mongo_db, --mongo_port command line options
    * sneaky_update_filter option added, can ignore minor updates
    * API bugfix when chamber isn't specified on bill lookup
    * billy-import replaced by --import[only] flag to billy-scrape
    * change import to use logger instead of unbuffered print statements
    * removed billy-generate-stats and replaced with robust billy-report
    * updated browse interface
    * billy-export replaces billy-dump-*

0.9.2
-----
**26 September 2011**
    * documentation improvements/moved to readthedocs.org
    * load settings from a ``billy_settings.py`` file
    * addition of ``SCRAPER_PATHS`` argument

0.9.1
-----
**23 September 2011**
    * packaging bugfix

0.9.0
-----
**23 September 2011**
    * initial release as used by Open States
