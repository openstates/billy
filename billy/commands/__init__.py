"""
    defines a command extension system that is used by billy-util

    new commands can be added by deriving from BaseCommand and overriding a few
    attributes:
        name: name of subcommand
        help: help string displayed for subcommand
        add_args(): method that calls `self.add_argument`
        handle(args): method that does the command
"""
class CommandMeta(type):
    """ register subcommands in a central registry """

    def __new__(meta, classname, bases, classdict):
        cls = type.__new__(meta, classname, bases, classdict)

        if not hasattr(cls, 'subcommands'):
            cls.subcommands = []
        else:
            # if this is a unique command
            if cls.name not in [c.name for c in cls.subcommands]:
                cls.subcommands.append(cls)

        return cls

class BaseCommand(object):

    __metaclass__ = CommandMeta

    help = ''

    def __init__(self, subparsers):
        self.subparser = subparsers.add_parser(self.name, help=self.help)
        self.add_args()

    def add_argument(self, *args, **kwargs):
        self.subparser.add_argument(*args, **kwargs)

    def add_args(self):
        pass

    def handle(self, args):
        raise NotImplementedError('commands must implement handle(args)')

