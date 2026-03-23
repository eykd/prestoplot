# 04 — Application Services

## Purpose

This document specifies the application layer of PrestoPlot: the use cases that
orchestrate the domain and adapters to produce text from a named grammar module.
The application layer owns no business logic of its own — it sequences calls to
domain services and adapters, handles cross-cutting concerns (error propagation,
logging), and enforces pre- and post-conditions.

---

## Overview

The application layer exposes one primary use case: **Generate Text** from a named
grammar module. All other operations documented here (`parse_grammar_file`,
`parse_value`, rule evaluation) are internal sub-operations that the primary use case
composes. They are specified here because conforming implementations must reproduce
their behavior exactly.

The entry point for the primary use case is named `render_story` in the reference
implementation, and corresponds to the `GenerationCommandPort.render` operation in the
hexagonal architecture.

---

## UC-1: Generate Text (Primary Use Case)

**Name**: `render_story` / `GenerationCommandPort.render`

### Signature

```
render_story(storage, module_name, start="Begin", seed=None, **user_vars) -> str
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `storage` | StoragePort | Configured storage adapter with at least one grammar module |
| `module_name` | string | Identifies an existing module in the storage |
| `start` | string | Name of the entry-point Rule (default: `"Begin"`) |
| `seed` | string or None | Seed for deterministic generation. `None` produces a random seed |
| `**user_vars` | any | Additional key-value pairs merged into the initial Context |

### Pre-conditions

- `storage` is configured and able to resolve `module_name`.
- The module identified by `module_name` contains a rule whose key matches `start`
  (default `"Begin"`).
- If `seed` is a string, it may be any non-empty string value.

### Steps

1. **Create Context**: Call `get_context(seed, **user_vars)`. This returns a Context
   map containing at minimum `{"seed": <resolved_seed>}`, plus any user variables.
   If `seed` is `None`, a fresh random seed string is generated. If `seed` is a
   string, it is used verbatim.

2. **Parse grammar**: Call `parse_grammar_file(storage, module_name, context)`. This
   populates the Context with all rules from `module_name` and any modules it
   transitively includes. See UC-3 for the full specification of this step.

3. **Evaluate entry point**: Evaluate `str(context[start])`. String coercion on the
   Rule object triggers lazy evaluation. The result of this evaluation is the final
   generated string.

4. **Return** the resulting string.

### Post-conditions

- The returned value is a `str`.
- The returned value is **deterministic** for the same `module_name`, same `start`
  rule, same `seed` string, and same `user_vars`. Two calls with identical inputs
  produce identical output.
- When `seed` is `None`, a fresh seed is generated per call, producing
  non-deterministic output across calls.

### Error Conditions

| Condition | Behavior |
|-----------|----------|
| `module_name` not found in storage | Raise `ModuleNotFoundError(module_name)` and propagate to caller |
| `start` key not present in context after parsing | Raise `KeyError(start)`; do not attempt to recover |
| Unknown `render` strategy in YAML | Raise `ConfigurationError` naming the strategy and the grammar path |
| Template evaluation failure | Log the grammar path and template content at ERROR level; re-raise the original exception |
| Invalid Markov chain length | Raise `ValidationError`; see 07-markov-chain.md |
| Unknown selection mode | Raise `ConfigurationError` naming the mode |

---

## UC-2: Generate Multiple Results

**Name**: `run --count N` (CLI) / repeated calls to `render_story`

This use case repeats UC-1 exactly `N` times and joins the results.

### Behavior by Seed Type

| Seed input | Behavior across N calls |
|------------|------------------------|
| String seed | The same seed string is used each time. All N results are identical. |
| `None` (no seed) | A fresh random seed is generated per call. All N results differ (with overwhelming probability). |

### Output Format

Results are concatenated, separated by the delimiter `"\n---\n"`.

For `N = 1`, no delimiter is added. For `N = 3`, the output is:
```
<result 1>
---
<result 2>
---
<result 3>
```

### Notes

- This use case exists at the adapter (CLI) layer, not in the domain. The domain only
  exposes single-call generation.
- The delimiter `"\n---\n"` is normative for the CLI adapter. Programmatic callers
  invoking `render_story` in a loop receive plain strings and may join however they
  choose.

---

## UC-3: Parse Grammar File (Internal Orchestration)

**Name**: `parse_grammar_file`

This is the recursive sub-operation that populates the Context with all parsed Rules.
It is called once per module in the transitive include graph.

### Signature

```
parse_grammar_file(storage, module_name, context, visited=None) -> context
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `storage` | StoragePort | Storage adapter |
| `module_name` | string | Name of the module to parse |
| `context` | Context | Mutable context map to populate |
| `visited` | set of string or None | Set of module names already parsed; guards against include cycles |

### Steps

1. **Initialize cycle guard**: If `visited` is `None` (top-level call), create a new
   set `{module_name}` and assign it to `visited`. Otherwise, if `module_name` is
   already in `visited`, return `context` unchanged immediately (cycle detected —
   silently skip). Otherwise, add `module_name` to `visited` and continue.

2. **Resolve module**: Call `storage.resolve_module(module_name)`. This returns a
   **mutable copy** of the raw module data (a map of string keys to raw YAML values).
   The returned copy must not be a shared reference — subsequent destructive operations
   must not affect the storage's internal state or any other caller's view of the data.

3. **Process includes**: Pop the `"include"` key from the raw data (if absent, treat
   as an empty list). For each module name in the resulting list, in order, call
   `parse_grammar_file(storage, included_module_name, context, visited)` recursively.
   This merges included rules into the context before the host module's own rules.
   Later includes and the host module's rules override earlier definitions for the
   same key.

4. **Determine render strategy**: Pop the `"render"` key from the raw data (if absent,
   default to `"ftemplate"`). Look up the corresponding TemplateEngine. Valid values
   are `"ftemplate"` and `"jinja2"` (alias `"jinja"`). An unrecognized value raises
   `ConfigurationError`. See 08-template-engines.md for engine behavior.

5. **Parse rules**: For each remaining key-value pair in the raw data, call
   `parse_value(value, grammar_path_for_key, context, render_strategy)` and store
   the result in `context[key]`. The `grammar_path_for_key` is a string that combines
   the module name and the rule key (e.g., `"modulename:RuleKey"`) for use in error
   messages and logging.

6. **Return** the updated context.

### Rule Override Semantics

If an included module and the host module both define a rule with the same key, the
host module's definition wins (it is parsed last and overwrites the earlier entry).
If two included modules define the same key, the later include wins. This is analogous
to mixin composition in object-oriented systems.

### Mutability Requirement

The `"include"` and `"render"` keys are **destructively removed** (popped) from the
raw data during step 3 and step 4. The storage adapter MUST return a fresh mutable
copy on each call to `resolve_module`. A storage adapter that returns a cached
reference to a shared internal map will corrupt that map on first use.

### Cycle Handling

Include cycles are silently ignored. If module A includes module B and module B
includes module A, the second attempt to parse either module finds it already in
`visited` and returns the context unchanged. No error is raised. The rules parsed
before the cycle was detected remain in the context.

---

## UC-4: Parse Value (Internal, Recursive)

**Name**: `parse_value`

Converts a raw YAML value into a domain Rule object. Called for every value in every
grammar module during UC-3 step 5.

### Signature

```
parse_value(value, grammar_path, context, render_strategy) -> Rule
```

### Dispatch Table

The type of `value` determines the resulting Rule:

| Input type | Condition | Output Rule | Notes |
|-----------|-----------|-------------|-------|
| list | mode is `reuse` (default) | `Database(choose(items))` | Items are recursively parsed via `parse_value` |
| list | mode is `pick` | `Database(pick(items))` | Items are recursively parsed via `parse_value`; list is mutable in closure |
| list | mode is `ratchet` | `Database(ratchet(items))` | Items are converted to `RenderedStr`; not recursively parsed |
| list | mode is `markov` | `Database(markovify(items))` | Items are converted to `RenderedStr`; not recursively parsed |
| list | mode is `list` | `Datalist(items)` | Items are converted to `RenderedStr`; no Database wrapper |
| map/dict | (any) | `Databag(parsed_values)` | Values are recursively parsed via `parse_value` |
| bool | (any) | boolean (pass-through) | No wrapping |
| string/number | (any) | `RenderableText(fix_text(value))` | `fix_text` strips leading/trailing whitespace and dedents |

### Mode Extraction

Before dispatching on item type for lists, the mode is extracted by calling
`get_list_setting(value, grammar_path)`:

1. If the list is non-empty and the first element is a single-key map whose only key
   is `"mode"`, that element is **removed** from the list (destructively consumed) and
   its value becomes the mode.
2. Otherwise, the mode defaults to `"reuse"` and the list is unchanged.

See 05-selection-modes.md for the full normative specification of each mode.

### fix_text Normalization

Before wrapping a scalar value in `RenderableText`, it is passed through `fix_text`:

1. Apply dedent: remove the common leading whitespace prefix from all lines.
2. Strip: remove leading and trailing whitespace (including newlines) from the result.

This allows multi-line YAML block scalars to be used as template strings without
unintended indentation.

### Recursive Parsing

For `reuse` and `pick` modes, each item in the list is itself passed through
`parse_value`. This allows list items to be nested lists, maps, or template strings —
not just plain strings. The same `render_strategy` is propagated to all recursive
calls.

For `ratchet`, `markov`, and `list` modes, items are converted to `RenderedStr`
directly (plain string wrappers) rather than recursively parsed. This means nested
lists and maps are not supported as items within these modes.

---

## UC-5: Evaluate a Rule (Internal, Lazy)

Rules are **not evaluated at parse time**. Evaluation is deferred until the Rule is
coerced to a string.

### Trigger

Evaluation is triggered by:
- `str(rule)` — explicit string coercion.
- f-string interpolation: `f"{rule}"` (which calls `str(rule)` internally).
- Jinja2 variable rendering: `{{ rule }}` (which calls `str(rule)` internally).

### Evaluation Chain

When the entry-point rule `Begin` is coerced to a string:

1. `str(context["Begin"])` is called on the `Database` wrapping the Begin rule.
2. The `Database.__str__` method calls `self.factory(self.context)`, which invokes
   the `choose` factory (for the common case of a list).
3. The `choose` factory selects one of the pre-parsed items. If the selected item is
   a `RenderableText`, it calls `item.render(context)`.
4. `render(context)` evaluates the template string, substituting references like
   `{Name}` or `{Name.hero}` with the values of those keys in the context.
5. Each such substitution coerces the referenced Rule to a string (recursively
   triggering evaluation for that Rule).

This lazy, recursive evaluation continues until all referenced rules have been
resolved to plain strings.

### Parse Time vs. Render Time

| Phase | What happens |
|-------|-------------|
| **Parse time** | YAML data is converted into Rule objects (`Database`, `Databag`, `RenderableText`, etc.). Templates are stored as unrendered strings. |
| **Render time** | `str(context["Begin"])` is called. Templates are evaluated. Rules referenced within templates are themselves coerced and evaluated. |

No template evaluation occurs during `parse_grammar_file`. All template evaluation
occurs during and after `str(context[start])`.

### Keyed Access and Seed Scoping

When a template references `{Name.hero}`, the Database for `Name` is accessed with
the key `"hero"`:

1. `Database.__getattr__("hero")` is called.
2. If `"hero"` is not in the cache, a scoped seed is constructed:
   `scoped_seed = f'{context["seed"]}-hero'`.
3. The factory is called with a context copy where `seed` is replaced by the scoped
   seed.
4. The result is stored in `self.cache["hero"]` and returned.
5. Subsequent accesses to `{Name.hero}` with the same base seed return the cached
   value — the name for `hero` is stable within one render pass.

This mechanism enables consistent character names: `{Name.protagonist}` always
returns the same value within a render pass, and `{Name.antagonist}` returns a
different but equally consistent value.

---

## Error Handling Summary

| Error condition | Behavior |
|----------------|----------|
| Module not found in storage | `ModuleNotFoundError(name)` — propagate to caller |
| Include cycle | Silently skipped; already-visited modules are not re-processed |
| Unknown `render` strategy | `ConfigurationError` with strategy name and grammar path |
| Template evaluation failure | Log at ERROR with grammar path and template content; re-raise |
| Markov chain length out of range | `ValidationError`; see 07-markov-chain.md |
| Unknown selection mode | `ConfigurationError` with mode name |
| Empty list in `pick` mode | `IndexError` — undefined behavior; do not attempt to handle |
| Key missing from context at render time | `KeyError` — propagate to caller |

---

## Sequence Diagram (Informative)

The following illustrates the call sequence for a single `render_story` invocation:

```
Caller
  │
  ├─► get_context(seed, **user_vars)
  │     └─► returns {seed: "...", ...user_vars}
  │
  ├─► parse_grammar_file(storage, "module", context)
  │     ├─► storage.resolve_module("module")  → raw_doc (mutable copy)
  │     ├─► parse_includes(...)               → recursive parse_grammar_file calls
  │     ├─► parse_render_strategy("ftemplate") → render_fn
  │     └─► parse_data(raw_doc, ..., render_fn)
  │           └─► for each key:
  │                 parse_value(value, ...) → Rule
  │                 context[key] = Rule
  │
  └─► str(context["Begin"])
        └─► Database.__str__()
              └─► choose_factory(context)
                    └─► rng.choice(items)
                          └─► RenderableText.render(context)
                                └─► render_fn("{Name.hero} fights {Name.villain}", ...)
                                      ├─► str(context["Name"].hero)  → "Arthur"
                                      └─► str(context["Name"].villain) → "Mordred"
```

---

## Conformance Notes

A conforming implementation MUST:

1. Produce deterministic output for the same `module_name`, `start`, `seed` (string),
   and `user_vars`.
2. Silently skip include cycles rather than raising an error.
3. Allow host-module rules to override included rules for the same key.
4. Apply `fix_text` (dedent + strip) to all scalar string values before wrapping in
   `RenderableText`.
5. Return a mutable copy from `resolve_module` so that `include` and `render` key
   removal does not corrupt stored state.
6. Propagate `render_strategy` to all recursive `parse_value` calls within the same
   module.
7. Use `grammar_path:key` as the `grammar_path` argument when calling `parse_value`
   from `parse_data` (e.g., `"module:Begin"`), so that error messages can identify
   the exact stanza.
