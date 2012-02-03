
import decimal
import datetime
from billy.models import *
from bson import ObjectId

type2field =  {
    bool: 'BooleanField',
    float: 'FloatField',
    int: 'IntField',
    list: 'ListField',
    dict: 'DictField',
    unicode: 'StringField',
    decimal.Decimal: 'DecimalField',
    ObjectId: 'ObjectIdField',
    datetime.datetime: 'DateTimeField',
    }

def convert(document):
	res = []
	for k in sorted(document, key=len):
		if document[k] is not None:
			res.append((k, type2field[type(document[k])]))
	
	line = '%s = %s()'
	return '    ' +  '\n    '.join(line % tpl for tpl in res)

if __name__ == "__main__":
	import pdb
	from billy import db
	doc = db.bills.find_one({'votes.0._type': 'vote'})['votes'][0]['yes_votes'][0]
	print convert(doc)
	pdb.set_trace()