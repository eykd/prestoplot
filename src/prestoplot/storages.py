import pathlib
from copy import deepcopy

import msgpack
import yaml


class ModuleNotFoundError(Exception):
    pass


class FileStorage:
    def __init__(self, path):
        self.path = pathlib.Path(path)

    def list_modules(self):
        return sorted(fn.stem for fn in self.path.glob("*.yaml"))

    def resolve_module(self, name):
        try:
            with open(self.path / f"{name}.yaml") as fi:
                return yaml.safe_load(fi)
        except FileNotFoundError:
            raise ModuleNotFoundError(name)


class CompilingFileStorage(FileStorage):
    def clean(self):
        for fn in self.path.glob("*.mp"):
            fn.remove()

    def recompile_modules(self):
        self.clean()
        for fn in self.path.glob("*.yaml"):
            self.resolve_module(fn.stem)

    def resolve_module(self, name):
        compiled_fn = self.path / f"{name}.mp"
        try:
            with open(compiled_fn, "rb") as fi:
                return msgpack.load(fi, raw=False)
        except (FileNotFoundError, TypeError, ValueError, msgpack.ExtraData):
            mod = super().resolve_module(name)
            with open(compiled_fn, "wb") as fo:
                msgpack.dump(mod, fo)
            return mod


class CachedFileStorage(FileStorage):
    _modules = {}

    def resolve_module(self, name):
        try:
            return deepcopy(self._modules[name])
        except KeyError:
            mod = super().resolve_module(name)
            self._modules[name] = mod
            return self.resolve_module(name)


class CompilingCachedFileStorage(CompilingFileStorage):
    _modules = {}

    def resolve_module(self, name):
        try:
            return msgpack.loads(self._modules[name], raw=False)
        except KeyError:
            mod = super().resolve_module(name)
            self._modules[name] = msgpack.dumps(mod)
            return self.resolve_module(name)
