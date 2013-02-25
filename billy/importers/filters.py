import re
import importlib


def apply_filters(filter_array, obj):
    for fltr in filter_array:
        for key in filter_array[fltr]:
            obj = filter_object(fltr, key, obj)
    return obj


def filter_object(filter_path, object_path, obj):
    module, func = filter_path.rsplit(".", 1)
    mod = importlib.import_module(module)
    fltr = getattr(mod, func)
    return run_filter(fltr, object_path, obj)


def run_filter(fltr, object_path, obj):
    if "." in object_path:
        root, new_path = object_path.split(".", 1)
        try:
            obj[root] = run_filter(fltr, new_path, obj[root])
        except KeyError:
            pass
        return obj
    try:
        if isinstance(obj, list):
            ret = []
            for entry in obj:
                ret.append(run_filter(fltr, object_path, entry))
            return ret

        fltr_obj = obj[object_path]
    except KeyError:
        return obj  # Eek, bad object path. Bail.

    if isinstance(fltr_obj, basestring):
        obj[object_path] = fltr(fltr_obj)

    if isinstance(fltr_obj, list):
        ret = []
        for item in fltr_obj:
            ret.append(fltr(item))
        obj[object_path] = ret
    return obj


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

    mailto = "mailto:"
    if email.startswith(mailto):
        email = email[len(mailto):]
        if "?" in email:
            email = email[:email.index("?")]

    if ">" in email and "<" in email:
        # we likely have a nested email.
        emails = re.findall("\<(.*)\>", email)
        if len(emails) == 1:
            email = emails[0]
    return email


def strip_filter(entry):
    if not isinstance(entry, basestring):
        return entry

    entry = entry.strip()
    return entry


def single_space_filter(entry):
    if not isinstance(entry, basestring):
        return entry

    entry = re.sub("\s+", " ", entry)
    return strip_filter(entry)
