# 01 — Domain Model

This document defines the entities, value objects, aggregates, and domain services
that constitute the PrestoPlot domain. All terms defined here are used consistently
throughout the specification. Implementations in any language must faithfully represent
the semantics described here, regardless of the specific data structures chosen.

---

## Overview

PrestoPlot's domain is organized around one primary concept: the **Grammar**. A Grammar
is a named collection of Rules loaded from a Module (a YAML file). Rules are evaluated
lazily in a shared mutable **Context**. Determinism is achieved through a **Seed**
stored in the Context.

The key insight of the domain model is that Rules are not evaluated at parse time. They
are wrapped in evaluation objects (Database, Databag, Datalist) that defer all
rendering until the value is actually coerced to a string. This lazy evaluation — driven
through the Context at render time — is what makes seed-based determinism possible.

---

## Aggregate Root: Grammar

### Identity

A Grammar is identified by its **module name** — the string used to request it from
Storage. Module names are unique within a given Storage instance. In the reference
implementation, this typically corresponds to the filename stem of a YAML file (e.g.,
`"characters"` for `characters.yaml`).

### Structure

A Grammar owns:

- A **rule map**: an ordered mapping of `string → Rule`. Keys are rule names as they
  appear in the YAML file. This map is populated during parsing and its structure is
  immutable after construction (though stateful rules like `pick` and `ratchet` have
  internal mutable state).
- A **RenderStrategy** value object (see below): determines which template engine is
  used for all `TextRule` instances in this Grammar. Defaults to `ftemplate`.
- An **IncludeList**: an ordered list of module names to be resolved and merged before
  the Grammar's own rules. Corresponds to the `include:` key in the YAML file.

In the reference implementation, the Grammar's rule map is the Context dict itself:
rules are stored as Context keys. This is an implementation detail; what matters
semantically is that after parsing, each named rule is accessible by name within the
evaluation environment.

### Invariants

1. **Begin rule required.** Every Grammar used as an entry point for rendering MUST
   contain a rule named `Begin`. Attempting to render a Grammar without a `Begin` rule
   is an error. (Grammars used only as includes may omit `Begin`.)

2. **Include cycle detection.** When processing includes, the parser tracks which
   modules have already been visited in the current parse pass. If a module is
   encountered again during recursive include processing, it is silently skipped. This
   prevents infinite loops and duplicate rule definitions.

3. **Include ordering.** Included grammar rules are merged before the including
   Grammar's own rules. If both define the same rule name, the later definition (from
   the including Grammar) takes precedence. Includes are processed in the order listed.

### Lifecycle

1. A client requests rendering by providing a module name and optional seed.
2. The **GrammarParser** domain service loads the module from Storage.
3. Include directives are resolved recursively.
4. All top-level YAML keys are parsed into Rule objects and stored in the Context.
5. Rendering begins from the `Begin` rule (or the specified start rule).
6. After rendering, the Grammar/Context is typically discarded; it is not cached
   between render calls (though specific storage adapters may cache the raw YAML data).

---

## Entity: Rule

A Rule is a named entry in a Grammar. All Rules share the following:

- **grammar_path** (string): A dot-separated or colon-separated identifier used in
  error reporting (e.g., `"characters:Name"`). It records where in the source the Rule
  was defined. It is not used for evaluation.
- **context** (Context reference): A reference to the mutable rendering Context. This
  reference is established at parse time.

Rules are not standalone objects in the traditional DDD sense — they do not have
identity independent of their containing Grammar. They are entities in that they carry
mutable state (pick and ratchet rules) and have a defined lifecycle within the Grammar.

### Subtype 1: TextRule

A TextRule wraps a single **template string**.

**Construction:**
- The raw string value from YAML is normalized: common leading whitespace is removed
  (dedented) and leading/trailing whitespace is stripped. This normalization happens at
  parse time, not at render time.
- The normalized string is stored as the template.
- The Grammar's RenderStrategy function is captured at parse time and stored alongside
  the template.

**Rendering:**
- When coerced to a string (or when `render(context)` is called explicitly), the
  template is evaluated by calling `render_strategy(template, grammar_path, context)`.
- The render strategy evaluates all template expressions (e.g., `{Name}`) by looking
  them up in the provided Context.
- The result is a **RenderedStr** (a string subtype with article properties).

**Article properties** (`.a`, `.an`, `.A`, `.An`):
- Available on all TextRule instances and RenderedStr values.
- See the Article value object description below.

**String coercion behavior:**
- `str(text_rule)` calls `render(context)` using the TextRule's own context reference.

### Subtype 2: ListRule

A ListRule holds an ordered list of candidate values and selects among them using a
**SelectionMode**.

**Construction:**
- The YAML list is parsed. If the first element is a single-key mapping with key
  `"mode"`, that element is consumed and its value determines the SelectionMode.
  If no mode element is present, the mode defaults to `reuse`.
- Each remaining list item is itself parsed as a Rule (recursive). This means list
  items can be strings (becoming TextRules), nested lists, or nested mappings.
- A **SelectionFactory** callable is constructed from the parsed items and mode.
- The ListRule is wrapped in a **Database** object (see below), which is what callers
  actually hold a reference to.

**Selection at evaluation time:**
- List items are not rendered at parse time.
- When the Database is coerced to a string or its factory is called, the SelectionFactory
  selects one item (according to the mode) and renders it if it is a TextRule.

**Modes:**
- `reuse`: random selection with replacement (stateless, seeded).
- `pick`: random selection without replacement (stateful — items are removed from the list).
- `ratchet`: sequential cycling (stateful — position advances on each call).
- `markov`: Markov chain generation from the list items as training data (stateless per call, seeded).
- `list`: no selection; the list is exposed as an ordered Datalist for indexed access.

> **Important note on `markov` and `ratchet` items.** When mode is `markov` or
> `ratchet`, list items are treated as raw strings wrapped in `RenderedStr` rather than
> being parsed as full Rules. This is because markov chains train on literal string
> values and ratchet items are typically simple strings.

**String coercion:**
- `str(database)` calls `factory(context)` directly. The result is rendered if it is a
  TextRule.

### Subtype 3: StructRule (Databag)

A StructRule is a key-value mapping where each value is itself a Rule.

**Construction:**
- The YAML mapping is parsed. Each key-value pair is recursively parsed: values become
  Rules of the appropriate subtype.
- The StructRule is represented as a **Databag** object — a dictionary-like container
  that holds the parsed Rules and provides context-aware access.

**Attribute / key access:**
- Accessing `databag["key"]` or `databag.key` retrieves the Rule stored at that key
  and, if it is a TextRule, calls `rule.render(context)` using the Databag's context.
- Non-TextRule values (nested Databases, other Databags) are returned as-is.
- Accessing a missing key raises an error (KeyError).

**String coercion:**
- A StructRule/Databag is a container, not a value. Direct `str()` coercion is not
  meaningful in the application domain, though it may produce a representation for
  debugging purposes.

**Nesting:**
- StructRules may be nested arbitrarily. A Databag's values may themselves be
  Databases (wrapping ListRules) or other Databags.

---

## Entity: Database

The Database is the most semantically significant runtime object in the domain. It
mediates all access to a ListRule's SelectionFactory and implements per-key caching
with seed scoping.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `factory` | `Callable[(Context) -> Any]` | The selection function (from `choose`, `pick`, `ratchet`, `markovify`) |
| `context` | `Context` | Reference to the mutable rendering Context |
| `grammar_path` | `string` | Source identifier for error reporting |
| `cache` | `mutable map[string -> Any]` | Per-key result cache; populated on first access |

### Attribute / Key Access Protocol

When a caller accesses attribute or key `K` on a Database:

1. **Cache check.** If `cache[K]` exists, return the cached value immediately.

2. **Instance field check.** If `K` matches an own field of the Database object
   (`factory`, `context`, `grammar_path`, `cache`), return that field. This prevents
   the key-scoping logic from shadowing the Database's own fields.

3. **String method delegation.** If `K` is the name of a standard string method (i.e.,
   the string type in the implementation language has an attribute named `K`), delegate
   to `str(self).K`. This allows Database objects to be used like strings in template
   expressions. For example, `{Name.upper}` in a template calls `upper()` on the
   string coercion of the Database. The result is cached.

4. **Key-scoped factory call** (the normal case for grammar rule access):
   a. Construct a scoped seed: `scoped_seed = f"{context['seed']}-{K}"`.
   b. Temporarily update the Context: set `context["seed"] = scoped_seed` and
      `context["key"] = K`.
   c. Call `factory(context)`.
   d. Restore the original `context["seed"]` and `context["key"]` values.
   e. Store the result in `cache[K]`.
   f. Return the result.

> **Restoration is required.** The Context update during step 4b must be temporary.
> After the factory call completes (step 4c), the original seed and key values must be
> restored (step 4d) before any other code runs. In the reference implementation this
> is achieved with a context manager.

### String Coercion

`str(database)` calls `factory(context)` **directly**, using the Context as-is (no
key scoping). The result is not cached.

### Key / Item Access Equivalence

`database[K]` is equivalent to `database.K`. Implementations must support both forms
to enable template expressions like `{Names[key]}` as well as `{Names.hero}`.

### Purpose and Rationale

The key-scoping mechanism is what enables a single Grammar rule to produce consistent
but independent values for different named scopes within one render pass.

Consider the template:
```
{Name.Protag} fights {Name.Antag}.
```

- `{Name.Protag}` accesses the `Name` Database with key `"Protag"`. The Database
  derives seed `"{base_seed}-Protag"` and calls the factory. The result (say, "Alice")
  is cached under `"Protag"`.
- `{Name.Antag}` accesses the same `Name` Database with key `"Antag"`. The Database
  derives seed `"{base_seed}-Antag"` and calls the factory. The result (say, "Bob")
  is cached under `"Antag"`.
- If `{Name.Protag}` appears again later in the same render pass, the cached value
  "Alice" is returned without re-evaluating the factory.

This mechanism provides referential consistency: the same named entity always has the
same attribute values within one render pass.

---

## Value Objects

### Seed

A Seed is a string used to initialize an RNG for reproducible output.

**Auto-generated seeds:**
- Generated by: `md5(str(rng.random()).encode('utf-8')).hexdigest()`
- Result: a 32-character lowercase hexadecimal string.
- The RNG used for auto-generation is the global (non-seeded) RNG by default, or a
  caller-provided RNG instance.

**User-provided seeds:**
- Any string is a valid seed. The system passes it directly to the RNG constructor.
- Example: `seed="testing"` is valid.

**Immutability:**
- A seed value is immutable once set in the Context. It is replaced (not modified) when
  a scoped seed is constructed during Database attribute access.

### ScopedSeed

A ScopedSeed is not a distinct type but a naming pattern for a derived seed:

```
scoped_seed = f"{base_seed}-{key}"
```

Where `base_seed` is the current `context["seed"]` and `key` is the attribute name
being accessed on a Database. The hyphen separator is normative; implementations must
use exactly one ASCII hyphen character (`U+002D`) between the base seed and the key.

**Example:**
- Base seed: `"abc123def456abc123def456abc123de"`
- Key: `"Protag"`
- Scoped seed: `"abc123def456abc123def456abc123de-Protag"`

### Context

The Context is a mutable key-value map threaded through all parsing and rendering
operations. It serves dual purpose: it holds configuration/state for the render pass,
and it accumulates parsed Rule objects as the Grammar is loaded.

**Required keys:**

| Key | Type | Description |
|-----|------|-------------|
| `seed` | string | Current seed for RNG initialization |

**Reserved optional keys:**

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `key` | string | absent | Present during Database attribute access; holds the current scope key |
| `markov_chainlen` | integer | `2` | Chain length for Markov chain generation |
| `start_markov` | string | `""` | Starting characters for Markov chain generation |

**User-provided keys:**
- Any additional keyword arguments passed to `render_story()` (or `get_context()`) are
  stored in the Context and are available as variables in template expressions.
- Example: calling `render_story(storage, "scene", seed="x", hero_name="Alice")` makes
  `{hero_name}` available in templates.

**Grammar rule keys:**
- After parsing, the Context also contains one entry per named Rule in the Grammar (and
  all transitively included Grammars). These are the Database, Databag, or Datalist
  objects produced by the parser.

**Mutation policy:**
- The Context is mutated in-place during Database attribute access (key and seed are
  temporarily updated). Implementations must restore the original values after each
  scoped factory call.
- The Context is not thread-safe; a separate Context instance must be used per
  concurrent render.

### SelectionMode

An enumeration of five values determining how a ListRule selects among its items:

| Mode | Description | Stateful? | Seeded? |
|------|-------------|-----------|---------|
| `reuse` | Random selection with replacement | No | Yes |
| `pick` | Random selection without replacement (items are consumed) | Yes | Yes |
| `ratchet` | Sequential cycling in order | Yes | No |
| `markov` | Markov chain generation using list items as training data | No | Yes |
| `list` | No selection; returns a Datalist for indexed access | No | No |

`reuse` is the default when no `mode:` directive is present in the YAML.

**Statefulness note:** Stateful modes (`pick`, `ratchet`) share state across all
accesses to the same Database instance within one parse/render lifetime. Because the
Database is created at parse time and discarded with the Context, statefulness does
not persist across separate `render_story()` calls.

### RenderStrategy

An enumeration of two values determining which template engine evaluates template
strings:

| Value | Aliases | Description |
|-------|---------|-------------|
| `ftemplate` | (none) | Python f-string-style expression evaluation (default) |
| `jinja2` | `jinja` | Jinja2 template engine |

The `render` key at the top level of a YAML grammar file sets the RenderStrategy for
all TextRules in that Grammar. Included grammars may use a different RenderStrategy;
each Grammar's rules use the strategy declared in their own file.

Any value other than `ftemplate`, `jinja2`, or `jinja` is an error and must cause the
parser to raise an exception.

**ftemplate behavior:**
- Templates use Python f-string expression syntax: `{expression}`.
- Expressions are evaluated in the Context as the local namespace.
- References to Grammar rules trigger rendering of those rules (via string coercion).
- Template evaluation errors are logged and re-raised.

**jinja2 behavior:**
- Templates use Jinja2 syntax: `{{ variable }}`, `{% for %}`, etc.
- The Context is passed as the template rendering variables.
- Undefined variables render as the literal Jinja2 `DebugUndefined` string (not as
  empty string).
- Template errors are logged and raise a domain-level error.

### Article

The Article accessor pattern is available on all rendered strings and TextRule objects.
It provides grammatically correct English indefinite articles.

**Properties:**

| Property | Alias | Returns |
|----------|-------|---------|
| `.an` | `.a` | `"an"` if the first character of the string (lowercased) is in `{a, e, i, o, u}`, otherwise `"a"` |
| `.An` | `.A` | Same as `.an` but capitalized: `"An"` or `"A"` |

**Alias semantics:** `.a` and `.an` return identical values. `.A` and `.An` return
identical values. The aliases exist for stylistic convenience in templates.

**Empty string:** Behavior is undefined when the string is empty (no first character
exists). Implementations may raise an error or return a default.

**Usage in templates:**
```yaml
Begin:
  - "{Person.an.capitalize()} {Person} walks into the room."
  # Produces: "An astronaut walks into the room." or "A doctor walks into the room."
```

---

## Domain Services

### GrammarParser

The GrammarParser is a stateless domain service responsible for loading and parsing a
Grammar module into a Context.

**Primary operation:**

```
parse_grammar_file(storage, module_name, context, visited?) -> context
```

**Algorithm:**

1. If `visited` is not provided, initialize it as a set containing `module_name`.
   If it is provided and already contains `module_name`, return `context` unchanged
   (cycle detected; skip silently).
   Otherwise, add `module_name` to `visited`.

2. Call `storage.resolve_module(module_name)` to obtain the raw YAML data as a mapping.

3. Extract and remove the `include` key (if present). This is the IncludeList.

4. Process each name in the IncludeList by recursively calling `parse_grammar_file`
   with the same `visited` set. This merges included rules into the Context before
   the current module's rules.

5. Extract and remove the `render` key (if present). Parse it as a RenderStrategy.
   Default to `ftemplate` if absent.

6. For each remaining key-value pair in the raw data, parse the value into a Rule
   object (see parse_value below) and store it in the Context under the key.

7. Return the updated Context.

**parse_value algorithm:**

Given a raw YAML value `v`:

- If `v` is a list:
  - Check if the first element is a single-key mapping `{"mode": <mode_string>}`.
    If so, remove it and use `<mode_string>` as the SelectionMode. Otherwise, default
    to `reuse`.
  - For `reuse` mode: parse each item recursively; wrap in a Database backed by a
    `choose` factory.
  - For `pick` mode: parse each item recursively; wrap in a Database backed by a
    `pick` factory.
  - For `ratchet` mode: wrap each item as a RenderedStr (no recursive parse); wrap in
    a Database backed by a `ratchet` factory.
  - For `markov` mode: wrap each item as a RenderedStr (no recursive parse); wrap in a
    Database backed by a `markovify` factory.
  - For `list` mode: wrap each item as a RenderedStr (no recursive parse); return a
    Datalist directly (not wrapped in a Database).

- If `v` is a mapping:
  - Parse each value recursively; return a Databag.

- If `v` is a boolean:
  - Return the boolean value as-is.

- Otherwise (string or scalar):
  - Normalize the string (dedent and strip).
  - Return a RenderableText (TextRule) wrapping the normalized string with the current
    RenderStrategy.

### ContextFactory

The ContextFactory is a stateless domain service responsible for creating a fresh
rendering Context.

**Primary operation:**

```
get_context(seed, **user_vars) -> context
```

**Algorithm:**

1. Initialize the Context as a copy of `user_vars`.
2. Determine the seed:
   - If `seed` is `None` or the global RNG module: auto-generate a seed using the
     global RNG (see Seed value object).
   - If `seed` is an RNG instance: auto-generate a seed using that RNG instance.
   - If `seed` is a string: use it directly.
3. Store the resolved seed in `context["seed"]`.
4. Return the Context.

---

## Relationships and Invariants Summary

The following diagram shows the structural relationships between domain objects:

```
Grammar (aggregate root)
│  Identity: module_name (string)
│  Has: RenderStrategy (value object)
│  Has: IncludeList (ordered list of module_name strings)
│
└── owns named Rules (stored in Context after parsing)
     │
     ├── TextRule / RenderableText (entity)
     │    ├── template: normalized string
     │    ├── grammar_path: string
     │    ├── context: Context reference
     │    └── render_strategy: RenderStrategy function
     │    Rendering: calls render_strategy(template, grammar_path, context)
     │
     ├── ListRule → Database (entity wrapping SelectionFactory)
     │    ├── factory: SelectionFactory callable
     │    ├── grammar_path: string
     │    ├── context: Context reference
     │    └── cache: mutable map[string -> Any]
     │    │
     │    └── SelectionFactory (one of):
     │         ├── choose(items)   → random.choice with seed [reuse]
     │         ├── pick(items)     → random.choice + pop with seed [pick]
     │         ├── ratchet(items)  → sequential, stateful [ratchet]
     │         └── markovify(items)→ NameGenerator with seed [markov]
     │
     ├── StructRule → Databag (entity)
     │    ├── grammar_path: string
     │    ├── context: Context reference
     │    └── data: map[string -> Rule]
     │    Access: retrieves Rule, renders if TextRule
     │
     └── Datalist (entity, list mode only)
          ├── grammar_path: string
          ├── context: Context reference
          └── items: ordered list of RenderedStr
          Access: retrieves item by integer index, renders if TextRule
```

**Context flows through all entities.** The same Context object (not copies) is passed
by reference into Database, Databag, and Datalist at parse time. When a Database
temporarily mutates `context["seed"]` during attribute access, that mutation is visible
to all other objects holding the same Context reference — and must be restored
immediately after the factory call completes.

**Seed is part of Context.** The Seed is not a standalone object; it is the string
value stored at `context["seed"]`. ScopedSeeds are transient: they exist only for the
duration of a single Database factory call.

**Stateful rules share state within one render pass.** A `pick` or `ratchet` Database
created during `parse_grammar_file` maintains its selection state for the entire
lifetime of that parse/render pass. A new `render_story()` call creates a new Context
and new Rule objects; state does not persist between calls.

---

## Non-Goals

The following are explicitly out of scope for the domain model:

- **Persistence of rendered output.** PrestoPlot produces strings; it does not store
  or index them.
- **Grammar validation at parse time.** The system does not validate that referenced
  rule names exist before rendering; missing references surface as errors at render time.
- **Thread safety.** A Context instance must not be shared across concurrent render
  calls. The domain does not provide synchronization primitives.
- **Streaming output.** Rendering is complete before any output is produced; there is
  no incremental output API in the domain model.
