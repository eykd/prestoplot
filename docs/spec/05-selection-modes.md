# 05 — Selection Modes

## Purpose

This document is the normative specification for all five selection modes available in
PrestoPlot ListRules. Every behavior contract stated here MUST be satisfied by
conforming implementations. Where this document and the reference Python implementation
conflict, this document takes precedence; file a bug against the reference
implementation.

---

## Overview

A ListRule is a YAML list value assigned to a rule key. The **selection mode**
determines how items are chosen from that list each time the rule is evaluated.

Mode is specified by placing a mode-setting element as the **first element** of the
YAML list. If no mode-setting element is present, the mode defaults to `reuse`.

Each mode is realized as a **factory function** — a closure constructed at parse time
that accepts a Context and returns a rendered value. The factory is wrapped in a
`Database` object (or, for `list` mode, a `Datalist`). The Database handles key-scoped
seed derivation and per-key caching; the factory handles item selection.

The five modes are:

| Mode | Selection strategy | Stateful? | Uses seed? |
|------|--------------------|-----------|------------|
| `reuse` | Uniform random, with replacement | No | Yes |
| `pick` | Uniform random, without replacement | Yes (depletes list) | Yes |
| `ratchet` | Sequential, cycling | Yes (advances index) | No |
| `markov` | Markov chain generation | No | Yes |
| `list` | Ordered, index-based access | No | No |

---

## Mode Setting Syntax

### Recognition Rules (Normative)

A list element is recognized as a mode-setting element if and only if ALL of the
following conditions hold:

1. The element is a map (key-value structure), not a string, number, boolean, or list.
2. The map has **exactly one key**.
3. That key is the string `"mode"`.

If these conditions hold, the element is consumed (removed from the list before item
parsing begins) and its value becomes the mode for this ListRule.

If the conditions do not hold, the element is treated as a data item and is NOT
consumed.

### Valid Mode Values

| YAML value | Mode |
|------------|------|
| `reuse` | Reuse (default) |
| `pick` | Pick without replacement |
| `ratchet` | Sequential cycling |
| `markov` | Markov chain generation |
| `list` | Ordered list |

An unrecognized value raises `ConfigurationError`.

### Examples: Mode Settings (Consumed)

```yaml
- {mode: pick}
- {mode: ratchet}
- {mode: markov}
- {mode: list}
```

### Examples: Data Items (Not Consumed)

```yaml
# Multi-key map — treated as a StructRule data item, NOT a mode setting
- {name: foo, value: bar}

# Single-key map whose key is not 'mode' — data item, not a mode setting
- {label: hello}

# String — data item
- reuse

# Number — data item
- 42
```

### Mode Extraction Is Destructive

The mode-setting element is removed from the list in place before item parsing begins.
The remaining elements form the item list for the factory. This removal must not be
observable to the caller.

---

## Mode: `reuse` (Default)

### Summary

Selects uniformly at random from the full item list on every call. The list is never
modified. The same seed always produces the same selection.

### Factory Constructor

```
choose(items: list) -> (Context) -> value
```

`items` is the list of pre-parsed Rule objects (produced by `parse_value` applied to
each element).

### Behavior Contract

1. On each call, seed an RNG from `context["seed"]` (the effective seed at the time of
   evaluation, which may be a scoped seed if the Database was accessed by key).
2. Select one item uniformly at random from the full `items` list using the seeded RNG.
3. If the selected item is a TextRule (i.e., has a `render` method), call
   `item.render(context)` and return the result.
4. If the selected item is already a rendered value (string or other plain type),
   return it directly.
5. The `items` list is **never modified**.

### Determinism

With the same `context["seed"]`, this factory always selects the same item. Across
two calls to `render_story` with the same seed, the same item is selected.

### State

None. The factory closure holds a reference to `items` but never mutates it.

### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Empty list | Undefined behavior. A conforming implementation may raise an exception or return `""`. |
| Single-item list | That item is always returned regardless of seed. |

### YAML Example

```yaml
Colors:
  - red
  - blue
  - green
```

No mode-setting element is present; mode defaults to `reuse`. With seed `"abc"`,
`{Colors}` always produces the same color. With seed `"xyz"`, a different color is
always produced. The same seed always produces the same result.

### Keyed Access Example

```yaml
Begin:
  - "The {Colors.sky} sky meets the {Colors.sea} sea."
```

`{Colors.sky}` uses seed `"{base_seed}-sky"`. `{Colors.sea}` uses seed
`"{base_seed}-sea"`. Within one render pass, `{Colors.sky}` always returns the same
value and `{Colors.sea}` always returns the same value (which may differ from sky's
value). Both are stable within the render pass regardless of how many times they
appear in the template.

---

## Mode: `pick` (Selection Without Replacement)

### Summary

Selects uniformly at random from the remaining (not-yet-selected) items. Each
selected item is permanently removed from the list. Items are never repeated within
a single render pass.

### Factory Constructor

```
pick(items: list) -> (Context) -> value
```

`items` is a **mutable list** of pre-parsed Rule objects. It is captured in the
factory closure. The same list object is shared across all calls to this factory
instance.

### Behavior Contract

1. On each call, seed an RNG from `context["seed"]`.
2. If the list has more than one item, select a random index in the range
   `[0, len(items) - 1]` (inclusive) using `rng.randint(0, len(items) - 1)`.
   If the list has exactly one item, the index is `0` (no randomness applied).
3. Remove and return the item at the selected index using `items.pop(idx)`.
4. If the removed item is a TextRule, call `item.render(context)` and return the
   result. Otherwise return the item directly.
5. The list is **permanently shorter** after each call.

### State

The mutable list in the closure is the state. It is shared across all calls to
the same factory instance. Once an item is removed, it cannot be re-selected by
this factory instance.

### Lifecycle

The mutable list is created fresh at **parse time** — specifically, when
`parse_grammar_file` calls `parse_value`, which calls `pick(items)` to construct the
factory. Each call to `render_story` triggers a new `parse_grammar_file`, which
constructs a new `pick` factory with a fresh copy of the full item list.

Within a single render pass (one call to `render_story`), the list depletes with
each access. Across render passes, the list is reset because a new factory is
constructed.

### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Empty list | `IndexError` — undefined behavior. Do not attempt to handle. |
| List exhausted mid-render | `IndexError` — undefined behavior. Do not attempt to handle. |
| Single-item list | That item is returned; the list is then empty. |

### Interaction with Keyed Access

When `{Weapon.hero}` and `{Weapon.villain}` are both evaluated in one render pass,
each invokes the `pick` factory once. The first invocation removes one item; the
second invocation selects from the remaining items. The two characters are guaranteed
to receive different weapons.

Note that keyed access also changes the seed passed to the factory (via the Database's
scoped seed mechanism). However, for `pick` mode, the seed determines which item is
selected from the remaining items at call time — it does not restore a previously
selected item.

### YAML Example

```yaml
Weapon:
  - mode: pick
  - sword
  - pistol
  - laser

Begin:
  - "The hero wields a {Weapon.hero}. The villain wields a {Weapon.villain}."
```

Within one render pass, `{Weapon.hero}` and `{Weapon.villain}` will always receive
distinct weapons. One possible output: `"The hero wields a pistol. The villain wields
a sword."` The weapon `"laser"` was not selected in this pass.

---

## Mode: `ratchet` (Sequential Cycling)

### Summary

Returns items in order, one per call, cycling back to the first item after the last.
The selection is entirely determined by call order, not by the seed.

### Factory Constructor

```
ratchet(items: list) -> (Context) -> value
```

`items` is a list of `RenderedStr` objects (plain string wrappers, not recursively
parsed Rules). An integer index starting at `0` is maintained in the factory closure.

### Behavior Contract

1. If `items` is empty, return `""` immediately.
2. Return `items[index]`.
3. Advance `index = (index + 1) % len(items)`.
4. If the returned item is a TextRule, call `item.render(context)` and return the
   result. Otherwise return the item directly.
5. `context["seed"]` is **not used**. The output is entirely determined by call order.

### State

An integer index starting at `0`, stored in the factory closure. It advances
monotonically (mod `len(items)`) with each call.

### Lifecycle

The index is initialized to `0` at parse time. Each call to `render_story` triggers a
new parse, resetting the index to `0`. Within a single render pass, the index advances
with each factory call (regardless of which key, if any, was used to access the
Database wrapping this factory).

### Items Are Not Recursively Parsed

Items in `ratchet` mode are converted to `RenderedStr` at parse time, not passed
through `parse_value`. This means nested lists, maps, and template strings are treated
as raw strings. Template expansion does not occur for ratchet items.

### Normative Test Vector

Given the grammar:

```yaml
Colors:
  - mode: ratchet
  - red
  - blue
  - green

Begin:
  - "{Colors.first} {Colors.second} {Colors.third} {Colors.fourth}"
```

The expected output is `"red blue green red"`.

Explanation:
- `{Colors.first}` — index 0 → `"red"`, index advances to 1
- `{Colors.second}` — index 1 → `"blue"`, index advances to 2
- `{Colors.third}` — index 2 → `"green"`, index advances to 3 → wraps to 0
- `{Colors.fourth}` — index 0 → `"red"`, index advances to 1

This test vector MUST be satisfied by all conforming implementations.

### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Empty list | Return `""` |
| Single-item list | Always returns that item; index cycles 0 → 0 |

### Important: Key Access Does Not Reset Index

Each access to `{Colors.something}` calls the same underlying factory, advancing the
shared index. There is no per-key index tracking.

---

## Mode: `markov` (Markov Chain Generation)

### Summary

Generates a new string on each call by training a character-level Markov chain on the
provided items. The same seed always produces the same generated string.

### Factory Constructor

```
markovify(items: list[RenderedStr]) -> (Context) -> str
```

`items` is a list of `RenderedStr` objects (plain string wrappers). They are used as
training data for the Markov chain at factory call time, not at construction time.

### Behavior Contract

1. On each call, construct a `NameGenerator` from `items` with chain length
   `context.get("markov_chainlen", 2)`.
2. Call `get_random_name(start=context.get("start_markov", ""), seed=context["seed"])`.
3. Return the resulting generated string.

### Items Are Training Strings, Not Templates

Items in `markov` mode are converted to `RenderedStr` at parse time. They are treated
as raw training strings for the Markov chain. They are NOT rendered through the
template engine. Template syntax within Markov training items has no special meaning.

### Context Parameters

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `markov_chainlen` | int | `2` | Length of Markov chain prefix. See 07-markov-chain.md for valid range. |
| `start_markov` | string | `""` | Optional starting characters for generation. |

### State

None in the factory closure. The `NameGenerator` is reconstructed on every factory
call.

### Determinism

With the same seed and the same `items`, the same name is always generated. The seed
is the sole source of randomness.

### YAML Example

```yaml
NamesMarkov:
  male:
    - mode: markov
    - Noah
    - Liam
    - William
    - Mason
    - James
```

Each access to `{NamesMarkov.male}` generates a plausible new name derived from the
character patterns of the source list. With the same seed, the same name is generated.

### Full Behavior Specification

See [07-markov-chain.md](07-markov-chain.md) for the complete algorithm specification,
including training, generation, valid chain lengths, and normative test vectors.

---

## Mode: `list` (Ordered List Access)

### Summary

Presents an ordered, immutable list of rendered strings for indexed access. No
selection occurs. The full list is accessible by integer index. This mode does NOT
wrap its result in a `Database`.

### Constructor

```
Datalist(grammar_path, context, items: list[RenderedStr])
```

`items` is a list of `RenderedStr` objects. The `Datalist` is returned directly from
`parse_value` — there is no `Database` wrapper.

### Behavior Contract

1. Items are stored in the order they appear in the YAML, after the mode-setting
   element is consumed.
2. Items are accessible by zero-based integer index.
3. If an item is a TextRule, it is rendered via `item.render(context)` at access time.
   Otherwise the item is returned directly.
4. The list order is preserved. No randomization occurs.
5. `context["seed"]` is not used for selection (though it may be used internally if
   an item is a TextRule that references other rules).

### Template Access Syntax

Template expressions MUST use integer index access:

```
{Steps[0]}   → first item
{Steps[1]}   → second item
{Steps[2]}   → third item
```

Attribute-style access (`{Steps.something}`) is not supported for `Datalist` and
produces undefined behavior.

### Items Are Not Recursively Parsed

Items in `list` mode are converted to `RenderedStr` at parse time, not passed through
`parse_value`. Template syntax within list items has no special meaning and is not
expanded.

### State

None. The list is immutable after construction.

### Lifecycle

The `Datalist` is constructed once at parse time. It is not recreated between
accesses within a render pass. Because items are `RenderedStr` objects (not
`RenderableText`), they are fixed strings that do not change between accesses.

### Edge Cases

| Condition | Behavior |
|-----------|----------|
| Index out of range | `IndexError` — propagate to caller |
| Empty list | `IndexError` on any access |

### YAML Example

```yaml
Steps:
  - mode: list
  - First, gather your materials.
  - Second, prepare the workspace.
  - Third, begin the process.

Begin:
  - "{Steps[0]}\n{Steps[1]}\n{Steps[2]}"
```

`{Steps[0]}` always returns `"First, gather your materials."`. The output is
deterministic and independent of seed.

### Use Case

`list` mode is appropriate when you need ordered, index-addressable access to a
fixed sequence of values — for example, enumerated steps, ordered options in a
menu, or positionally-significant data like days of the week.

---

## Mode Comparison Table

| Property | `reuse` | `pick` | `ratchet` | `markov` | `list` |
|----------|---------|--------|-----------|----------|--------|
| Items parsed via `parse_value` | Yes | Yes | No (RenderedStr) | No (RenderedStr) | No (RenderedStr) |
| Wrapped in `Database` | Yes | Yes | Yes | Yes | No (`Datalist`) |
| Uses `context["seed"]` | Yes | Yes | No | Yes | No |
| Mutates item list | No | Yes | No | No | No |
| Maintains index/counter | No | No | Yes | No | No |
| Allows repetition | Yes | No | Yes (cycles) | Yes | Yes |
| Access pattern | `{Rule}` or `{Rule.key}` | `{Rule}` or `{Rule.key}` | `{Rule}` or `{Rule.key}` | `{Rule}` or `{Rule.key}` | `{Rule[n]}` |
| Generates novel strings | No | No | No | Yes | No |

---

## Conformance Requirements

A conforming implementation MUST:

1. Recognize the mode-setting syntax exactly as described: a single-key map with key
   `"mode"` as the first list element.
2. Treat any first-element map that does not meet all three recognition conditions as
   a data item, not a mode setting.
3. Default to `reuse` mode when no mode-setting element is present.
4. Raise `ConfigurationError` for an unrecognized mode value.
5. For `reuse` and `pick` modes: pass each item through `parse_value` recursively,
   enabling nested lists and maps as items.
6. For `ratchet`, `markov`, and `list` modes: convert each item to `RenderedStr`
   (plain string) without recursive `parse_value` processing.
7. For `ratchet` mode: satisfy the normative test vector (`"red blue green red"` for
   the four-access, three-item cycling grammar given above).
8. For `pick` mode: guarantee that each item is selected at most once per factory
   instance (i.e., per render pass).
9. For `list` mode: return a `Datalist` (or equivalent indexed-access structure)
   directly, without wrapping in a `Database`.
10. For `markov` mode: delegate fully to the algorithm specified in 07-markov-chain.md.
