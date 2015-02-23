import logging

from billy.core import user_db
from billy.bin.commands import BaseCommand

logger = logging.getLogger('billy')


class UnsubscribeCommand(BaseCommand):
    name = 'unsubscribe'
    help = 'Load in the Open States districts'

    def add_args(self):
        self.add_argument('user', metavar='USER', type=str,
                          help='user to unsubscribe')

    def handle(self, args):
        user = args.user
        bills = user_db.favorites.find({"username": user}).count()
        print("About to flip off {} bills. Is that OK?".format(bills))
        print(" (if it's not, control-c this guy, otherwise hit enter")
        raw_input()
        print("Updated entries.".format(user_db.favorites.update({
            "username": user
        }, {"$set": {"is_favorite": False}}, multi=True)))

        # for bill in user_db.favorites.find({"username": user}):
        #     print(bill)
