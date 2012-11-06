from billy.importers.utils import prepare_obj


def import_events(abbr, data_dir, import_actions=False):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'events', '*.json')

    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))

    raise NotImplemented
