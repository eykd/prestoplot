"""Storage backends for grammar files."""

from __future__ import annotations

import pathlib
from copy import deepcopy
from typing import Any, ClassVar

import msgpack
import yaml


class GrammarModuleNotFoundError(Exception):
    """Raised when a requested grammar module cannot be found."""


class FileStorage:
    """Simple file-based storage for YAML grammar files."""

    def __init__(self, path: str | pathlib.Path) -> None:
        """Initialize storage with a base path.

        Args:
            path: Directory containing grammar files

        """
        self.path = pathlib.Path(path)

    def list_modules(self) -> list[str]:
        """List available grammar modules by filename stem.

        Returns:
            Sorted list of module names (without .yaml extension)

        """
        return sorted(fn.stem for fn in self.path.glob('*.yaml'))

    def resolve_module(self, name: str) -> dict[str, Any]:
        """Load and parse a grammar module from YAML file.

        Args:
            name: Module name (without .yaml extension)

        Returns:
            Parsed YAML data as Python dict

        Raises:
            GrammarModuleNotFoundError: If the module file doesn't exist

        """
        try:
            with pathlib.Path.open(self.path / f'{name}.yaml') as fi:
                return yaml.safe_load(fi)
        except FileNotFoundError:
            raise GrammarModuleNotFoundError(name) from None


class CompilingFileStorage(FileStorage):
    """File storage with MessagePack compilation caching.

    Compiles YAML files to MessagePack (.mp) format for faster loading.
    """

    def clean(self) -> None:
        """Remove all compiled MessagePack files."""
        for fn in self.path.glob('*.mp'):
            fn.unlink()

    def recompile_modules(self) -> None:
        """Recompile all YAML modules to MessagePack format."""
        self.clean()
        for fn in self.path.glob('*.yaml'):
            self.resolve_module(fn.stem)

    def resolve_module(self, name: str) -> dict[str, Any]:
        """Load module from compiled cache or compile from YAML.

        Args:
            name: Module name (without extension)

        Returns:
            Parsed module data

        """
        compiled_fn = self.path / f'{name}.mp'
        try:
            with pathlib.Path.open(compiled_fn, 'rb') as fi:
                return msgpack.load(fi, raw=False)
        except (FileNotFoundError, TypeError, ValueError, msgpack.ExtraData):
            mod = super().resolve_module(name)
            with pathlib.Path.open(compiled_fn, 'wb') as fo:
                msgpack.dump(mod, fo)
            return mod


class CachedFileStorage(FileStorage):
    """File storage with in-memory caching.

    Caches parsed modules in memory to avoid repeated file I/O.
    """

    _modules: ClassVar[dict[str, dict[str, Any]]] = {}

    def resolve_module(self, name: str) -> dict[str, Any]:
        """Load module from memory cache or file.

        Args:
            name: Module name (without extension)

        Returns:
            Deep copy of cached module data

        """
        try:
            return deepcopy(self._modules[name])
        except KeyError:
            mod = super().resolve_module(name)
            self._modules[name] = mod
            return self.resolve_module(name)


class CompilingCachedFileStorage(CompilingFileStorage):
    """File storage with both compilation and memory caching.

    Combines MessagePack compilation with in-memory caching for
    maximum performance.
    """

    _modules: ClassVar[dict[str, bytes]] = {}

    def resolve_module(self, name: str) -> dict[str, Any]:
        """Load module from memory cache, compiled cache, or source file.

        Args:
            name: Module name (without extension)

        Returns:
            Module data loaded from most efficient available source

        """
        try:
            return msgpack.loads(self._modules[name], raw=False)
        except (KeyError, TypeError, ValueError, msgpack.ExtraData):
            mod = super().resolve_module(name)
            self._modules[name] = msgpack.dumps(mod)
            return self.resolve_module(name)
