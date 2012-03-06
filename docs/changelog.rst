scrapelib changelog
===================

0.9.7
-----
    * lots of improvements to billy admin
    * removal of never-used RSS emitter
    * drop billy-util districtcsv in favor of an admin view
    * addition of billy-update --oyster argument, adds tracking of versions
    * bugfix: stop silently swallowing errors in subject csvs

0.9.6
-----
**27 February 2012**
    * add alternate_bill_ids and related functionality (needed for TN)
    * updated oysterize command to work with oyster >= 0.3
    * added initial work on class-based models
    * added new beginning of web frontend
    * added run logging work
    * bugfix: billy-util broken by jenkins command
    * bugfix: random_bill restricted session

0.9.5
-----
**21 February 2012**
    * added doc_ids on versions and documents
    * API: add boundary_id to legislator responses (experimental)
    * browse: MOM legislator merge tool
    * browse: improved browse templates & random_bill
    * scrapers: --cache_dir argument added
    * scrapers: _partial_vote_bill_id flag added for Rhode Island
    * bugfix: boundary API method returning first polygon
    * bugfix: dotted keys in reports
    * bugfix: billy-util retire
    * bugfix: unicode error in loadlegislators


0.9.4
-----
**20 January 2012**
    * lots of fixes and improvements to browse
        * new /bills/ view
        * row highlighting
        * unmatched_leg_ids page
        * other_actions page
        * json views
        * random_bill/?bad_vote_counts
    * new and fixed utils
        * districtcsv for generating district CSV stubs
        * prunecommittees for removing old committees
        * load_legislators fixed
    * improve session handling
        * session_list in metadata file
        * missing sessions trigger an error
    * new capitol_maps feature in metadata
    * latest_only can be a flag on scrapers that only work for latest term
    * addition of optional mimetype on documents & versions
    * promote legislator's url to a non + field
    * replace all csv usage with unicodecsv
    * API: block requests for over 5000 bills at once


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
