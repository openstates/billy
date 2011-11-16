=============
Billy Scripts
=============

Billy is primarily composed of a handful of scripts that help facilitate the scraping, import, and cleanup process.

Scraping
========

.. program:: billy-scrape

:program:`billy-scrape` <STATE>
-------------------------------

.. option:: MODULE

    state scraper module name (eg. nc) [required]

.. option:: --alldata

    include all available scrapers

.. option:: --bills, --legislators, --votes, --committees, --events

    include (bill, legislator, vote, committee, event) scraper
    (can specify multiple)

.. option:: --upper, --lower

    scrape upper/lower chamber (if neither is specified will include both)

.. option:: -v, --verbose

    be verbose (use multiple times for more verbosity)

.. option:: -s SESSION, --session SESSION

    session(s) to scrape, must be present in state's metadata

.. option:: -t TERM, --term TERM

    term(s) to scrape, must be present in state's metadata

.. option:: --strict

    fail immediately when encountering validation warnings

.. option:: -n, --no_cache

    do not use cache

.. option:: --fastmode

    operate in "fast mode", using cached version when possible and
    removing --rpm induced delays

.. option:: -r RPM, --rpm RPM

    set maximum number of requests per minute (default: 60)

.. option:: --timeout TIMEOUT

    set HTTP timeout in seconds (default: 10s)

.. option:: --import

    import data to MongoDB database after scraping is complete

.. option:: --importonly

    same as specifying --import but skips scrape step
