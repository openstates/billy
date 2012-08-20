import re

def _phone_formatter(obj):
    objs = []
    for thing in ["country", "area", "prefix", "line_number"]:
        if thing in obj:
            objs.append(obj[thing])
    return "-".join(objs)


def phone_filter(number, formatter=_phone_formatter):
    breakers = "+-()."
    for b in breakers:
        number = number.replace(b, " ")
    number = re.sub("\s+", " ", number).strip()
    blobs = number.split()
    blobs.reverse()
    order = [
        "line_number",
        "prefix",
        "area",
        "country"
    ]
    obj = {}
    for blob in blobs:
        obj[order[len(obj)]] = blob

    number = formatter(obj)
    return number
