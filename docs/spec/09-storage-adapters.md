# 09 — Storage Adapters

This document specifies the four storage adapter implementations provided by the
reference implementation, plus the normative contract that all storage adapters must
satisfy. Storage adapters are driven adapters in the hexagonal architecture: they sit
on the right side of the application core and are called by `parse_grammar_file` to
resolve grammar module definitions.

This document supplements the port definition in `02-ports-and-adapters.md`, providing
full behavioral contracts, implementation notes, and conformance requirements for each
adapter. Sections marked **[Normative]** state requirements that all conforming
implementations must satisfy. Sections marked **[Informative]** describe optional
behaviors or implementation guidance.

---

## StoragePort Contract [Normative]

Every storage adapter must implement the following two operations:

```
resolve_module(name: string) → map[string, any]
list_modules()               → list[string]
```

### `resolve_module(name)` [Normative]

| Aspect | Contract |
|--------|----------|
| **Input** | Module name as a string, without any file extension. |
| **Output** | A **mutable, independent copy** of the raw module data as a key-value map. |
| **Mutable copy requirement** | The caller (grammar parser) mutates the returned map: it pops the `"include"` and `"render"` keys before processing rule entries. The storage adapter must ensure that each call returns an independent copy; a subsequent call with the same name must return the same original data unaffected by mutations to any prior return value. |
| **Not found** | Raises `ModuleNotFoundError(name)` (or the implementation's equivalent named exception) when no module with that name exists in the backing store. |
| **Empty module** | Returns `null` / `None` when the module file exists but contains no data (e.g., an empty YAML file). The grammar parser treats a `null` module as an empty rule set and does not iterate it. |
| **Invalid content** | Propagates the YAML parser's own error unchanged. Does not swallow or transform parse errors. |

The returned map has the shape of a parsed YAML document. At the top level it is a
`map[string, any]` where values may be:

- `string` — a TextRule template.
- `list[any]` — a ListRule (optionally beginning with a single-key `{mode: ...}` map).
- `map[string, any]` — a StructRule (Databag).
- `bool` — a boolean value passed through to the Context as-is.

### `list_modules()` [Normative]

| Aspect | Contract |
|--------|----------|
| **Output** | An alphabetically sorted list of module name strings (without file extensions). |
| **Empty store** | Returns an empty list; no error is raised. |
| **Side effects** | None. Does not load or parse any module data. |

---

## FileStorage [Normative]

`FileStorage` is the minimum required storage adapter. It reads YAML files from a
filesystem directory on every call to `resolve_module`. No caching of any kind is
performed.

### Constructor

```
FileStorage(path: string | Path)
```

`path` is the directory containing `.yaml` grammar files. It is stored as-is; no
validation is performed at construction time. A missing directory surfaces as an error
at the first `resolve_module` or `list_modules` call.

### `resolve_module(name)` [Normative]

1. Construct the file path: `{path}/{name}.yaml`.
2. Open the file for reading (UTF-8 encoding is assumed; the YAML specification
   requires UTF-8 as the default).
3. Parse the file content using a **safe** YAML parser (one that does not execute
   arbitrary code). The reference implementation uses PyYAML's `yaml.safe_load`.
4. Return the parsed value (a dict, list, or scalar) as-is. This is already a fresh
   Python object on each parse, satisfying the mutable-copy requirement.
5. If the file does not exist, raise `ModuleNotFoundError(name)`. The original
   `FileNotFoundError` from the OS must not propagate directly; it must be caught and
   re-raised as `ModuleNotFoundError`.

**YAML parsing note**: `yaml.safe_load` returns `None` for an empty file, which
satisfies the empty-module contract. No special-casing is needed.

### `list_modules()` [Normative]

1. Enumerate all files in `path` matching the glob pattern `*.yaml`.
2. Collect the stem of each matching filename (the filename without the `.yaml`
   extension).
3. Return the stems sorted lexicographically (locale-independent, byte-order sort).

---

## CompilingFileStorage [Informative]

`CompilingFileStorage` extends `FileStorage` with a binary compile cache stored
alongside the YAML source files. The first call to `resolve_module` for a given module
parses the YAML source and writes a binary cache file. Subsequent calls read the binary
cache directly, bypassing YAML parsing. This provides faster load times for large
grammar sets.

The reference implementation uses the MessagePack format (`.mp` files) for the binary
cache. Any equivalent binary serialization format that round-trips the YAML data
structure without loss may be used.

### `resolve_module(name)` [Informative]

1. Construct the cache file path: `{path}/{name}.mp`.
2. Attempt to read and deserialize the cache file:
   a. Open the file in binary read mode.
   b. Deserialize using the binary format (MessagePack in the reference implementation,
      with `raw=False` so string values are decoded to native strings rather than bytes).
   c. On success: return the deserialized data. This satisfies the mutable-copy
      requirement because deserialization always constructs new Python objects.
3. On any failure (file not found, truncated file, corruption, deserialization error):
   fall through to YAML loading:
   a. Call `FileStorage.resolve_module(name)` (the base implementation) to parse the
      YAML source. If the YAML file does not exist, `ModuleNotFoundError` propagates.
   b. Write the result to the cache file: open `{path}/{name}.mp` in binary write mode
      and serialize the parsed data.
   c. Return the parsed data.

**Cache invalidation**: there is no automatic cache invalidation on YAML change. If a
YAML file is modified, the stale `.mp` cache file remains until `clean()` is called or
the cache file is deleted manually.

**Concurrency**: the reference implementation performs no locking. Concurrent writes to
the same cache file produce undefined behavior. This adapter is intended for
single-process use.

### Additional Operations [Informative]

```
clean()
```

Removes all `.mp` cache files from `path`. Does not affect `.yaml` files. Raises no
error if the directory is empty or contains no `.mp` files.

```
recompile_modules()
```

1. Call `clean()` to remove all existing cache files.
2. For each `.yaml` file stem in the directory (in any order), call `resolve_module`
   to load and re-cache it.

`recompile_modules` is a maintenance operation intended to be called explicitly after
updating grammar files, not invoked during normal text generation.

---

## CachedFileStorage [Informative]

`CachedFileStorage` extends `FileStorage` with a **class-level in-memory cache**. The
cache is shared across all instances of `CachedFileStorage` (or a subclass, if the
subclass defines its own class-level cache dict) within the same process. This
eliminates repeated filesystem reads for modules that have already been loaded.

The class-level cache persists for the lifetime of the process. It is not invalidated
when YAML files change on disk.

### `resolve_module(name)` [Informative]

1. Check the class-level cache dict: if `name` is a key, return a **deep copy** of the
   cached value.
   - The deep copy is required because the grammar parser mutates the returned map. A
     shallow copy would allow mutations to corrupt the cached data.
2. On cache miss: call `FileStorage.resolve_module(name)` to obtain fresh data.
3. Store the loaded data in the class-level cache under `name`.
4. Return a deep copy of the newly cached data.

**Why deep copy**: In the reference implementation, the module data is a nested dict
that the parser modifies in place (popping `"include"` and `"render"` keys). A deep
copy ensures the cached copy is not affected by those modifications.

**Cache scope**: The cache is keyed only by module name, not by path. If two
`CachedFileStorage` instances point to different directories but load a module with the
same name, they share the cached data. In practice, this is not a concern because all
storage instances in one process typically point to the same grammar directory.

### Cache Clearing [Informative]

There is no public method to clear the in-memory cache in the reference implementation.
Tests that use `CachedFileStorage` must clear the class-level cache dict between test
runs to avoid cross-test pollution. In the reference implementation, tests do this by
assigning a fresh empty dict to `CachedFileStorage._modules` directly.

---

## CompilingCachedFileStorage [Informative]

`CompilingCachedFileStorage` combines both caching strategies: binary file caching from
`CompilingFileStorage` and in-memory caching from `CachedFileStorage`. The in-memory
cache stores the **serialized binary bytes** of each module (not the deserialized dicts)
as a performance optimization: storing bytes avoids the need for deep copy and produces
independent data structures on each access via deserialization.

### `resolve_module(name)` [Informative]

1. Check the class-level cache dict: if `name` is a key, deserialize and return the
   cached bytes.
   - In the reference implementation: `msgpack.loads(self._modules[name], raw=False)`.
   - Deserialization always produces a fresh dict, satisfying the mutable-copy
     requirement without an explicit deep copy.
2. On cache miss (key absent) or on deserialization failure (corrupted cached bytes):
   fall through to the binary file cache:
   a. Call `CompilingFileStorage.resolve_module(name)` to obtain the data (reading the
      `.mp` file if available, otherwise parsing YAML and writing the `.mp` file).
3. Re-serialize the result to bytes: `self._modules[name] = msgpack.dumps(mod)`.
4. Return the data obtained in step 2a.
   - Note: the data is returned as obtained from `CompilingFileStorage`, not by
     deserializing the just-cached bytes. This is equivalent since the bytes encode
     the same data, but avoids a redundant deserialization step.

### Inheritance and Cache Isolation [Informative]

`CompilingCachedFileStorage` must define its **own** class-level `_modules = {}` dict,
independent of `CachedFileStorage._modules`. This prevents the two adapter classes from
sharing an in-memory cache that stores incompatible types (dicts vs. bytes).

---

## Conformance Summary [Normative]

All storage adapter implementations claiming conformance to this specification MUST:

1. Implement `resolve_module(name)` and `list_modules()`.
2. Return a mutable, independent copy from `resolve_module`. A subsequent call with the
   same name must return the original data unaffected by any mutations to prior return
   values.
3. Raise `ModuleNotFoundError(name)` (or equivalent) when the named module does not
   exist. The exception must carry the module name.
4. Return `None` for an empty (zero-byte or whitespace-only) YAML file.
5. Return module stems in alphabetically sorted order from `list_modules`.
6. Use safe YAML parsing that does not execute arbitrary code.

Caching adapters additionally MUST:

7. Return data equivalent to what `FileStorage` would return for the same module name
   and directory contents. Caching must be a transparent optimization; it must not alter
   the returned values.

---

## Error Types [Normative]

| Exception | Raised by | Condition |
|-----------|-----------|-----------|
| `ModuleNotFoundError(name)` | `resolve_module` | The named module does not exist in the backing store. |
| YAML parse error (propagated) | `resolve_module` | The YAML file exists but contains invalid YAML syntax. |

`ModuleNotFoundError` is a domain-specific exception. It is not the same as the Python
built-in `ModuleNotFoundError` (which is about Python modules). Implementations should
define a namespaced equivalent (e.g., `GrammarModuleNotFoundError`) to avoid confusion
with the host language's own module-not-found error type.

---

## Implementation Notes [Informative]

### Why Class-Level Cache?

The class-level (rather than instance-level) cache means that all `CachedFileStorage`
instances in the same process share parsed module data. In the PrestoPlot HTTP server,
a new `CachedFileStorage` instance may be created per request; the class-level cache
ensures that modules loaded during earlier requests are not reloaded for later ones.

### Why Store Bytes in CompilingCachedFileStorage?

Storing serialized bytes rather than dicts in the in-memory cache avoids the need for
deep copying. When the in-memory cache stores dicts (as in `CachedFileStorage`), a
deep copy must be made on every cache hit to satisfy the mutable-copy contract. When
the cache stores bytes, deserialization on every cache hit produces a naturally
independent copy at a cost comparable to or lower than deep copy for typical grammar
sizes.

### Cache File Coexistence

`CompilingFileStorage` and `CompilingCachedFileStorage` write `.mp` files into the same
directory as the `.yaml` source files. This means the directory will contain both
`characters.yaml` and `characters.mp`. The `list_modules()` method only enumerates
`.yaml` files and is not affected by the presence of `.mp` files.

### Testing Guidance

When testing storage adapters:

- Use `FileStorage` as the baseline; test all other adapters against it for data
  equivalence.
- Clear class-level caches (`_modules = {}`) in `setup_method` or a fixture to prevent
  cross-test pollution.
- Test `resolve_module` with a module name that does not exist to verify
  `ModuleNotFoundError` is raised with the correct module name.
- Test that mutating the returned dict from one call does not affect subsequent calls
  (the mutable-copy invariant).
- For `CompilingFileStorage`, verify that a `.mp` file is created on first access and
  that the cache file is removed by `clean()`.
- For `CompilingFileStorage`, test fallback: write a corrupted (truncated) `.mp` file
  before the test and verify that the YAML is loaded successfully and a valid `.mp`
  file is written.
