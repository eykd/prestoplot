import pathlib
from copy import deepcopy

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


class CachedFileStorage(FileStorage):
    _modules = {}

    def resolve_module(self, name):
        try:
            return deepcopy(self._modules[name])
        except KeyError:
            mod = super().resolve_module(name)
            self._modules[name] = mod
            return self.resolve_module(name)
