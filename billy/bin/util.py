import argparse
import logging
import importlib

from billy.core import settings, base_arg_parser
from billy.bin.commands import BaseCommand

logger = logging.getLogger('billy')

COMMAND_MODULES = (
    'billy.bin.commands.download_photos',
    'billy.bin.commands.ensure_indexes',
    'billy.bin.commands.elasticsearch_push',
    'billy.bin.commands.dump',
    'billy.bin.commands.update_external_ids',
    'billy.bin.commands.update_leg_ids',
    'billy.bin.commands.loaddistricts',
    'billy.bin.commands.unsubscribe',
)


def import_command_module(mod):
    try:
        importlib.import_module(mod)
    except ImportError as e:
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
    subcommands[args.subcommand].handle(args)

if __name__ == '__main__':
    main()
