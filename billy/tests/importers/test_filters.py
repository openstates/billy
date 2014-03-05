from billy.importers.filters import (phone_filter, email_filter,
                                     single_space_filter)


def test_phone_filter():
    number = "555-606-0842"
    numbers = [
        "(555)-606-0842",
        "(555) 606-0842",
        "(555) 606 0842",
        "555.606.0842",
        "555 606.0842",
        "555 606 0842",
        "555-606-0842"
    ]
    for num in numbers:
        assert phone_filter(num) == number


def test_phone_filter_country():
    number = "1-555-606-0842"
    numbers = [
        "+1-(555)-606-0842",
        "+1 (555) 606-0842"
    ]
    for num in numbers:
        assert phone_filter(num) == number


def test_barebones_filter():
    number = "606-0842"
    numbers = [
        "606-0842",
        "606.0842",
        "606 0842"
    ]
    for num in numbers:
        assert phone_filter(num) == number


def test_garbage():
    numbers = [
        "this krufty string.  is a test",
        "abc abc abcd",
        "1-5fo-2cds",
        "1-800-foo-paul"
    ]
    for number in numbers:
        assert number == phone_filter(number)


def test_extention():
    number = "555-606-0842 x505"
    numbers = [
        "555-606-0842, x505",
        "555-606-0842 x505",
        "555-606-0842 Ext. 505",
        "555-606-0842 Ext. 505",
        "555-606-0842 Extension 505"
    ]
    for n in numbers:
        num = phone_filter(n)
        assert number == num


def test_email_basics():
    email = "foo@example.com"
    emails = [
        "foo@example.com",
        "mailto:foo@example.com",
        "mailto:foo@example.com?foobar=baz",
        "<foo@example.com>",
        '"John Q. Public" <foo@example.com>'
    ]
    for e in emails:
        assert email_filter(e) == email


def test_invalid_emails():
    emails = [
        "foo@example.com>",
        "<foo@example.com",
        "Contact Me!",
        ""
    ]
    for e in emails:
        assert email_filter(e) == e


def test_single_space_filter():
    line = "Hello, this is a test"
    lines = [
        "  Hello,    this  is     a    test",
        "Hello,      this is   a    test   "
    ]
    for l in lines:
        assert line == single_space_filter(l)


def test_strip_filter():
    line = "Hello, this is a test"
    lines = [
        "Hello, this is a test ",
        " Hello, this is a test ",
        " Hello, this is a test",
        "Hello, this is a test"
    ]
    for l in lines:
        assert line == single_space_filter(l)
