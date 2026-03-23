# 02 — Ports and Adapters (Hexagonal Architecture)

This document specifies the architectural boundaries of PrestoPlot using hexagonal
architecture (also called ports-and-adapters). The goal is to keep the application
core free of I/O concerns: file access, HTTP, and CLI details are pushed to adapters
that implement well-defined port contracts. Any conforming implementation in any
language must satisfy these contracts to be interoperable.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  DRIVING ADAPTERS              APPLICATION CORE        DRIVEN ADAPTERS
│  (left side)                   (hexagon)               (right side) │
│                                                                     │
│  ┌──────────────┐   drives   ┌──────────────────┐                  │
│  │  CLI Adapter │──────────▶ │  render_story()   │──────────────┐  │
│  │  (run/http)  │            │                  │               │  │
│  └──────────────┘            │  GrammarParser   │   ┌───────────▼─┐│
│                              │                  │   │ StoragePort ││
│  ┌──────────────┐   drives   │  ContextFactory  │   │             ││
│  │ HTTP Adapter │──────────▶ │                  │   │ FileStorage ││
│  │              │            │  SeedManager     │   │ CachedFS    ││
│  └──────────────┘            │                  │   │ Compiling…  ││
│                              │                  │   └─────────────┘│
│  ┌──────────────┐   drives   │                  │                  │
│  │ Programmatic │──────────▶ │                  │──────────────┐  │
│  │     API      │            │                  │               │  │
│  └──────────────┘            │                  │   ┌───────────▼─┐│
│                              │                  │   │TemplatePort ││
│                              │                  │   │             ││
│                              │                  │   │  ftemplate  ││
│                              │                  │   │  jinja2     ││
│                              │                  │   └─────────────┘│
│                              │                  │                  │
│                              │                  │──────────────┐  │
│                              │                  │               │  │
│                              └──────────────────┘   ┌───────────▼─┐│
│                                                      │ RandomPort  ││
│                                                      │             ││
│                                                      │ seeded RNG  ││
│                                                      │ global RNG  ││
│                                                      └─────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Primary (Driving) Ports

Primary ports define how the outside world triggers generation. All driving adapters
funnel through a single application service interface.

### GenerationCommandPort

The main application service interface. All driving adapters call this.

```
render_story(
  storage:     StoragePort,
  module_name: string,
  start:       string = "Begin",
  seed:        string | RNG | null = null,
  **user_vars: any
) → string
```

**Parameters:**

| Parameter     | Type                  | Default    | Description                                                                   |
|---------------|-----------------------|------------|-------------------------------------------------------------------------------|
| `storage`     | `StoragePort`         | (required) | Driven adapter that resolves grammar modules.                                 |
| `module_name` | `string`              | (required) | Name of the top-level grammar module to render (no `.yaml` extension).        |
| `start`       | `string`              | `"Begin"`  | The rule name within the module used as the entry point for generation.       |
| `seed`        | `string \| RNG \| null` | `null`   | Seed for deterministic generation. `null` produces a random, non-deterministic run. |
| `**user_vars` | `any`                 | (none)     | Arbitrary key-value pairs injected into the rendering context as top-level variables. Common keys: `markov_chainlen`, `start_markov`. |

**Returns:** The fully rendered string produced by evaluating the `start` rule.

**Behaviour:**

1. A fresh context is created from `seed` and `user_vars`.
2. The grammar module `module_name` (and any transitive includes) is loaded via
   `storage.resolve_module` and parsed into the context.
3. The rule named `start` is looked up in the context and evaluated to a string.
4. That string is returned.

**Errors:**

- If `module_name` does not exist in storage, propagates `ModuleNotFoundError`.
- If the `start` key is absent from the parsed context, raises a key-error equivalent.
- Template rendering errors are logged and re-raised (see `TemplateEnginePort`).

---

## Secondary (Driven) Ports

Secondary ports define what the application core needs from the outside world. Each
port is an interface that must be satisfied by a driven adapter.

### StoragePort

Resolves grammar module definitions from a backing store (filesystem, database, etc.).

```
resolve_module(name: string) → map[string, any]
list_modules()               → list[string]
```

#### `resolve_module(name)`

| Aspect         | Contract                                                                                       |
|----------------|-----------------------------------------------------------------------------------------------|
| Input          | Module name (string, no extension).                                                           |
| Output         | A **mutable copy** of the raw YAML-equivalent data for the module. Callers mutate this map    |
|                | (e.g. `pop("include", ...)` and `pop("render", ...)`). The storage layer must ensure that     |
|                | each call returns an independent copy; shared mutable state between calls is forbidden.       |
| Error          | Raises `ModuleNotFoundError(name)` when the named module does not exist in the store.         |
| Side effects   | None observable by the caller.                                                                |

The returned map has the shape of a parsed YAML document. At the top level it is a
`map[string, any]` where values may be:

- `string` — a TextRule template
- `list[any]` — a ListRule (optionally beginning with a mode-specifier map)
- `map[string, any]` — a StructRule (Databag)
- `bool`

#### `list_modules()`

| Aspect  | Contract                                              |
|---------|-------------------------------------------------------|
| Output  | Alphabetically sorted list of available module names. |
| Errors  | None defined; empty list if store is empty.           |

---

### TemplateEnginePort

Renders a template string against a context map to produce a rendered string.

```
render(
  template:    string,
  source_path: string,
  context:     map[string, any]
) → RenderedString
```

| Parameter     | Type              | Description                                                                                 |
|---------------|-------------------|---------------------------------------------------------------------------------------------|
| `template`    | `string`          | The template text to evaluate.                                                              |
| `source_path` | `string`          | Identifies the origin of the template for error messages only. Does **not** affect output.  |
| `context`     | `map[string, any]`| The variable bindings available to the template expression.                                 |

**Returns:** A `RenderedString` — a string augmented with article properties:

| Property | Type     | Semantics                                                                    |
|----------|----------|------------------------------------------------------------------------------|
| `.a`     | `string` | `"a"` or `"an"` based on the first character of the rendered value.          |
| `.an`    | `string` | Alias for `.a`.                                                              |
| `.A`     | `string` | Capitalised form of `.a` (`"A"` or `"An"`).                                 |
| `.An`    | `string` | Alias for `.A`.                                                              |

**Error contract:** On any rendering failure:
1. Log the error, including the template text, `source_path`, and exception details.
2. Re-raise the exception (do not swallow it).

---

### RandomPort

Provides random number generation with deterministic seeding.

```
get_rng(seed: string | RNG | null) → RNG
```

#### Seed semantics

| Seed value      | Returned RNG                                                              |
|-----------------|---------------------------------------------------------------------------|
| `null`          | The global, unseeded random module. Non-deterministic; advances global state. |
| `string`        | A new seeded RNG instance initialised from the string. Deterministic: the same string always produces the same sequence. |
| `RNG` instance  | The instance itself, returned as-is. Stateful; each call advances the sequence. |

#### RNG interface

Implementations must provide at minimum:

```
choice(items: list) → item
  # Uniformly random selection from a non-empty list.

randint(low: int, high: int) → int
  # Uniformly random integer in [low, high], inclusive on both ends.

paretovariate(shape: float) → float
  # Sample from a Pareto distribution with the given shape parameter.
  # (Informative: used internally for weighted selection. Not required by
  #  all selection modes.)
```

---

## Driving Adapters

### CLI Adapter — `run` command

Invokes `render_story` once (or N times) and writes output to stdout.

**Positional argument:**

| Name   | Description                                             |
|--------|---------------------------------------------------------|
| `file` | Path to a YAML grammar file. Must exist and be readable. |

**Options:**

| Flag               | Type    | Default | Description                                                                                  |
|--------------------|---------|---------|----------------------------------------------------------------------------------------------|
| `--count N`        | integer | `1`     | Number of generation passes to perform. Results are separated by `\n---\n` between outputs.  |
| `--seed SEED`      | string  | (none)  | Seed for deterministic output. If omitted, each run is non-deterministic.                    |
| `--wrap`           | flag    | off     | Enable line-wrapping of output text.                                                         |
| `--wrap-length N`  | integer | `78`    | Column width for line wrapping. Only relevant when `--wrap` is active.                       |
| `--markov-chainlen N` | integer | `2`  | Character chain length used by any `markov`-mode rules in the grammar.                      |
| `--markov-start S` | string  | `""`   | Starting character sequence for Markov generation.                                           |

**Validation:**

- If `--markov-start` is non-empty and `len(--markov-start) < --markov-chainlen`,
  the adapter must exit with an error before any generation occurs.

**Output:**

- Each result is written to stdout, followed by a newline.
- When `--count N` is greater than 1, results are separated by `\n---\n` (a
  blank line, three dashes, blank line).
- When `--wrap` is active, each non-blank line is wrapped to `--wrap-length`
  columns. Blank lines are passed through unchanged.
- Exit code `0` on success; non-zero on any error.

---

### CLI Adapter — `http` command

_(Informative)_

Starts an HTTP server that serves grammar-generated content on each request.

**Positional argument:**

| Name   | Description                                              |
|--------|----------------------------------------------------------|
| `file` | Path to a YAML grammar file. Must exist and be readable. |

**Options:**

| Flag               | Type    | Default | Description                                                       |
|--------------------|---------|---------|-------------------------------------------------------------------|
| `--port N`         | integer | `5555`  | TCP port the HTTP server listens on.                              |
| `--markov-chainlen N` | integer | `2`  | Chain length for any Markov-mode rules.                          |
| `--markov-start S` | string  | `""`   | Starting sequence for Markov generation.                          |

**Validation:** same as `run` — if `--markov-start` is non-empty and shorter than
`--markov-chainlen`, exit with error before binding the socket.

---

### HTTP Adapter

_(Informative)_

Serves content generated by `render_story` as HTML pages over HTTP.

**Route:** `GET /`

- Calls `render_story` with the configured storage and module.
- Interprets the returned string as Markdown and converts it to HTML.
- Responds with HTTP 200 and a complete HTML document wrapping the converted content.

**Error handling:**

- Any exception from `render_story` results in HTTP 500.
- The response body is an HTML error page containing the exception traceback.

**Extension point:** Query parameters are not handled in the reference implementation.
Implementations may extend this adapter to pass query parameters as `user_vars` to
`render_story`.

---

### Programmatic API

For direct use in host-language code, without going through the CLI layer.

```
render_story(
  storage:     StoragePort,
  module_name: string,
  start:       string = "Begin",
  seed:        string | RNG | null = null,
  **user_vars: any
) → string
```

This is the same function defined under `GenerationCommandPort`. The CLI adapters
create a `StoragePort` instance and delegate to it; library users may do the same.

---

## Driven Adapters

### Storage Adapters

All storage adapters implement `StoragePort`. The reference implementations are
file-system based, using the directory containing the grammar file as the module root.

| Adapter                    | Description                                                                          |
|----------------------------|--------------------------------------------------------------------------------------|
| `FileStorage`              | Loads YAML source files on every `resolve_module` call. Simple; no caching.         |
| `CompilingFileStorage`     | _(Informative)_ Compiles parsed YAML to MessagePack (`.mp`) binary files on first load; subsequent loads read the binary cache. Faster for large grammars. |
| `CachedFileStorage`        | _(Informative)_ Keeps parsed modules in an in-memory dict. Returns a deep copy on each call to satisfy the mutable-copy contract. |
| `CompilingCachedFileStorage` | _(Informative)_ Combines binary compilation and in-memory caching. Stores serialised MessagePack bytes in memory; deserialises on each call. |

Full details, including cache invalidation semantics, are specified in
`09-storage-adapters.md`.

---

### Template Engine Adapters

Both adapters implement `TemplateEnginePort`.

| Adapter         | Engine                    | Trigger                            |
|-----------------|---------------------------|------------------------------------|
| `ftemplate`     | Python f-string semantics | `render: ftemplate` (default)      |
| `jinja2`        | Jinja2 template engine    | `render: jinja2` or `render: jinja`|

Full syntax details are specified in `08-template-engines.md` and in
`03-grammar-file-format.md`.
