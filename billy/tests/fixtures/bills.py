import datetime
from billy.scrape.bills import Bill

# alias to b while we're working on it
b = bill_with_everything = Bill('S1', 'lower', 'HB1', 'Armadillo Ranching')
b.add_sponsor('primary', 'Washington')
b.add_sponsor('primary', 'Lincoln')
b.add_sponsor('cosponsor', 'Clinton', note='test note')
b.add_document('fiscal note', 'http://example.com/fn1.doc',
               mimetype='application/msword')
b.add_document('fiscal note', 'http://example.com/fn1.html',
               mimetype='text/html')
b.add_version('introduced', 'http://example.com/v1.doc',
              mimetype='application/msword')
b.add_version('introduced', 'http://example.com/v1.html',
              mimetype='text/html')
b.add_action('lower', 'introduced', datetime.date(2012, 1, 1),
             type='bill:introduced', legislators='Washington')
b.add_action('lower', 'passed house without vote', datetime.date(2012, 1, 2),
             type='bill:passed')
b.add_action('upper', 'referred to senate committees',
             datetime.datetime(2012, 2, 1), type='committee:referred',
             committees=['Agriculture', 'Judiciary'])
b.add_action('upper', 'failed in senate', datetime.datetime(2012, 2, 5),
             type=['bill:reading:3', 'bill:failed'], vote_slug='vote-1')
b.add_title('The Armadillo Bill')
b.add_companion('SB200')


bill_with_multiple_types = Bill('S1', 'upper', 'SJR1',
                                'Division of State - Consitutional Amendment',
                                type=['joint resolution',
                                      'constitutional amendment'])
