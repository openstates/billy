=============
Billy Scripts
=============

Scraping
========

.. program:: billy-update

:program:`billy-update` <STATE>
-------------------------------

.. option:: MODULE

    state scraper module name (eg. nc) [required]

.. option:: --scrape, --import, --report

    Which portions of the update process to run, specifying none implies ``--scrape --import --report``

    --scrape crawls the specified sites and writes data to disk in JSON format
    --import imports the JSON format on disk to billy's MongoDB database
    --report runs a series of reports on data quality and aggregates

.. option:: --bills, --legislators, --votes, --committees, --events

    include (bill, legislator, vote, committee, event) data in (scrape/import/report)
    Specifying none is the same as specifying --bills --legislators --votes --committees

.. option:: --upper, --lower

    process upper/lower chamber (if neither is specified will include both)

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
