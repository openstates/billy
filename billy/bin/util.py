import os
import sys
import glob
import argparse

from billy.conf import settings, base_arg_parser
from billy.commands import BaseCommand

def scan_plugin_dir(dir):
    if not dir.endswith('/'):
        dir = dir + '/'
    sys.path.insert(0, dir)
    for fname in glob.glob(dir + '[a-zA-Z]*.py'):
        name = fname.replace(dir, '').replace('.py', '')
        try:
            __import__(name)
        except ImportError, e:
            print 'error "{0}" prevented loading of {1} module'.format(e, name)
    sys.path.pop(0)

def main():
    parser = argparse.ArgumentParser(description='generic billy util',
                                     parents=[base_arg_parser])
    subparsers = parser.add_subparsers()

    # import command plugins
    plugin_dir = os.path.join(os.path.dirname(__file__), '../commands')
    scan_plugin_dir(plugin_dir)

    # instantiate all subcommands
    for SubcommandCls in BaseCommand.subcommands:
        command = SubcommandCls(subparsers)

    # parse arguments, update settings, then run the appropriate function
    args = parser.parse_args()
    settings.update(args)
    args.func(args)

if __name__ == '__main__':
    main()
