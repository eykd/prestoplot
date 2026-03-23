# 11 — Test Specification

This document is the normative test specification for PrestoPlot conformance. It
defines the behavior that all conforming implementations must exhibit, expressed as
Given/When/Then test cases organized by domain area.

---

## Normative Status

Tests marked **[NORMATIVE]** state requirements that every conforming implementation
must satisfy. An implementation that fails any normative test case is non-conforming.

Tests marked **[INFORMATIVE]** describe optional behaviors, implementation-specific
optimizations, or behaviors that depend on implementation choices that the specification
permits to vary. Informative tests are guidance; they are not conformance requirements.

Normative integration tests in section 9 require exact string match against the
provided expected values. The expected values are derived from the normative grammar
files in Appendix A and the normative seed and RNG behavior defined in
`06-seed-and-context.md`. Cross-language implementations must replicate the exact PRNG
algorithm (Mersenne Twister, MT19937) and seeding behavior to pass these tests.

---

## Test Case Format

```
### TC-XXX: Title
**[NORMATIVE]** or **[INFORMATIVE]**

**Given** precondition
**When** action
**Then** expected result
**And** additional expectation
```

---

## 1. Seed and Context

### TC-SEED-001: Auto-generated seed when none provided
**[NORMATIVE]**

**Given** no seed is passed to context creation
**When** `get_context(seed=None)` is called
**Then** `context["seed"]` is a 32-character string composed entirely of lowercase hexadecimal characters (`[0-9a-f]`)
**And** `context["seed"]` is different from a second call to `get_context(seed=None)` with overwhelming probability (the probability of collision is 1/2^128)

### TC-SEED-002: String seed stored verbatim
**[NORMATIVE]**

**Given** the string `"testing"` is passed as seed
**When** `get_context(seed="testing")` is called
**Then** `context["seed"] == "testing"`

### TC-SEED-003: Effective seed without key
**[NORMATIVE]**

**Given** a Context with `seed = "base"` and no `"key"` entry
**When** `get_seed(context)` is called
**Then** the return value is `"base"`

### TC-SEED-004: Effective seed with key
**[NORMATIVE]**

**Given** a Context with `context["seed"] = "base"` and `context["key"] = "hero"`
**When** `get_seed(context)` is called
**Then** the return value is `"base-hero"`
**And** `context["seed"]` is still `"base"` after the call (unmodified)

### TC-SEED-005: Same string seed produces identical output
**[NORMATIVE]**

**Given** a valid grammar module and the string seed `"test_seed"`
**When** `render_story` is called twice with the same module name and seed `"test_seed"`
**Then** both calls produce byte-for-byte identical output strings

### TC-SEED-006: Different seeds produce (typically) different output
**[NORMATIVE]**

**Given** a grammar with at least two alternatives in its `Begin` rule
**When** `render_story` is called with seed `"aaa"` and then with seed `"zzz"`
**Then** the specification does not require the outputs to differ — but different seeds are expected to select different alternatives with high probability across a diverse grammar

### TC-SEED-007: `make_seed` uses MD5 of float string
**[NORMATIVE]**

**Given** an RNG instance that, on its first call to `random()`, returns `0.6394267984578837`
**When** `make_seed(rng)` is called
**Then** the result equals `md5("0.6394267984578837".encode("utf-8")).hexdigest()`
**And** the result is `"a1d4b744e42b3fe5c91b72d32b7e14c1"` (or equivalent MD5 hex digest of that exact string)

### TC-SEED-008: RNG instance seed is consumed across calls
**[NORMATIVE]**

**Given** an RNG instance obtained from `get_rng("foo")` (a stateful seeded RNG)
**When** `render_story` is called with this RNG instance as seed (first call)
**And** `render_story` is called again with the same RNG instance (second call)
**Then** the second call produces different output from the first
**And** this is because the RNG state advanced during the first call, changing the auto-generated seed used for the second call

### TC-SEED-009: `None` seed produces auto-generated 32-char hex seed
**[NORMATIVE]**

**Given** `None` is passed as seed
**When** `get_context(seed=None)` is called
**Then** `context["seed"]` is a string of exactly 32 characters
**And** every character in `context["seed"]` is in `[0-9a-f]`

### TC-SEED-010: Database key scoping is transient
**[NORMATIVE]**

**Given** a Context with `seed = "base"` and a Database wrapping a `choose` factory for rule `Name`
**When** `Name["hero"]` is accessed (key `"hero"`)
**Then** the factory is called with effective seed `"base-hero"` (i.e., `context["seed"]` is `"base-hero"` during the factory call)
**And** after the factory call returns, `context["seed"]` is restored to `"base"`
**And** `context.get("key")` is absent (or restored to its previous value) after the call

---

## 2. Article Generation

### TC-ART-001: Vowel-initial string gets "an"
**[NORMATIVE]**

**Given** the rendered string `"explorer"`
**When** `.an` is accessed
**Then** the return value is `"an"`

### TC-ART-002: Consonant-initial string gets "a"
**[NORMATIVE]**

**Given** the rendered string `"sword"`
**When** `.a` is accessed
**Then** the return value is `"a"`

### TC-ART-003: Uppercase vowel-initial gets "an"
**[NORMATIVE]**

**Given** the rendered string `"Explorer"` (capital `E`)
**When** `.an` is accessed
**Then** the return value is `"an"`
**And** the first character is lowercased before the vowel check

### TC-ART-004: `.a` is an alias for `.an`
**[NORMATIVE]**

**Given** any rendered string
**When** both `.a` and `.an` are accessed
**Then** both return the same value

### TC-ART-005: `.An` returns the capitalized form of the article
**[NORMATIVE]**

**Given** the rendered string `"explorer"`
**When** `.An` is accessed
**Then** the return value is `"An"`

### TC-ART-006: `.A` is an alias for `.An`
**[NORMATIVE]**

**Given** any rendered string
**When** both `.A` and `.An` are accessed
**Then** both return the same value

### TC-ART-007: All five ASCII vowels are recognized
**[NORMATIVE]**

**Given** rendered strings beginning with each of: `"a"`, `"e"`, `"i"`, `"o"`, `"u"` and their uppercase equivalents `"A"`, `"E"`, `"I"`, `"O"`, `"U"`
**When** `.an` is accessed on each
**Then** all ten return `"an"`

### TC-ART-008: Article properties on `Text` objects
**[NORMATIVE]**

**Given** a `Text` (or `RenderableText`) object whose underlying value is `"apple"`
**When** `.an` is accessed
**Then** the return value is `"an"`

### TC-ART-009: Article properties on `Database` via string delegation
**[NORMATIVE]**

**Given** a `Database` whose string coercion (`str(database)`) produces the rendered string `"orange"`
**When** `.an` is accessed on the `Database` object directly
**Then** the return value is `"an"` (delegated to `str(database).an`)

### TC-ART-010: Non-alphabetic first character gets "a"
**[NORMATIVE]**

**Given** the rendered string `"3 blind mice"`
**When** `.a` is accessed
**Then** the return value is `"a"`
**And** the digit `"3"` is not in the vowel set

---

## 3. Selection Modes

### TC-MODE-001: Reuse mode — same seed, same result
**[NORMATIVE]**

**Given** a ListRule with mode `reuse` and items `["red", "blue", "green"]`
**When** the rule is evaluated twice with identical Context (same seed, no key)
**Then** both evaluations return the same item
**And** the item list is unmodified after both calls

### TC-MODE-002: Reuse mode — does not deplete the list
**[NORMATIVE]**

**Given** a ListRule with mode `reuse` and items `["a"]` (one item)
**When** the Database is evaluated 100 times (with any seed)
**Then** `"a"` is returned all 100 times
**And** no error occurs

### TC-MODE-003: Pick mode — different keys yield different items
**[NORMATIVE]**

**Given** a ListRule with mode `pick` and items `["x", "y", "z"]`
**When** the Database is accessed with key `"first"` and then with key `"second"` in the same render pass
**Then** the two returned items are distinct members of the original list
**And** together they represent exactly two of the three original items

### TC-MODE-004: Pick mode — last remaining item requires no RNG call
**[NORMATIVE]**

**Given** a ListRule with mode `pick` where all but one item have been consumed by prior accesses
**When** the Database's factory is called one more time
**Then** the last remaining item is returned
**And** no random selection is performed (index is unconditionally 0)

### TC-MODE-005: Ratchet — cycles through items in order
**[NORMATIVE]**

**Given** a grammar with:
```yaml
Colors:
  - mode: ratchet
  - red
  - blue
  - green
Begin:
  - "{Colors.first} {Colors.second} {Colors.third} {Colors.fourth}"
```
**When** `render_story` is called with any seed
**Then** the result is exactly `"red blue green red"`

### TC-MODE-006: Ratchet — state resets between `render_story` calls
**[NORMATIVE]**

**Given** the `test_ratchet` grammar (see Appendix A) and three different seeds
**When** `render_story` is called three times, once with each seed
**Then** all three calls return `"red blue green red"`
**And** the ratchet index always starts at 0 for each new render pass

### TC-MODE-007: Ratchet — ignores seed
**[NORMATIVE]**

**Given** a grammar with a ratchet Database
**When** the ratchet factory is called with different seeds in separate render passes
**Then** the order of returned items is identical across all calls (seed has no effect on ratchet ordering)

### TC-MODE-008: Ratchet — empty list returns empty string
**[NORMATIVE]**

**Given** a ListRule with mode `ratchet` and an empty item list (after mode element is removed)
**When** the factory is called
**Then** the return value is `""`
**And** no error is raised

### TC-MODE-009: Markov — same seed yields same name
**[NORMATIVE]**

**Given** a ListRule with mode `markov` and a non-empty list of training strings
**When** the factory is called twice with identical seed and `markov_chainlen`
**Then** both calls return the same generated string

### TC-MODE-010: Markov — `markov_chainlen` context parameter is used
**[NORMATIVE]**

**Given** a ListRule with mode `markov` and `context["markov_chainlen"] = 3`
**When** the factory is called
**Then** the `NameGenerator` is constructed with chain length 3

### TC-MODE-011: List mode — index access returns items in order
**[NORMATIVE]**

**Given** a ListRule with mode `list` and items `["first", "second", "third"]`
**When** the Datalist is accessed at index `0`, `1`, and `2` respectively
**Then** the results are `"first"`, `"second"`, and `"third"` in order
**And** no random selection occurs

### TC-MODE-012: Mode element is consumed from item list
**[NORMATIVE]**

**Given** a YAML list `[{mode: pick}, apple, banana]`
**When** the list is parsed
**Then** the resulting Database's item list contains exactly `["apple", "banana"]`
**And** the `{mode: pick}` element is not present in the item list

### TC-MODE-013: Non-mode single-key map is a data item
**[NORMATIVE]**

**Given** a YAML list `[{label: hello}, apple]`
**When** the list is parsed
**Then** `{label: hello}` is treated as a data item (not a mode-setting element)
**And** the resulting Database's item list has two items: `{label: hello}` and `"apple"`
**And** the mode defaults to `reuse`

---

## 4. Grammar Parsing

### TC-GRAM-001: Simplest valid grammar
**[NORMATIVE]**

**Given** a module containing `Begin: ["Hello, World!"]` and nothing else
**When** `render_story` is called
**Then** the result is `"Hello, World!"`

### TC-GRAM-002: Include directive merges rules
**[NORMATIVE]**

**Given** module `A` with `include: [B]` and one rule `Start: ["go"]`
**And** module `B` with rule `Name: ["Alice"]`
**When** module `A` is parsed
**Then** the Context contains both `Start` and `Name`
**And** `{Name}` resolves to `"Alice"` in templates rendered from module `A`

### TC-GRAM-003: Include cycle is silently skipped
**[NORMATIVE]**

**Given** module `A` with `include: [B]` and module `B` with `include: [A]`
**When** module `A` is parsed
**Then** no infinite recursion or stack overflow occurs
**And** each module is processed at most once per parse pass

### TC-GRAM-004: `render: jinja2` selects Jinja2 engine
**[NORMATIVE]**

**Given** a module with `render: jinja2` and a text rule using `{{ variable }}` syntax
**When** the text rule is rendered
**Then** the Jinja2 engine evaluates the `{{ }}` expression
**And** the ftemplate engine is not used

### TC-GRAM-005: Default render strategy is ftemplate
**[NORMATIVE]**

**Given** a module with no `render` key and a text rule using `{variable}` syntax
**When** the text rule is rendered
**Then** the ftemplate engine evaluates the `{}` expression
**And** the result is the string coercion of the named Context entry

### TC-GRAM-006: Unknown render strategy raises an error
**[NORMATIVE]**

**Given** a module with `render: totally_unknown_engine`
**When** the module is parsed
**Then** a configuration error (or equivalent) is raised before rendering begins

### TC-GRAM-007: Text values are dedented and stripped
**[NORMATIVE]**

**Given** a TextRule that contains leading whitespace due to YAML block scalar indentation (e.g., using `>` or `|`)
**When** the value is stored in the Context
**Then** common leading indentation is removed from all lines (dedent)
**And** leading and trailing whitespace is stripped from the resulting string

### TC-GRAM-008: Dict value becomes Databag
**[NORMATIVE]**

**Given** a YAML module with the rule `Names: {male: [Noah], female: [Emma]}`
**When** parsed
**Then** `Names` in the Context is a Databag (StructRule)
**And** `Names["male"]` returns a Database whose factory yields `"Noah"` with any seed
**And** `Names["female"]` returns a different Database whose factory yields `"Emma"` with any seed

### TC-GRAM-009: Boolean YAML value passes through unchanged
**[NORMATIVE]**

**Given** a rule with value `true` (YAML boolean)
**When** parsed
**Then** the Context entry is the boolean value `true` (not the string `"true"`)
**And** it is accessible in template expressions as a boolean

### TC-GRAM-010: Module data is consumed during parsing
**[NORMATIVE]**

**Given** a module with `include`, `render`, and rule keys
**When** `parse_grammar_file` completes
**Then** the `include` and `render` keys have been removed from the raw module data (they were popped by the parser)
**And** only the rule keys remain in the raw data map
**And** this does not affect subsequent calls to `resolve_module` because each call returns a fresh copy

---

## 5. Storage

### TC-STOR-001: FileStorage resolves an existing module
**[NORMATIVE]**

**Given** a directory containing `greet.yaml` with content `{Begin: [Hello]}`
**When** `resolve_module("greet")` is called on a `FileStorage` pointing to that directory
**Then** the return value is a dict with key `"Begin"` containing `["Hello"]`

### TC-STOR-002: FileStorage raises ModuleNotFoundError for missing module
**[NORMATIVE]**

**Given** a directory that does not contain `missing.yaml`
**When** `resolve_module("missing")` is called
**Then** `ModuleNotFoundError` (or the implementation's equivalent) is raised
**And** the exception carries the module name `"missing"`

### TC-STOR-003: FileStorage lists modules alphabetically
**[NORMATIVE]**

**Given** a directory with `zebra.yaml`, `apple.yaml`, and `mango.yaml`
**When** `list_modules()` is called
**Then** the return value is `["apple", "mango", "zebra"]` (sorted, no extensions)

### TC-STOR-004: `resolve_module` returns a mutable independent copy
**[NORMATIVE]**

**Given** any storage adapter
**When** `resolve_module("greet")` is called and the returned dict is mutated (e.g., a key is deleted)
**Then** a second call to `resolve_module("greet")` returns the original dict with the deleted key present
**And** the mutation of the first return value did not affect the stored data

### TC-STOR-005: CachedFileStorage returns equivalent data to FileStorage
**[INFORMATIVE]**

**Given** a `CachedFileStorage` and a `FileStorage` both pointing to the same directory
**When** `resolve_module` is called on each with the same module name
**Then** the return values are structurally equal (same keys and values)

### TC-STOR-006: CompilingFileStorage creates a cache file on first access
**[INFORMATIVE]**

**Given** a `CompilingFileStorage` pointing to a directory with `scene.yaml` and no `scene.mp`
**When** `resolve_module("scene")` is called
**Then** a file named `scene.mp` is created in the same directory
**And** the return value is the same data as `FileStorage.resolve_module("scene")`

### TC-STOR-007: CompilingFileStorage falls back to YAML when cache is corrupted
**[INFORMATIVE]**

**Given** a `CompilingFileStorage` pointing to a directory with `scene.yaml`
**And** a corrupted (truncated or invalid) `scene.mp` file in the same directory
**When** `resolve_module("scene")` is called
**Then** the YAML file is loaded successfully
**And** a new, valid `scene.mp` file is written
**And** the return value matches what `FileStorage` would return

### TC-STOR-008: Empty YAML file returns None
**[NORMATIVE]**

**Given** a storage adapter pointing to a directory with an empty `empty.yaml` file (zero bytes)
**When** `resolve_module("empty")` is called
**Then** the return value is `null` / `None`
**And** no error is raised

---

## 6. Template Engines

### TC-TMPL-001: ftemplate renders a simple variable reference
**[NORMATIVE]**

**Given** the template `"{Name}"` and a Context containing `Name` bound to the string `"Alice"`
**When** rendered with the ftemplate engine
**Then** the result is `"Alice"`

### TC-TMPL-002: ftemplate renders a conditional expression
**[NORMATIVE]**

**Given** the template `"{'she' if Sex == 'female' else 'he'}"` and a Context with `Sex = "female"`
**When** rendered with the ftemplate engine
**Then** the result is `"she"`

### TC-TMPL-003: ftemplate raises on undefined variable
**[NORMATIVE]**

**Given** the template `"{Undefined}"` and a Context that does not contain `Undefined`
**When** rendered with the ftemplate engine
**Then** an error is raised (NameError or equivalent)
**And** the error is logged before being re-raised

### TC-TMPL-004: Jinja2 renders a simple variable reference
**[NORMATIVE]**

**Given** the template `"{{Name}}"` and a Context containing `Name` bound to the string `"Alice"`
**When** rendered with the Jinja2 engine
**Then** the result is `"Alice"`

### TC-TMPL-005: Jinja2 renders an if block
**[NORMATIVE]**

**Given** the template `"{% if Sex == 'female' %}she{% else %}he{% endif %}"` and a Context with `Sex = "male"`
**When** rendered with the Jinja2 engine
**Then** the result is `"he"`

### TC-TMPL-006: Jinja2 undefined variable renders as literal
**[NORMATIVE]**

**Given** the template `"{{Undefined}}"` and a Context that does not contain `Undefined`
**When** rendered with the Jinja2 engine
**Then** the result is the literal string `"{{ Undefined }}"` (DebugUndefined behavior)
**And** no error is raised

### TC-TMPL-007: Jinja2 TemplateError is logged and re-raised
**[NORMATIVE]**

**Given** a Jinja2 template with a syntax error that causes a `TemplateError` at render time
**When** rendered with the Jinja2 engine
**Then** the error is logged, including the template source path
**And** a domain-level error is raised (not swallowed)

### TC-TMPL-008: Template output is a RenderedStr with article properties
**[NORMATIVE]**

**Given** a template that renders to the string `"explorer"`
**When** rendered with either the ftemplate or Jinja2 engine
**Then** the result supports `.a` returning `"an"` and `.an` returning `"an"`
**And** the result is an instance of `RenderedStr` (or equivalent string subtype with article properties)

### TC-TMPL-009: ftemplate renders keyed Database access
**[NORMATIVE]**

**Given** the template `"{Name.hero}"` and a Context with `Name` bound to a `Database`
**When** rendered with the ftemplate engine
**Then** `Name.__getattr__("hero")` is invoked (or equivalent attribute access)
**And** the Database performs key-scoped seed derivation for key `"hero"`

### TC-TMPL-010: Jinja2 renders a filter
**[NORMATIVE]**

**Given** the template `"{{ Name | upper }}"` and a Context with `Name = "alice"`
**When** rendered with the Jinja2 engine
**Then** the result is `"ALICE"`

---

## 7. Database

### TC-DB-001: Database caches factory results by key
**[NORMATIVE]**

**Given** a Database wrapping a `choose` factory
**When** the Database is accessed with key `"hero"` a first time and then a second time
**Then** the factory is called exactly once
**And** both accesses return the same value

### TC-DB-002: Database uses scoped seed for key access
**[NORMATIVE]**

**Given** a Database with base seed `"base"` and a `choose` factory that records the seed it was called with
**When** the Database is accessed with key `"hero"`
**Then** the factory was called with effective seed `"base-hero"` (i.e., `context["seed"]` was `"base-hero"` during the call)

### TC-DB-003: `str(database)` uses unscoped seed
**[NORMATIVE]**

**Given** a Database with base seed `"base"` and a `choose` factory that records the seed it was called with
**When** `str(database)` is called (no key)
**Then** the factory was called with seed `"base"` (no key appended)
**And** the result is not stored in the key cache

### TC-DB-004: Different keys produce independently cached values
**[NORMATIVE]**

**Given** a Database wrapping `choose(["red", "blue", "green"])` with a seed that produces different choices for different scoped seeds
**When** accessed with key `"hero"` and then with key `"villain"` in the same render pass
**Then** both values are independently cached
**And** subsequent accesses to `"hero"` and `"villain"` return their respective cached values

### TC-DB-005: Databag key access renders contained TextRule
**[NORMATIVE]**

**Given** a Databag containing a TextRule stored under key `"male"`
**When** `databag["male"]` is accessed
**Then** the TextRule is rendered in the current Context
**And** the return value is a string (or RenderedStr)

### TC-DB-006: Databag missing key raises KeyError
**[NORMATIVE]**

**Given** a Databag that does not contain the key `"missing"`
**When** `databag["missing"]` is accessed
**Then** a `KeyError` is raised

### TC-DB-007: Datalist index access returns the item at that index
**[NORMATIVE]**

**Given** a Datalist with items `["first", "second"]`
**When** `datalist[0]` is accessed
**Then** the return value is `"first"`
**And** `datalist[1]` returns `"second"`

### TC-DB-008: Database delegates string methods via `str(self)`
**[NORMATIVE]**

**Given** a Database whose string coercion produces `"hello"`
**When** `.upper()` is invoked on the Database object
**Then** the return value is `"HELLO"`
**And** this is achieved by delegating to `str(database).upper()`

### TC-DB-009: Pick factory removes items on each call
**[NORMATIVE]**

**Given** a `pick` factory initialized with items `["a", "b", "c"]`
**When** the factory is called three times (with any seeds)
**Then** each call returns a different item
**And** the item list is empty after three calls
**And** a fourth call raises an error (index error or equivalent)

### TC-DB-010: Ratchet factory cycles through items in order
**[NORMATIVE]**

**Given** a `ratchet` factory initialized with items `["x", "y"]`
**When** the factory is called four times
**Then** the results are `"x"`, `"y"`, `"x"`, `"y"` in that order
**And** the cycle continues indefinitely with no error

---

## 8. Markov Chain

### TC-MARKOV-001: NameGenerator builds chain from corpus
**[NORMATIVE]**

**Given** `NameGenerator(["Noah", "Liam"], chainlen=2)`
**When** the generator is constructed
**Then** the Markov chain contains prefix `"  "` (two spaces, representing the start-of-name boundary) with at least one suffix entry
**And** the chain contains prefix `"No"` with suffix `"a"` (from `"Noah"`)
**And** the chain contains prefix `"Li"` with suffix `"a"` (from `"Liam"`)

### TC-MARKOV-002: `get_random_name` is deterministic with same seed
**[NORMATIVE]**

**Given** a `NameGenerator` constructed from a fixed corpus and a fixed `chainlen`
**When** `get_random_name(seed="foo")` is called twice on the same generator
**Then** both calls return the same generated name

### TC-MARKOV-003: `get_random_name` respects `max_length`
**[NORMATIVE]**

**Given** a `NameGenerator` and `max_length=5`
**When** `get_random_name(max_length=5, seed="any")` is called
**Then** the returned string has at most 5 characters (not counting any trailing newline stripped during generation)

### TC-MARKOV-004: `chainlen` out of range raises ValueError
**[NORMATIVE]**

**Given** `chainlen=0` or `chainlen=11`
**When** `NameGenerator` is constructed with that chain length
**Then** a `ValueError` is raised

### TC-MARKOV-005: Empty `start` string uses space prefix
**[NORMATIVE]**

**Given** a `NameGenerator` with `chainlen=2` and `start=""`
**When** `get_random_name(start="")` is called
**Then** the initial Markov prefix is `"  "` (two spaces, representing the start boundary)
**And** the generated name starts from the beginning of the chain

### TC-MARKOV-006: Dash character is skipped during generation
**[NORMATIVE]**

**Given** a `NameGenerator` whose chain contains `"-"` as a possible suffix for some prefix
**When** generation encounters that prefix and selects `"-"` as the next character
**Then** the `"-"` is discarded and generation attempts the next suffix (or reseeds)
**And** the generated name does not contain `"-"`

### TC-MARKOV-007: Newline character terminates generation
**[NORMATIVE]**

**Given** a trained `NameGenerator`
**When** generation encounters the newline character `"\n"` as a suffix
**Then** generation stops immediately
**And** the name returned does not include the `"\n"` character

### TC-MARKOV-008: Normative test vector — "Owenry" from seed "testing"
**[NORMATIVE]**

**Given** the 43-name male corpus from `names.yaml` (see Appendix A), specifically the `NamesMarkov.male` list
**And** `chainlen=2` (the default)
**And** the `characters` grammar rendered with seed `"testing"`
**And** the key `"Protag"` applied to `Name` (resulting in effective seed `"testing-Protag"`)
**When** the Markov name generator is invoked for `NamesMarkov[Sex["Protag"]]["Protag"]` which is `NamesMarkov["male"]["Protag"]`
**Then** the generated name is `"Owenry"`

This test vector verifies that the full chain — MD5 seed generation, MT19937 PRNG,
Markov chain training, and character-level generation — matches the reference
implementation exactly.

---

## 9. Integration Tests

### TC-INT-001: `characters` grammar with seed `"testing"`
**[NORMATIVE]**

**Given** the `characters` module (which includes `names`) as defined in Appendix A
**And** seed `"testing"`
**When** `render_story(storage, "characters", seed="testing")` is called
**Then** the result is exactly:
```
Our hero, Owenry, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip.
```

### TC-INT-002: `characters_jinja` grammar with seed `"testing"`
**[NORMATIVE]**

**Given** the `characters_jinja` module (which includes `names`, uses Jinja2 rendering) as defined in Appendix A
**And** seed `"testing"`
**When** `render_story(storage, "characters_jinja", seed="testing")` is called
**Then** the result is exactly:
```
Our hero, Noah, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip.
```

Note: `characters_jinja` uses `Names[Sex[key]][key]` (traditional name lists) rather
than `NamesMarkov` (Markov generation). This is why the name is `"Noah"` rather than
`"Owenry"`.

### TC-INT-003: `test_ratchet` grammar with seed `"test"`
**[NORMATIVE]**

**Given** the `test_ratchet` module as defined in Appendix A
**And** seed `"test"`
**When** `render_story(storage, "test_ratchet", seed="test")` is called
**Then** the result is exactly `"red blue green red"`

### TC-INT-004: Seeded RNG produces consistent sequence across two calls
**[NORMATIVE]**

**Given** an RNG instance obtained from `get_rng("foo")` and the `characters` grammar
**When** `render_story(storage, "characters", seed=rng)` is called a first time with this RNG instance
**Then** the result is exactly:
```
Our hero, Carter, is a lithe, married scientist, subjected to adverse conditions. He carries a whip.
```
**When** `render_story(storage, "characters", seed=rng)` is called a second time with the same RNG instance (state advanced)
**Then** the result is exactly:
```
Our heroine, Avery, is a superbly fit, rifle-wielding millionaire, swayed by pretense. She carries a rifle.
```

### TC-INT-005: Ratchet state resets across `render_story` calls
**[NORMATIVE]**

**Given** the `test_ratchet` grammar and three arbitrary seeds (e.g., `"a"`, `"b"`, `"c"`)
**When** `render_story` is called three times, once with each seed
**Then** all three calls return `"red blue green red"`
**And** each call produces a fresh parse with a fresh ratchet index starting at `0`

---

## 10. CLI Acceptance Tests

### TC-CLI-001: Basic grammar execution succeeds
**[NORMATIVE]**

**Given** a YAML grammar file containing `Begin: ["Hello, World!"]`
**When** `presto run <file>` is executed
**Then** stdout contains `"Hello, World!"`
**And** the process exits with code `0`

### TC-CLI-002: `--seed` produces deterministic output
**[NORMATIVE]**

**Given** a grammar file with multiple alternatives in `Begin`
**When** `presto run <file> --seed test_seed` is executed twice
**Then** stdout is byte-for-byte identical for both runs

### TC-CLI-003: `--count` produces multiple results separated by `---`
**[NORMATIVE]**

**Given** a grammar file
**When** `presto run <file> --count 3` is executed
**Then** stdout contains exactly two occurrences of `\n---\n` (the three results are separated by `\n---\n`)

### TC-CLI-004: `--markov-start` length validation fails when too short
**[NORMATIVE]**

**Given** `--markov-start "A"` (length 1) and `--markov-chainlen 3`
**When** `presto run <file> --markov-start A --markov-chainlen 3` is executed
**Then** the process exits with a non-zero exit code before generating any output
**And** an error message is written to stderr (or stdout) describing the length constraint violation

### TC-CLI-005: `--markov-start` constrains generated name prefix
**[NORMATIVE]**

**Given** a grammar using `mode: markov` and the flags `--markov-start Jo --markov-chainlen 2`
**When** `presto run <file> --markov-start Jo --markov-chainlen 2` is executed
**Then** the generated Markov name begins with `"Jo"`

### TC-CLI-006: Non-existent grammar file exits with error
**[NORMATIVE]**

**Given** a path to a YAML file that does not exist on the filesystem
**When** `presto run <nonexistent_path>` is executed
**Then** the process exits with a non-zero exit code
**And** an error message is displayed describing the missing file
