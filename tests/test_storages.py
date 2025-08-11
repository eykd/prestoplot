"""Comprehensive tests for prestoplot.storages module."""

import pathlib
import tempfile
from typing import Any

import msgpack
import pytest
import yaml

from prestoplot.storages import (
    CachedFileStorage,
    CompilingCachedFileStorage,
    CompilingFileStorage,
    FileStorage,
    GrammarModuleNotFoundError,
)


class TestGrammarModuleNotFoundError:
    """Test the custom exception class."""

    def test_exception_creation(self) -> None:
        """Test exception can be created and raised."""
        exc = GrammarModuleNotFoundError('test_module')
        assert str(exc) == 'test_module'

    def test_exception_inheritance(self) -> None:
        """Test exception inherits from Exception."""
        exc = GrammarModuleNotFoundError('test')
        assert isinstance(exc, Exception)


class TestFileStorage:
    """Test the FileStorage class."""

    @pytest.fixture
    def temp_dir(self) -> pathlib.Path:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_path:
            yield pathlib.Path(temp_path)

    @pytest.fixture
    def sample_yaml_content(self) -> dict[str, Any]:
        """Sample YAML content for testing."""
        return {
            'Begin': ['Hello world'],
            'greeting': ['Hi', 'Hello', 'Hey'],
        }

    @pytest.fixture
    def storage_with_data(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> FileStorage:
        """Create FileStorage with test data."""
        # Create test YAML files
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        another_file = temp_dir / 'another.yaml'
        with another_file.open('w') as f:
            yaml.dump({'Begin': ['Another test']}, f)

        return FileStorage(temp_dir)

    def test_init_with_string_path(self, temp_dir: pathlib.Path) -> None:
        """Test initialization with string path."""
        storage = FileStorage(str(temp_dir))
        assert storage.path == temp_dir
        assert isinstance(storage.path, pathlib.Path)

    def test_init_with_pathlib_path(self, temp_dir: pathlib.Path) -> None:
        """Test initialization with pathlib.Path."""
        storage = FileStorage(temp_dir)
        assert storage.path == temp_dir
        assert isinstance(storage.path, pathlib.Path)

    def test_list_modules_empty_directory(self, temp_dir: pathlib.Path) -> None:
        """Test listing modules in empty directory."""
        storage = FileStorage(temp_dir)
        result = storage.list_modules()
        assert result == []

    def test_list_modules_with_yaml_files(self, storage_with_data: FileStorage) -> None:
        """Test listing modules with YAML files present."""
        result = storage_with_data.list_modules()
        assert result == ['another', 'test']  # Should be sorted

    def test_list_modules_ignores_non_yaml_files(self, temp_dir: pathlib.Path) -> None:
        """Test that list_modules only includes .yaml files."""
        # Create various file types
        (temp_dir / 'test.yaml').touch()
        (temp_dir / 'readme.txt').touch()
        (temp_dir / 'config.json').touch()
        (temp_dir / 'script.py').touch()

        storage = FileStorage(temp_dir)
        result = storage.list_modules()
        assert result == ['test']

    def test_resolve_module_success(
        self, storage_with_data: FileStorage, sample_yaml_content: dict[str, Any]
    ) -> None:
        """Test successful module resolution."""
        result = storage_with_data.resolve_module('test')
        assert result == sample_yaml_content

    def test_resolve_module_not_found(self, storage_with_data: FileStorage) -> None:
        """Test module resolution with non-existent file."""
        with pytest.raises(GrammarModuleNotFoundError) as exc_info:
            storage_with_data.resolve_module('nonexistent')

        assert str(exc_info.value) == 'nonexistent'
        assert (
            exc_info.value.__cause__ is None
        )  # Should suppress original FileNotFoundError

    def test_resolve_module_with_invalid_yaml(self, temp_dir: pathlib.Path) -> None:
        """Test module resolution with invalid YAML content."""
        invalid_file = temp_dir / 'invalid.yaml'
        with invalid_file.open('w') as f:
            f.write('invalid: yaml: content: [')  # Invalid YAML

        storage = FileStorage(temp_dir)
        with pytest.raises(yaml.YAMLError):
            storage.resolve_module('invalid')

    def test_resolve_module_with_empty_file(self, temp_dir: pathlib.Path) -> None:
        """Test module resolution with empty YAML file."""
        empty_file = temp_dir / 'empty.yaml'
        empty_file.touch()

        storage = FileStorage(temp_dir)
        result = storage.resolve_module('empty')
        assert result is None  # Empty YAML file loads as None

    def test_resolve_module_with_complex_yaml(self, temp_dir: pathlib.Path) -> None:
        """Test module resolution with complex YAML structures."""
        complex_data = {
            'Begin': ['Start here'],
            'nested': {'deep': {'structure': ['works']}},
            'list': [1, 2, 3],
            'mixed': {'string': 'value', 'number': 42, 'boolean': True, 'null': None},
        }

        complex_file = temp_dir / 'complex.yaml'
        with complex_file.open('w') as f:
            yaml.dump(complex_data, f)

        storage = FileStorage(temp_dir)
        result = storage.resolve_module('complex')
        assert result == complex_data


class TestCompilingFileStorage:
    """Test the CompilingFileStorage class."""

    @pytest.fixture
    def temp_dir(self) -> pathlib.Path:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_path:
            yield pathlib.Path(temp_path)

    @pytest.fixture
    def sample_yaml_content(self) -> dict[str, Any]:
        """Sample YAML content for testing."""
        return {
            'Begin': ['Compiled hello world'],
            'greeting': ['Hi', 'Hello', 'Hey'],
        }

    @pytest.fixture
    def storage_with_data(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> CompilingFileStorage:
        """Create CompilingFileStorage with test data."""
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        return CompilingFileStorage(temp_dir)

    def test_inherits_from_file_storage(self) -> None:
        """Test that CompilingFileStorage inherits from FileStorage."""
        assert issubclass(CompilingFileStorage, FileStorage)

    def test_clean_removes_compiled_files(self, temp_dir: pathlib.Path) -> None:
        """Test that clean() removes all .mp files."""
        # Create some .mp files and other files
        (temp_dir / 'test1.mp').touch()
        (temp_dir / 'test2.mp').touch()
        (temp_dir / 'test.yaml').touch()
        (temp_dir / 'readme.txt').touch()

        storage = CompilingFileStorage(temp_dir)
        storage.clean()

        # Only .mp files should be removed
        assert not (temp_dir / 'test1.mp').exists()
        assert not (temp_dir / 'test2.mp').exists()
        assert (temp_dir / 'test.yaml').exists()
        assert (temp_dir / 'readme.txt').exists()

    def test_clean_with_no_compiled_files(self, temp_dir: pathlib.Path) -> None:
        """Test clean() when no .mp files exist."""
        storage = CompilingFileStorage(temp_dir)
        # Should not raise any errors
        storage.clean()

    def test_recompile_modules_cleans_and_recompiles(
        self, storage_with_data: CompilingFileStorage
    ) -> None:
        """Test that recompile_modules() cleans and recompiles all modules."""
        # First, create a compiled file manually
        mp_file = storage_with_data.path / 'test.mp'
        with mp_file.open('wb') as f:
            msgpack.dump({'old': 'data'}, f)

        assert mp_file.exists()

        # Recompile should clean and recreate
        storage_with_data.recompile_modules()

        # The .mp file should exist and contain correct data
        assert mp_file.exists()
        with mp_file.open('rb') as f:
            compiled_data = msgpack.load(f, raw=False)

        # Should match the YAML content, not the old data
        assert compiled_data['Begin'] == ['Compiled hello world']
        assert 'old' not in compiled_data

    def test_resolve_module_creates_compiled_file(
        self,
        storage_with_data: CompilingFileStorage,
        sample_yaml_content: dict[str, Any],
    ) -> None:
        """Test that resolve_module creates .mp file on first access."""
        mp_file = storage_with_data.path / 'test.mp'
        assert not mp_file.exists()

        result = storage_with_data.resolve_module('test')

        # Should create compiled file
        assert mp_file.exists()
        assert result == sample_yaml_content

        # Verify compiled file content
        with mp_file.open('rb') as f:
            compiled_data = msgpack.load(f, raw=False)
        assert compiled_data == sample_yaml_content

    def test_resolve_module_uses_compiled_file_when_available(
        self, storage_with_data: CompilingFileStorage
    ) -> None:
        """Test that resolve_module uses existing .mp file."""
        # Create a compiled file with different data than YAML
        compiled_data = {'compiled': ['data']}
        mp_file = storage_with_data.path / 'test.mp'
        with mp_file.open('wb') as f:
            msgpack.dump(compiled_data, f)

        result = storage_with_data.resolve_module('test')

        # Should return compiled data, not YAML data
        assert result == compiled_data

    def test_resolve_module_handles_corrupted_compiled_file(
        self,
        storage_with_data: CompilingFileStorage,
        sample_yaml_content: dict[str, Any],
    ) -> None:
        """Test handling of corrupted .mp files."""
        # Create corrupted compiled file
        mp_file = storage_with_data.path / 'test.mp'
        with mp_file.open('wb') as f:
            f.write(b'corrupted data')

        result = storage_with_data.resolve_module('test')

        # Should fallback to YAML and recreate .mp file
        assert result == sample_yaml_content

        # Verify new .mp file is valid
        with mp_file.open('rb') as f:
            compiled_data = msgpack.load(f, raw=False)
        assert compiled_data == sample_yaml_content

    def test_resolve_module_handles_msgpack_exceptions(
        self,
        storage_with_data: CompilingFileStorage,
        sample_yaml_content: dict[str, Any],
    ) -> None:
        """Test handling of various msgpack exceptions."""
        mp_file = storage_with_data.path / 'test.mp'

        # Test with each type of exception that's caught
        for bad_data in [
            b'',  # Empty file (ValueError)
            b'invalid',  # Invalid msgpack (msgpack.exceptions.ExtraData)
        ]:
            with mp_file.open('wb') as f:
                f.write(bad_data)

            result = storage_with_data.resolve_module('test')
            assert result == sample_yaml_content

    def test_resolve_module_nonexistent_raises_error(
        self, storage_with_data: CompilingFileStorage
    ) -> None:
        """Test that non-existent modules raise GrammarModuleNotFoundError."""
        with pytest.raises(GrammarModuleNotFoundError):
            storage_with_data.resolve_module('nonexistent')


class TestCachedFileStorage:
    """Test the CachedFileStorage class."""

    @pytest.fixture
    def temp_dir(self) -> pathlib.Path:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_path:
            yield pathlib.Path(temp_path)

    @pytest.fixture
    def sample_yaml_content(self) -> dict[str, Any]:
        """Sample YAML content for testing."""
        return {
            'Begin': ['Cached hello world'],
            'mutable_data': {'count': 1},
        }

    @pytest.fixture
    def storage_with_data(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> CachedFileStorage:
        """Create CachedFileStorage with test data."""
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        # Clear class cache before each test
        CachedFileStorage._modules.clear()  # noqa: SLF001
        return CachedFileStorage(temp_dir)

    def test_inherits_from_file_storage(self) -> None:
        """Test that CachedFileStorage inherits from FileStorage."""
        assert issubclass(CachedFileStorage, FileStorage)

    def test_resolve_module_caches_result(
        self, storage_with_data: CachedFileStorage, sample_yaml_content: dict[str, Any]
    ) -> None:
        """Test that modules are cached in memory."""
        # First call should read from file
        result1 = storage_with_data.resolve_module('test')
        assert result1 == sample_yaml_content

        # Module should now be cached
        assert 'test' in CachedFileStorage._modules  # noqa: SLF001
        assert CachedFileStorage._modules['test'] == sample_yaml_content  # noqa: SLF001

        # Second call should use cache
        result2 = storage_with_data.resolve_module('test')
        assert result2 == sample_yaml_content

    def test_resolve_module_returns_deep_copy(
        self, storage_with_data: CachedFileStorage
    ) -> None:
        """Test that cached modules return deep copies."""
        result1 = storage_with_data.resolve_module('test')
        result2 = storage_with_data.resolve_module('test')

        # Should be equal but not the same object
        assert result1 == result2
        assert result1 is not result2

        # Modifying one should not affect the other
        result1['mutable_data']['count'] = 999
        assert result2['mutable_data']['count'] == 1

    def test_resolve_module_cache_persists_across_instances(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> None:
        """Test that cache is shared across instances (class variable)."""
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        # Clear cache first
        CachedFileStorage._modules.clear()  # noqa: SLF001

        storage1 = CachedFileStorage(temp_dir)
        result1 = storage1.resolve_module('test')

        # Create new instance
        storage2 = CachedFileStorage(temp_dir)
        result2 = storage2.resolve_module('test')

        # Both should return same data (but different objects due to deepcopy)
        assert result1 == result2
        assert 'test' in CachedFileStorage._modules  # noqa: SLF001

    def test_resolve_module_nonexistent_raises_error(
        self, storage_with_data: CachedFileStorage
    ) -> None:
        """Test that non-existent modules raise GrammarModuleNotFoundError."""
        with pytest.raises(GrammarModuleNotFoundError):
            storage_with_data.resolve_module('nonexistent')


class TestCompilingCachedFileStorage:
    """Test the CompilingCachedFileStorage class."""

    @pytest.fixture
    def temp_dir(self) -> pathlib.Path:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_path:
            yield pathlib.Path(temp_path)

    @pytest.fixture
    def sample_yaml_content(self) -> dict[str, Any]:
        """Sample YAML content for testing."""
        return {
            'Begin': ['Compiling cached hello world'],
            'data': {'value': 42},
        }

    @pytest.fixture
    def storage_with_data(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> CompilingCachedFileStorage:
        """Create CompilingCachedFileStorage with test data."""
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        # Clear class cache before each test
        CompilingCachedFileStorage._modules.clear()  # noqa: SLF001
        return CompilingCachedFileStorage(temp_dir)

    def test_inherits_from_compiling_file_storage(self) -> None:
        """Test that CompilingCachedFileStorage inherits from CompilingFileStorage."""
        assert issubclass(CompilingCachedFileStorage, CompilingFileStorage)

    def test_resolve_module_caches_msgpack_bytes(
        self,
        storage_with_data: CompilingCachedFileStorage,
        sample_yaml_content: dict[str, Any],
    ) -> None:
        """Test that modules are cached as msgpack bytes."""
        result = storage_with_data.resolve_module('test')
        assert result == sample_yaml_content

        # Should cache as bytes
        assert 'test' in CompilingCachedFileStorage._modules  # noqa: SLF001
        cached_bytes = CompilingCachedFileStorage._modules['test']  # noqa: SLF001
        assert isinstance(cached_bytes, bytes)

        # Cached bytes should deserialize to original data
        deserialized = msgpack.loads(cached_bytes, raw=False)
        assert deserialized == sample_yaml_content

    def test_resolve_module_uses_memory_cache_first(
        self,
        storage_with_data: CompilingCachedFileStorage,
        sample_yaml_content: dict[str, Any],
    ) -> None:
        """Test that memory cache is used before file cache."""
        # First call loads and caches
        result1 = storage_with_data.resolve_module('test')
        assert result1 == sample_yaml_content

        # Modify the disk cache to different data
        mp_file = storage_with_data.path / 'test.mp'
        different_data = {'different': ['data']}
        with mp_file.open('wb') as f:
            msgpack.dump(different_data, f)

        # Second call should use memory cache, not disk cache
        result2 = storage_with_data.resolve_module('test')
        assert result2 == sample_yaml_content  # Original data, not different_data

    def test_resolve_module_fallback_chain(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> None:
        """Test the complete fallback chain: memory -> disk -> yaml."""
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        CompilingCachedFileStorage._modules.clear()  # noqa: SLF001
        storage = CompilingCachedFileStorage(temp_dir)

        # First call: yaml -> disk -> memory
        result1 = storage.resolve_module('test')
        assert result1 == sample_yaml_content

        # Should have created both disk and memory cache
        mp_file = temp_dir / 'test.mp'
        assert mp_file.exists()
        assert 'test' in CompilingCachedFileStorage._modules  # noqa: SLF001

        # Clear memory cache only
        CompilingCachedFileStorage._modules.clear()  # noqa: SLF001

        # Second call: disk -> memory
        result2 = storage.resolve_module('test')
        assert result2 == sample_yaml_content
        assert 'test' in CompilingCachedFileStorage._modules  # noqa: SLF001

    def test_resolve_module_handles_corrupted_memory_cache(
        self,
        storage_with_data: CompilingCachedFileStorage,
        sample_yaml_content: dict[str, Any],
    ) -> None:
        """Test handling of corrupted memory cache."""
        # Manually corrupt memory cache
        CompilingCachedFileStorage._modules['test'] = b'corrupted'  # noqa: SLF001

        # Should fallback to parent resolve_module
        result = storage_with_data.resolve_module('test')
        assert result == sample_yaml_content

    def test_resolve_module_memory_cache_persists_across_instances(
        self, temp_dir: pathlib.Path, sample_yaml_content: dict[str, Any]
    ) -> None:
        """Test that memory cache persists across instances."""
        test_file = temp_dir / 'test.yaml'
        with test_file.open('w') as f:
            yaml.dump(sample_yaml_content, f)

        CompilingCachedFileStorage._modules.clear()  # noqa: SLF001

        storage1 = CompilingCachedFileStorage(temp_dir)
        result1 = storage1.resolve_module('test')

        storage2 = CompilingCachedFileStorage(temp_dir)
        result2 = storage2.resolve_module('test')

        assert result1 == result2 == sample_yaml_content
        assert len(CompilingCachedFileStorage._modules) == 1  # noqa: SLF001

    def test_resolve_module_nonexistent_raises_error(
        self, storage_with_data: CompilingCachedFileStorage
    ) -> None:
        """Test that non-existent modules raise GrammarModuleNotFoundError."""
        with pytest.raises(GrammarModuleNotFoundError):
            storage_with_data.resolve_module('nonexistent')


class TestStorageIntegration:
    """Integration tests comparing different storage implementations."""

    @pytest.fixture
    def temp_dir(self) -> pathlib.Path:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_path:
            yield pathlib.Path(temp_path)

    @pytest.fixture
    def sample_data(self, temp_dir: pathlib.Path) -> dict[str, Any]:
        """Create sample test data."""
        data = {
            'Begin': ['Integration test'],
            'complex': {
                'nested': {'deep': ['structure']},
                'list': [1, 2, 3],
                'mixed': True,
            },
        }

        test_file = temp_dir / 'integration.yaml'
        with test_file.open('w') as f:
            yaml.dump(data, f)

        return data

    @pytest.mark.parametrize(
        'storage_class',
        [
            FileStorage,
            CachedFileStorage,
            CompilingFileStorage,
            CompilingCachedFileStorage,
        ],
    )
    def test_all_storages_return_same_data(
        self, temp_dir: pathlib.Path, sample_data: dict[str, Any], storage_class: type
    ) -> None:
        """Test that all storage implementations return identical data."""
        # Clear any class caches
        if hasattr(storage_class, '_modules'):
            storage_class._modules.clear()  # noqa: SLF001

        storage = storage_class(temp_dir)
        result = storage.resolve_module('integration')
        assert result == sample_data

    def test_performance_order(
        self, temp_dir: pathlib.Path, sample_data: dict[str, Any]
    ) -> None:
        """Test that cached versions avoid file I/O on subsequent calls."""
        # Clear caches
        CachedFileStorage._modules.clear()  # noqa: SLF001
        CompilingCachedFileStorage._modules.clear()  # noqa: SLF001

        storages = [
            FileStorage(temp_dir),
            CachedFileStorage(temp_dir),
            CompilingFileStorage(temp_dir),
            CompilingCachedFileStorage(temp_dir),
        ]

        # All should return same data
        results = [s.resolve_module('integration') for s in storages]
        assert all(r == sample_data for r in results)

        # Cached versions should have populated their caches
        assert 'integration' in CachedFileStorage._modules  # noqa: SLF001
        assert 'integration' in CompilingCachedFileStorage._modules  # noqa: SLF001
        assert (
            temp_dir / 'integration.mp'
        ).exists()  # Compiling versions create .mp files
