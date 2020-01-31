from pupa.scrape import Post
from openstatesapi.jurisdiction import make_jurisdiction

Texas = make_jurisdiction('tx')
Texas.url = 'http://texas.gov'
