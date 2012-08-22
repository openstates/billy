import re


class Filter(object):
    def filter(self, obj):
        pass


def _phone_formatter(obj, extention):
    objs = []
    for thing in ["country", "area", "prefix", "line_number"]:
        if thing in obj:
            objs.append(obj[thing])
    number = "-".join(objs)
    if extention is not None:
        number += " x%s" % (extention)
    return number


def phone_filter(original_number, formatter=_phone_formatter):
    number = original_number

    extentions = [
        "extension",
        "ext.",
        "x"
    ]
    extention = None

    for x in extentions:
        if x in number.lower():
            number, extention = number.lower().split(x, 1)
            extention = extention.strip()
            break

    breakers = "+-().,"
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

    number = formatter(obj, extention)
    return number


def email_filter(email):
    leaders = [
        "mailto:"
    ]

    for leader in leaders:
        if email.startswith(leader):
            email = email[len(leader):]

    if ">" in email and "<" in email:
        # we likely have a nested email.
        emails = re.findall("\<(.*)\>", email)
        if len(emails) == 1:
            email = emails[0]
    return email


def strip_filter(entry):
    entry = entry.strip()
    return entry


def single_space_filter(entry):
    if not isinstance(entry, basestring):
        return entry

    entry = re.sub("\s+", " ", entry)
    return strip_filter(entry)


class LegislatorPhoneFilter(Filter):
    def filter(self, obj):
        if "offices" in obj:
            for i in range(0, len(obj['offices'])):
                if "phone" in obj['offices'][i]:
                    obj['offices'][i]['phone'] = \
                            phone_filter(obj['offices'][i]['phone'])
        return obj


class LegislatorEmailFilter(Filter):
    def filter(self, obj):
        if "email" in obj:
            obj['email'] = email_filter(obj['email'])
        return obj


class StripFilter(Filter):
    def filter(self, obj):
        if isinstance(obj, basestring):
            return strip_filter(obj)
        elif isinstance(obj, list):
            newl = []
            for x in obj:
                newl.append(self.filter(x))
            return newl
        for x in obj:
            obj[x] = self.filter(obj[x])
        return obj


class BillStringsFilter(Filter):
    def filter(self, obj):
        keys = [
            "title",
            "description",
            "summary"
        ]
        for key in keys:
            if key in obj:
                obj[key] = single_space_filter(obj)
        return obj
