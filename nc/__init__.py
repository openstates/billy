from pupa.scrape import Post
from openstates.jurisdiction import make_jurisdiction

NC = make_jurisdiction('nc')
NC.url = 'http://www.ncgov.com/'
NC.posts = (
    [Post(label=str(n), role='Representative', chamber='lower') for n in range(1, 121)] +
    [Post(label=str(n), role='Senator', chamber='upper') for n in range(1, 51)]
)
