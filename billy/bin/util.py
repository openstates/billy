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

def scan_plugin_dir(dir):
    if not dir.endswith('/'):
        dir = dir + '/'
    sys.path.insert(0, dir)
    for fname in glob.glob(dir + '[a-zA-Z]*.py'):
        name = fname.replace(dir, '').replace('.py', '')
        try:
            __import__(name)
        except ImportError, e:
            logger.warning(
                'error "{0}" prevented loading of {1} module'.format(e, name))
    sys.path.pop(0)

def main():
    parser = argparse.ArgumentParser(description='generic billy util',
                                     parents=[base_arg_parser])
    subparsers = parser.add_subparsers(dest='subcommand')

    # import command plugins
    plugin_dir = os.path.join(os.path.dirname(__file__), '../commands')
    scan_plugin_dir(plugin_dir)

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
