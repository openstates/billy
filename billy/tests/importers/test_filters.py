from billy.importers.filters import phone_filter

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
