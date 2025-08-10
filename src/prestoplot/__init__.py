try:
    from . import _version

    __version__ = _version.version
except (ImportError, AttributeError):
    import importlib.metadata

    try:
        __version__ = importlib.metadata.version(__name__)
    except importlib.metadata.PackageNotFoundError:
        __version__ = "0.0.0"
