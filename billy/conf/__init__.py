import os
import sys
import argparse
import logging

from billy.conf import default_settings

base_arg_parser = argparse.ArgumentParser(add_help=False)

global_group = base_arg_parser.add_argument_group('global settings',
                              'settings that apply to all billy commands')

global_group.add_argument('-v', '--verbose', action='count',
                          dest='verbose', default=False,
                          help=("be verbose (use multiple times for "
                                "more debugging information)"))
global_group.add_argument('--mongo_host', help='mongo host', dest='MONGO_HOST')
global_group.add_argument('--mongo_port', help='mongo port', dest='MONGO_PORT')
global_group.add_argument('--mongo_db', help='mongo database name',
                          dest='MONGO_DATABASE')
global_group.add_argument('--manual_data_dir', dest='BILLY_MANUAL_DATA_DIR')


class Settings(object):
    def __init__(self):
        pass

    def update(self, module):
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
