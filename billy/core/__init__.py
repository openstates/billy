import os
import sys
import argparse
import logging
import logging.config

import pymongo
from pymongo.son_manipulator import SONManipulator
import boto
from boto.s3.connection import OrdinaryCallingFormat

from billy.core import default_settings

base_arg_parser = argparse.ArgumentParser(add_help=False)

global_group = base_arg_parser.add_argument_group(
    'global settings', 'settings that apply to all billy commands')

global_group.add_argument('--mongo_host', help='mongo host', dest='MONGO_HOST')
global_group.add_argument('--mongo_port', help='mongo port', dest='MONGO_PORT')
global_group.add_argument('--mongo_db', help='mongo database name',
                          dest='MONGO_DATABASE')
global_group.add_argument('--manual_data_dir', dest='BILLY_MANUAL_DATA_DIR')
global_group.add_argument('--cache_dir', dest='BILLY_CACHE_DIR')


class Settings(object):
    def __init__(self):
        pass

    def __setattr__(self, attr, val):
        super(Settings, self).__setattr__(attr, val)
        # if logging config is changed, reconfigure logging
        if attr == 'LOGGING_CONFIG':
            logging.config.dictConfig(self.LOGGING_CONFIG)

    def update(self, module):
        if isinstance(module, dict):
            for setting, val in module.iteritems():
                if setting.isupper() and val is not None:
                    setattr(self, setting, val)
        else:
            for setting in dir(module):
                if setting.isupper():
                    val = getattr(module, setting)
                    if val is not None:
                        setattr(self, setting, val)

settings = Settings()
settings.update(default_settings)

try:
    sys.path.insert(0, os.getcwd())
    import billy_settings
    settings.update(billy_settings)
    sys.path.pop(0)
except ImportError:
    logging.warning('no billy_settings file found, continuing with defaults..')

db = None
mdb = None
feeds_db = None
user_db = None
elasticsearch = None
s3bucket = None
_model_registry = {}
_model_registry_by_collection = {}


class ErrorProxy(object):
    def __init__(self, error):
        self.error = error

    def __getattr__(self, attr):
        raise self.error


def _configure_db(host, port, db_name, user_db_name):
    global db
    global mdb
    global feeds_db
    global user_db

    class Transformer(SONManipulator):
        def transform_outgoing(self, son, collection,
                               mapping=_model_registry_by_collection):
            try:
                return mapping[collection.name](son)
            except KeyError:
                return son

    transformer = Transformer()

    try:
        conn = pymongo.Connection(host, port)
        db = conn[db_name]
        mdb = conn[db_name]
        user_db = conn[user_db_name]
        feeds_db = conn['newsblogs']
        mdb.add_son_manipulator(transformer)
        feeds_db.add_son_manipulator(transformer)
    # return a dummy NoDB object if we couldn't connect
    except (pymongo.errors.AutoReconnect,
            pymongo.errors.ConnectionFailure) as e:
        db = ErrorProxy(e)
        mdb = ErrorProxy(e)
        feeds_db = ErrorProxy(e)


def _configure_es(host, timeout):
    import pyelasticsearch
    global elasticsearch
    try:
        elasticsearch = pyelasticsearch.ElasticSearch(host, timeout=timeout,
                                                      max_retries=0)
    except Exception as e:
        elasticsearch = ErrorProxy(e)


def _configure_s3(aws_key, aws_secret, bucket):
    global s3bucket
    try:
        if aws_key and aws_secret and bucket:
            s3bucket = boto.connect_s3(
                aws_key, aws_secret, calling_format=OrdinaryCallingFormat()
                ).get_bucket(bucket)
        else:
            s3bucket = ErrorProxy(ValueError('s3 not configured in settings'))
    except Exception as e:
        s3bucket = ErrorProxy(e)


_configure_db(settings.MONGO_HOST, settings.MONGO_PORT,
              settings.MONGO_DATABASE, settings.MONGO_USER_DATABASE)
if settings.ENABLE_ELASTICSEARCH:
    _configure_es(settings.ELASTICSEARCH_HOST, settings.ELASTICSEARCH_TIMEOUT)
_configure_s3(settings.AWS_KEY, settings.AWS_SECRET, settings.AWS_BUCKET)
