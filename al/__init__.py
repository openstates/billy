from pupa.scrape import Post
from openstates.jurisdiction import make_jurisdiction

Alabama = make_jurisdiction('al')

Alabama.posts = (
    [Post(label=str(n), role='Representative', chamber='lower') for n in range(1, 106)] +
    [Post(label=str(n), role='Senator', chamber='upper') for n in range(1, 36)]
)
Alabama.url = 'http://alabama.gov'
