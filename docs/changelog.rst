scrapelib changelog
===================

0.9.3
-----
**30 November 2011**
    * force tests to use a test database
    * --mongo_host, --mongo_db, --mongo_port command line options
    * sneaky_update_filter option added, can ignore minor updates
    * API bugfix when chamber isn't specified on bill lookup
    * change importers to use logger instead of unbuffered print statements
    * billy-update
        * billy-scrape deprecated and replaced with billy-update
        * billy-import, billy-bill-scrape, billy-import-districts replaced
    * billy-util
        * takes place of all utility scripts that didn't get merged into billy-update
    * reporting
        * removed billy-generate-stats and replaced with robust reporting
        * updated browse interface to use reports
        * browse interface also got a partial facelift (more to come)

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
