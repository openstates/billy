from billy.importers.utils import prepare_obj


def import_transcriptions(abbr, data_dir, import_actions=False):
    data_dir = os.path.join(data_dir, abbr)
    pattern = os.path.join(data_dir, 'transcriptions', '*.json')

    for path in glob.iglob(pattern):
        with open(path) as f:
            data = prepare_obj(json.load(f))

    raise NotImplemented
