#!/bin/sh

python -c 'import sys; print(sys.version_info[0])' | grep 3 &> /dev/null
if [ $? = 0 ]; then
    nosetests # don't run Django tests for Py3
else
    nosetests && django-admin.py test --settings=billy.tests.django_settings --pythonpath=.
fi
