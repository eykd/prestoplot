# 06 — Seed and Context

This document specifies the determinism system underlying PrestoPlot text generation.
It defines how seeds are generated, resolved, and scoped; how the rendering Context is
structured and mutated; and what guarantees a conforming implementation must provide.
This document is normative throughout.

---

## Overview

PrestoPlot uses a deterministic seed system to ensure reproducible text generation.
Given the same module name, seed string, and user variables, `render_story` always
produces the same output. Determinism is achieved by seeding a pseudo-random number
generator (RNG) from a consistent string value derived from the Context before every
random selection.

Seeds in the PrestoPlot domain are **32-character lowercase hexadecimal strings**
derived by MD5-hashing a floating-point value drawn from an RNG. User-supplied seeds
may be any non-empty string and are used directly without hashing.

The Context is the single mutable map threaded through all parsing and rendering
operations. It holds the current seed, optional key-scoping state, user-supplied
variables, and — after parsing — all named Rule objects. Every random selection reads
the seed from the Context at call time.

---

## Seed Generation Algorithm

### `make_seed(rng)`

Produces a 32-character lowercase hexadecimal string from a single draw of an RNG.

**Inputs**: `rng` — an RNG instance or the global random module.

**Steps**:

1. Draw a float: `r = rng.random()`. This returns a float in the half-open interval
   `[0, 1)`.
2. Convert to string: `s = str(r)`. This uses the host language's default
   floating-point-to-string conversion.
3. UTF-8 encode: `b = s.encode('utf-8')`.
4. Compute MD5 digest: `h = md5(b)`.
5. Return the hex digest: `h.hexdigest()` — exactly 32 lowercase hexadecimal
   characters.

**Normative note on MD5**: MD5 is used for its fixed-length hex output and
wide availability, not for cryptographic security. A conforming implementation must
use the MD5 algorithm as specified. Substituting a different hash function produces
non-conforming auto-generated seeds.

**Cross-language compatibility**: Auto-generated seeds depend on the exact string
representation of the float drawn from the RNG. In the reference implementation this
is Python's `str(float)`, which uses the shortest decimal representation that rounds
back to the same float (e.g., `"0.6394267984578837"`). Implementations in other
languages must either replicate this exact representation or document that their
auto-generated seeds are not compatible with the reference test vectors. User-supplied
string seeds (which bypass `make_seed` entirely) are always cross-language compatible.

---

## Seed Resolution

### `set_seed(context, seed)`

Stores a resolved seed into the Context. Called once during `get_context`.

| Input `seed` value | Stored in `context["seed"]` |
|---|---|
| `None` | `make_seed(global_rng)` — auto-generated, non-deterministic |
| Global random module (unseeded) | `make_seed(global_rng)` — treated the same as `None` |
| RNG instance | `make_seed(rng)` — auto-generated using the provided instance; that instance's state advances by one draw |
| String | The string itself, used verbatim |

### `get_seed(context)`

Computes the **effective seed** for seeding the RNG at selection time. This is called
by selection factories immediately before constructing an RNG.

**Algorithm**:

1. Read `context["seed"]`. If the key is absent, auto-generate a seed via
   `make_seed(global_rng)` and store it in `context["seed"]`.

2. If the stored value is an RNG instance or the global random module, generate a new
   seed from it via `make_seed(rng)` and replace `context["seed"]` with the result.

3. Read `context.get("key")`. If `key` is present and not `None`:
   - Return the scoped seed string `f"{context['seed']}-{context['key']}"`.
   - Do **not** modify `context["seed"]`. The scoped seed is transient.

4. Otherwise, return `context["seed"]` directly.

The value returned by `get_seed` is passed to `get_rng` to construct the RNG for
the current selection.

---

## RNG Construction

### `get_rng(seed)`

Constructs an RNG from a seed value.

| Input `seed` value | Returned RNG |
|---|---|
| `None` | The global random module. Non-deterministic; advances global state. |
| RNG instance | The instance itself, returned unchanged. Stateful. |
| String | A new seeded RNG instance: `Random(seed)`. Deterministic. |

**RNG interface requirements**: the constructed RNG must support:

| Method | Semantics |
|---|---|
| `random()` | Returns a float uniformly distributed in `[0, 1)`. |
| `choice(seq)` | Returns a uniformly random element from a non-empty sequence. |
| `randint(a, b)` | Returns a uniformly random integer in `[a, b]` (both inclusive). |
| `paretovariate(alpha)` | Returns a sample from the Pareto distribution. _(Informative: used for weighted selection in certain adapters; not required by all modes.)_ |

**Seeding semantics (normative)**: the reference implementation uses Python's
`random.Random`, which applies the Mersenne Twister (MT19937) algorithm. The string
seed is passed directly to `Random(seed)`, which Python hashes internally. An
implementation targeting cross-platform test-vector compatibility must replicate this
seeding behavior exactly. Implementations that use a different PRNG algorithm or
different seeding mechanism must document the divergence and cannot claim to pass
normative test vectors that involve seeded selection.

---

## Context Structure

The Context is a single mutable key-value map with string keys and heterogeneous
values. It is created fresh for each `render_story` call and is not reused across
calls.

### Required key

| Key | Type | Description |
|---|---|---|
| `seed` | string | The current base seed. Always present after `get_context` is called. |

### Reserved optional keys

| Key | Type | Default | Description |
|---|---|---|---|
| `key` | string | absent | Present during Database attribute access. Holds the current scope key. See Context Scoping below. |
| `markov_chainlen` | integer | `2` | Chain length for Markov chain generation. Consumed by the `markovify` factory. |
| `start_markov` | string | `""` | Starting character sequence for Markov chain generation. Consumed by the `markovify` factory. |

### User-provided keys

Any keyword arguments passed to `render_story` (or `get_context`) are injected into
the Context before parsing. These are accessible by name in all template expressions.

Example: `render_story(storage, "quest", seed="abc", hero_name="Aldric")` makes
`{hero_name}` evaluate to `"Aldric"` in any template.

### Grammar rule keys

After parsing, the Context accumulates one entry per named Rule in the Grammar and
all transitively included Grammars. Keys are the Rule names as they appear in the
YAML source. Values are `Database`, `Databag`, or `Datalist` objects.

**Key collision policy**: if a user-provided key has the same name as a Grammar rule,
the Grammar rule written during parsing **overwrites** the user-provided value. To
avoid ambiguity, user-provided keys should not share names with Grammar rules.

---

## Context Initialization

### `get_context(seed, **user_vars) -> context`

Creates and returns a fresh Context ready for a render pass.

**Algorithm**:

1. Initialize the Context as a shallow copy of `user_vars`.
2. Call `set_seed(context, seed)` to resolve and store the seed.
3. Return the Context.

**Example**:

```
get_context("testing", hero_name="Aldric")
→ context = {
    "seed": "testing",
    "hero_name": "Aldric"
  }
```

```
get_context(None)
→ context = {
    "seed": "4e3a1f..."   # auto-generated 32-char hex string
  }
```

---

## Context Scoping During Database Attribute Access

When a Database object resolves attribute or key `K`, it temporarily modifies the
Context to scope the seed and record the key. This modification is **always reversed**
after the factory call completes — whether it returns normally or raises an exception.

### Protocol

1. Save current values: `old_seed = context["seed"]`, `old_key = context.get("key")`.
2. Update the Context:
   - `context["seed"] = f"{old_seed}-{K}"`
   - `context["key"] = K`
3. Call `factory(context)`.
4. Restore the Context:
   - `context["seed"] = old_seed`
   - If `old_key` was absent: remove `context["key"]`.
   - If `old_key` was present: `context["key"] = old_key`.
5. Cache and return the result from step 3.

This operation must be implemented as an atomic restore — if the factory raises, the
Context must be restored before the exception propagates. In languages with
`try/finally` or RAII semantics, use the appropriate construct. In the reference
implementation this is a context manager (`contextlib.contextmanager`).

### Worked example

Base seed: `"testing"`, Grammar rule: `Name`, key: `"Protag"`.

| Phase | `context["seed"]` | `context["key"]` |
|---|---|---|
| Before | `"testing"` | absent |
| During factory call | `"testing-Protag"` | `"Protag"` |
| Inside `get_seed` | returns `"testing-Protag"` (key is present) | — |
| After factory returns | `"testing"` | absent (restored) |

The RNG inside the factory is seeded with `"testing-Protag"`. The base seed
`"testing"` is never altered permanently.

---

## Scoped Seed Format

A scoped seed is formed by concatenating:

1. The base seed string.
2. A single ASCII hyphen character (`U+002D`).
3. The key string.

```
scoped_seed = f"{base_seed}-{key}"
```

The hyphen separator is normative. Implementations must use exactly one hyphen between
the base seed and the key. Multiple levels of nesting produce multiple hyphens:

| Base seed | Key | Scoped seed |
|---|---|---|
| `"testing"` | `"Protag"` | `"testing-Protag"` |
| `"abc123def456abc123def456abc123de"` | `"hero"` | `"abc123def456abc123def456abc123de-hero"` |

---

## Key Naming Convention

Keys are strings passed as attribute names on Database objects in template expressions.
They identify semantic roles within a single render pass. By convention, keys use
PascalCase for named roles and lowercase for generic roles:

| Convention | Examples |
|---|---|
| Named roles | `Protag`, `Antag`, `Boss`, `Mentor` |
| Generic roles | `hero`, `villain`, `character1`, `npc` |

Any string is a valid key. The key is appended to the base seed using the scoped seed
format above.

---

## Caching Guarantee

Once a Database has resolved attribute `K` via a factory call, the result is stored in
the Database's `cache` map. Subsequent accesses of attribute `K` on the same Database
instance within the same render pass return the cached value without calling the
factory again.

This guarantees **referential consistency**: the same named entity always produces the
same attribute values within one render pass.

```
# Template: "{Name.Protag} defeated {Name.Protag}'s rival, {Name.Antag}."
#
# First  {Name.Protag} → factory called with seed "testing-Protag" → "Alice"; cached.
# Second {Name.Protag} → cache hit → "Alice" (no factory call).
# First  {Name.Antag}  → factory called with seed "testing-Antag"  → "Bob";  cached.
#
# Result: "Alice defeated Alice's rival, Bob."
```

Caching is per-Database-instance, per-render-pass. A new `render_story` call creates
a new set of Database instances and an empty cache.

---

## Determinism Guarantees

Given identical inputs, `render_story` produces identical output. The inputs that
determine output are:

1. The **module name** (including all transitively included modules).
2. The **seed string** stored in the Context (after resolution).
3. All **user-provided variables** that affect template evaluation.

Determinism holds across:

- Multiple calls in the same process.
- Multiple processes on the same machine.
- Multiple machines with conforming implementations.

Determinism requires all of the following conditions to hold:

| Condition | Normative status |
|---|---|
| MD5 algorithm used for `make_seed` | Normative |
| Exact same PRNG algorithm (Mersenne Twister MT19937) | Normative for cross-implementation compatibility |
| Same seeding behavior: `Random(string)` → same initial state | Normative |
| `random()` and `choice(seq)` produce identical sequences for the same seed | Normative |
| Hyphen separator used in scoped seeds | Normative |

**Non-deterministic inputs**: when `seed=None` is passed, `make_seed` draws from the
global unseeded RNG. Output differs across calls and implementations. This is
intentional and does not violate any conformance requirement.

---

## Summary: Seed Flow Through a Render Pass

The following traces seed handling for `render_story(storage, "quest", seed="testing")`:

```
1. get_context("testing")
   → context = {"seed": "testing"}

2. parse_grammar_file loads "quest.yaml"
   → context gains rules: {Name: Database, Trait: Database, Begin: Database, ...}

3. str(context["Begin"])
   → Begin's factory is called with context (no key scope)
   → get_seed(context) returns "testing"
   → RNG = Random("testing")
   → selects template: "{Name.hero} has the trait of {Trait.hero}."

4. Template evaluation: {Name.hero}
   → Database.__getattr__("hero")
   → context temporarily: {"seed": "testing-hero", "key": "hero"}
   → factory called → get_seed returns "testing-hero" → RNG = Random("testing-hero")
   → selects "Aldric"
   → context restored: {"seed": "testing"}
   → cached: Name.cache["hero"] = "Aldric"

5. Template evaluation: {Trait.hero}
   → Database.__getattr__("hero")
   → context temporarily: {"seed": "testing-hero", "key": "hero"}
   → factory called → RNG = Random("testing-hero")
   → selects "brave"
   → context restored: {"seed": "testing"}
   → cached: Trait.cache["hero"] = "brave"

6. Final output: "Aldric has the trait of brave."
```

Calling `render_story(storage, "quest", seed="testing")` again, in any conforming
implementation, produces `"Aldric has the trait of brave."` identically.
