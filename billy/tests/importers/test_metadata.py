from billy.core import db
from billy.importers.metadata import import_metadata, PRESERVED_FIELDS

from nose.tools import with_setup


def drop_metadata():
    db.metadata.drop()


@with_setup(drop_metadata)
def test_import_metadata():
    import_metadata("ex")
    metadata = db.metadata.find_one({"_id": "ex"})
    assert metadata
    assert metadata['_type'] == 'metadata'

    # add some fields
    for f in PRESERVED_FIELDS:
        metadata[f] = 'preserved'
    metadata['junk'] = 'goes away'
    db.metadata.save(metadata, safe=True)

    import_metadata("ex")
    metadata = db.metadata.find_one({"_id": "ex"})
    for f in PRESERVED_FIELDS:
        assert f in metadata
    assert 'junk' not in metadata
