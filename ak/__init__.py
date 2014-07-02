from openstates.jurisdiction import make_jurisdiction

Alaska = make_jurisdiction('ak')

Alaska.posts = (
    [Post(label=str(n), role='Representative', chamber='lower') for n in range(1, 41)] +
    [Post(label=chr(n), role='Senator', chamber='upper') for n in range(65, 85)]
)
Alaska.url = 'http://alaska.gov'
