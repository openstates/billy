import re
from collections import defaultdict


class Filter(object):
    def filter(self, obj):
        pass


def _phone_formatter(obj):
    objs = []
    for thing in ["country", "area", "prefix", "line_number"]:
        if thing in obj:
            objs.append(obj[thing])
    return "-".join(objs)


def phone_filter(original_number, formatter=_phone_formatter):
    number = original_number
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
        if len(obj) >= len(order):
            return original_number

        obj[order[len(obj)]] = blob

    reqs = {
        "prefix": 3,
        "area": 3,
        "line_number": 4
    }

    for req in reqs:
        if req in obj:
            try:
                int(obj[req])
            except ValueError:
                return original_number

            if len(obj[req]) != reqs[req]:
                return original_number

    number = formatter(obj)
    return number


class LegislatorPhoneFilter(Filter):
    def filter(self, obj):
        if "offices" in obj:
            for i in range(0, len(obj['offices'])):
                if "phone" in obj['offices'][i]:
                    obj['offices'][i]['phone'] = \
                            phone_filter(obj['offices'][i]['phone'])
        return obj
