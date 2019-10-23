import pathlib

import pytest
import yaml
from prestoplot import storages

PATH = pathlib.Path(__file__).parent

DATA = PATH / "data"


@pytest.fixture
def fs():
    return storages.FileStorage(str(DATA))


def test_file_storage_should_store_path(fs):
    assert isinstance(fs.path, pathlib.Path)
    assert fs.path == DATA


def test_file_storage_should_list_modules(fs):
    result = fs.list_modules()
    assert result == ["characters", "characters_jinja", "names"]


def test_file_storage_resolve_module_should_resolve_valid_names(fs):
    result = fs.resolve_module("names")
    with open(DATA / "names.yaml") as fi:
        expected = yaml.load(fi)
    assert result == expected


def test_file_storage_resolve_module_should_not_resolve_invalid_names(fs):
    with pytest.raises(storages.ModuleNotFoundError):
        fs.resolve_module("foo")
