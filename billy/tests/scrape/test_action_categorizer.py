from nose.tools import eq_

from billy.scrape.actions import Rule, BaseCategorizer


test_actions = (
    'Referred to Committee on Bats; also referred to Fake Committee',
    'Goat action: walk around, eat grass.',
    )

rules = (

    # For testing key clobbering.
    Rule(r'Referred to (?P<committees>Committee on .+?);'),
    Rule(r'also referred to (?P<committees>.+)'),

    # For testing stop.
    Rule(r'walk', ['action:walk'], stop=True),
    Rule(r'eat', ['action:eatgrass']),

    # Flexible whitespace.
    Rule(r'Moo moo', ['action:moo']),

    # Test attrs
    Rule(r'Test attrs', species='goat'),

    # Test multiple types.
    Rule(r'1', ['1', '2']),
    Rule(r'3', ['3']),
    )


class Categorizer(BaseCategorizer):
    rules = rules

categorizer = Categorizer()


def test_keys_not_clobbering():
    '''Verify that multiple captured groups with the
    same name are ending up in a list instead of
    overwriting each other.
    '''
    action = test_actions[0]
    attrs = categorizer.categorize(action)

    expected = set(['Committee on Bats', 'Fake Committee'])
    eq_(set(attrs['committees']), expected)


def test_stop_feature():
    '''Verify that stop=True prevents further testing
    of subsequent rules.
    '''
    action = test_actions[1]
    attrs = categorizer.categorize(action)

    expected = ['action:walk']
    eq_(attrs['type'], expected)


def test_whitespace_feature():
    '''Verify that flexible_whitespace=True correctly liberalizes
    whitespace matching.
    '''
    action = 'Moo   moo'
    attrs = categorizer.categorize(action)

    expected = ['action:moo']
    eq_(attrs['type'], expected)


def test_rule_attrs_feature():
    '''Verify that rule attrs are being added into the
    categorize return value.
    '''
    action = 'Test attrs'
    attrs = categorizer.categorize(action)

    eq_(attrs['species'], 'goat')


def test_types_aggregation():
    action = 'Types 1, 2, and 3'
    attrs = categorizer.categorize(action)
    eq_(set(attrs['type']), set(['1', '2', '3']))
