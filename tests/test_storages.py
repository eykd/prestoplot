import pathlib
from typing import Final

import pytest
import yaml

from prestoplot import storages

PATH: Final[pathlib.Path] = pathlib.Path(__file__).parent

DATA: Final[pathlib.Path] = PATH / 'data'


@pytest.fixture(
    params=[
        storages.FileStorage,
        storages.CachedFileStorage,
        storages.CompilingFileStorage,
    ]
)
def fs(
    request: pytest.FixtureRequest,
) -> storages.FileStorage | storages.CachedFileStorage | storages.CompilingFileStorage:
    return request.param(str(DATA))


def test_file_storage_should_store_path(
    fs: storages.FileStorage
    | storages.CachedFileStorage
    | storages.CompilingFileStorage,
) -> None:
    assert isinstance(fs.path, pathlib.Path)
    assert fs.path == DATA


def test_file_storage_should_list_modules(
    fs: storages.FileStorage
    | storages.CachedFileStorage
    | storages.CompilingFileStorage,
) -> None:
    result = fs.list_modules()
    expected = ['characters', 'characters_jinja', 'names', 'test_ratchet']
    assert result == expected


def test_file_storage_resolve_module_should_resolve_valid_names(
    fs: storages.FileStorage
    | storages.CachedFileStorage
    | storages.CompilingFileStorage,
) -> None:
    result = fs.resolve_module('names')
    with (DATA / 'names.yaml').open() as fi:
        expected = yaml.safe_load(fi)
    assert result == expected


def test_file_storage_resolve_module_should_not_resolve_invalid_names(
    fs: storages.FileStorage
    | storages.CachedFileStorage
    | storages.CompilingFileStorage,
) -> None:
    with pytest.raises(storages.ModuleNotFoundError):
        fs.resolve_module('foo')
