import os
import sys
import glob
import argparse
import logging

from billy.conf import settings, base_arg_parser
from billy.utils import configure_logging
from billy.commands import BaseCommand

logger = logging.getLogger('billy')
configure_logging(1)

COMMAND_MODULES = (
    'billy.commands.district_csv_stub',
    'billy.commands.dump',
    'billy.commands.load_legislators',
    'billy.commands.oysterize',
    'billy.commands.prune_committees',
    'billy.commands.retire',
    'billy.commands.serve',
    'billy.commands.update_external_ids',
    'billy.commands.update_leg_ids',
    'billy.commands.validate_api',
)

def import_command_module(mod):
    try:
        __import__(mod)
    except ImportError, e:
        logger.warning(
            'error "{0}" prevented loading of {1} module'.format(e, mod))

def main():
    parser = argparse.ArgumentParser(description='generic billy util',
                                     parents=[base_arg_parser])
    subparsers = parser.add_subparsers(dest='subcommand')

    # import command plugins
    for mod in COMMAND_MODULES:
        import_command_module(mod)

    # instantiate all subcommands
    subcommands = {}
    for SubcommandCls in BaseCommand.subcommands:
        subcommands[SubcommandCls.name] = SubcommandCls(subparsers)

    # parse arguments, update settings, then run the appropriate function
    args = parser.parse_args()
    settings.update(args)
    configure_logging(args.verbose)
    subcommands[args.subcommand].handle(args)

if __name__ == '__main__':
    main()
