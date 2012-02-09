#!/usr/bin/env python
from setuptools import setup, find_packages
from billy import __version__

long_description = open('README.rst').read()

setup(name='billy',
      version=__version__,
      packages=find_packages(),
      package_data={'billy': ['schemas/*.json',
                              'schemas/api/*.json',
                              'schemas/relax/api.rnc'],
                    'billy.site.browse': ['templates/billy/*.html'],
                   },
      author="James Turk",
      author_email="jturk@sunlightfoundation.com",
      license="GPL v3",
      url="http://github.com/sunlightlabs/billy/",
      description='scraping, storing, and sharing legislative information',
      long_description=long_description,
      platforms=['any'],
      entry_points="""
[console_scripts]
billy-scrape = billy.bin.update:scrape_compat_main
billy-update = billy.bin.update:main
billy-util = billy.bin.util:main
""",
    install_requires=[
        "Django>=1.3",
        "argparse==1.1",
        "boto",
        "django-piston",
        "icalendar",
        "jellyfish>=0.1.2",
        "lxml>=2.2",
        "name_tools>=0.1.2",
        "nose",
        "pymongo>=2.0.0",
        "python-votesmart",
        "scrapelib>=0.5.4",
        "unicodecsv",
        "validictory>=0.7.1",
    ]
)
