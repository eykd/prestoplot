# Appendix A — Normative Grammar Examples

This appendix contains the full YAML source of the four grammar files used as
normative references throughout the specification. These files define the expected
behavior for all integration tests in section 9 of `11-test-specification.md`
(TC-INT-001 through TC-INT-005).

---

## Status and Purpose

The grammar files in this appendix are **normative**. Any implementation that claims
conformance to the PrestoPlot specification must produce the exact output strings
specified in TC-INT-001 through TC-INT-005 when given these grammar files and the
stated seeds.

Implementors who do not have access to the Python reference test suite can use the
grammar files in this appendix to set up their own conformance tests. Place all four
files in the same directory, configure storage to point to that directory, and verify
the expected outputs from the integration test cases.

The expected outputs depend on:

1. The exact YAML content of these grammar files (normative).
2. The Mersenne Twister (MT19937) PRNG algorithm seeded with Python's `random.Random`
   semantics (normative for cross-implementation compatibility; see `06-seed-and-context.md`).
3. The MD5-based `make_seed` algorithm (normative; see `06-seed-and-context.md`).
4. The character-level Markov chain algorithm (normative; see `07-markov-chain.md`).

---

## Grammar 1: `names.yaml`

This foundational data grammar provides two top-level rules used by `characters.yaml`
and `characters_jinja.yaml` via their `include` directives. It contains no `Begin`
rule; it is designed exclusively to be included by other grammars.

```yaml
Names:
  male:
    - Noah
    - Liam
    - William
  female:
    - Emma
    - Olivia
    - Ava

NamesMarkov:
  male:
    - mode: markov
    - Noah
    - Liam
    - William
    - Mason
    - James
    - Benjamin
    - Jacob
    - Michael
    - Elijah
    - Ethan
    - Alexander
    - Oliver
    - Daniel
    - Lucas
    - Matthew
    - Aiden
    - Jackson
    - Logan
    - David
    - Joseph
    - Samuel
    - Henry
    - Owen
    - Sebastian
    - Gabriel
    - Carter
    - Jayden
    - John
    - Luke
    - Anthony
    - Isaac
    - Dylan
    - Wyatt
    - Andrew
    - Joshua
    - Christopher
    - Grayson
    - Jack
    - Julian
    - Ryan
    - Jaxon
    - Levi
    - Nathan
  female:
    - Emma
    - Olivia
    - Ava
    - Sophia
    - Isabella
    - Mia
    - Charlotte
    - Abigail
    - Emily
    - Harper
    - Amelia
    - Evelyn
    - Elizabeth
    - Sofia
    - Madison
    - Avery
    - Ella
    - Scarlett
    - Grace
    - Chloe
    - Victoria
    - Riley
    - Aria
    - Lily
    - Aubrey
    - Zoey
    - Penelope
    - Lillian
    - Addison
    - Layla
    - Natalie
```

### Annotations

**[1] `Names` — StructRule (Databag) with small curated lists**

`Names` is a top-level mapping; the parser produces a Databag. Each value (`male`,
`female`) is itself a YAML list, so the parser produces a Database for each sub-rule
using the default `reuse` selection mode.

`Names.male` randomly selects from `["Noah", "Liam", "William"]`. With seed `"testing"` and
key `"Protag"` (effective seed `"testing-Protag"`), it selects `"Noah"`. This is the
value used in TC-INT-002 (`characters_jinja` grammar, which uses `Names` not
`NamesMarkov`).

**[2] `NamesMarkov` — StructRule with Markov-mode sub-lists**

`NamesMarkov` is a mapping of gender keys to `mode: markov` lists. The `mode: markov`
first element causes each list to be parsed as a Markov training corpus rather than a
pool for random selection.

`NamesMarkov.male` contains 43 names. The Markov chain is trained on these at factory
call time (not at parse time) with `chainlen=2` (the default). With effective seed
`"testing-Protag"`, the Markov generator produces `"Owenry"`. This is the name in
TC-INT-001.

`NamesMarkov.female` contains 31 names. With effective seed `"testing-Protag"` applied
to the female corpus, the generator would produce a female-sounding name. In
TC-INT-001, the character's `Sex` is selected as `"male"` by the seed, so
`NamesMarkov["male"]` is used rather than `NamesMarkov["female"]`.

**[3] No `Begin` rule**

`names.yaml` has no `Begin` rule and cannot be rendered directly. It is always used
via `include:` from another grammar. Attempting `render_story(storage, "names")` raises
a key error because `"Begin"` is absent from the Context.

**Test vectors using this grammar:**

TC-INT-001, TC-INT-002, TC-INT-004 (via include from `characters.yaml` and
`characters_jinja.yaml`).

---

## Grammar 2: `characters.yaml`

The main ftemplate integration test grammar. It includes `names.yaml` and uses ftemplate
syntax (`{expression}`) throughout.

```yaml
include:
  - names

Begin:
  - "{Description}"

Description:
  - Our {hero.Protag}, {Name.Protag}, is {Person.Protag.a} {Person.Protag}. {He.Protag} carries a {Weapon.Protag}.

Sex:
  - male
  - female

hero:
  - "{'heroine' if Sex[key] == 'female' else 'hero'}"

Name:
  - >
    {NamesMarkov[Sex[key]][key]}

he:
  - >
    {'she' if Sex[key] == 'female' else 'he'}

He:
  - >
    {'She' if Sex[key] == 'female' else 'He'}

Person:
  - "{Physical[key]}, {Status[key]} {Occupation[key]}, {Motivation}"

Status:
  - mode: pick
  - married
  - lawless
  - erring
  - benevolent
  - resentful
  - subtle
  - normal
  - "{Weapon[key]}-wielding"

Motivation:
  - mode: pick
  - in love
  - of ideals
  - influenced by an obligation
  - subjected to adverse conditions
  - swayed by pretense
  - influenced by the occult and the mysterious

Physical:
  - mode: pick
  - "tall"
  - "flashing-eyed"
  - "supernaturally strong"
  - "superbly fit"
  - "lithe"
  - "well-muscled"

Weapon:
  - mode: pick
  - "sword"
  - "pistol"
  - "laser"
  - "whip"
  - "saber"
  - "rifle"

Occupation:
  - mode: pick
  - "scientist"
  - "adventurer"
  - "explorer"
  - "archaeologist"
  - "pilot"
  - "soldier"
  - "hunter"
  - "millionaire"
```

### Annotations

**[1] `include: [names]`**

Processed before any rule in this file. The parser loads `names.yaml` and merges its
rules (`Names`, `NamesMarkov`) into the Context. `characters.yaml`'s own rules are then
added, potentially overriding any conflicting names (none in this case).

**[2] `Begin: ["{Description}"]`**

A single-item list (mode: `reuse`, defaulted). The sole item is a TextRule template
`{Description}`. Rendering `Begin` evaluates `Description` and returns the result.
This single-level indirection keeps the top-level entry point clean.

**[3] `Description`**

```yaml
Description:
  - Our {hero.Protag}, {Name.Protag}, is {Person.Protag.a} {Person.Protag}. {He.Protag} carries a {Weapon.Protag}.
```

This single template demonstrates several key features simultaneously:

- `{hero.Protag}` — keyed Database access: seed scoped to `"Protag"`, result cached.
  With seed `"testing-Protag"`, `Sex` is evaluated first inside `hero` (see annotation 4),
  selecting `"male"`, and `hero` evaluates the conditional to return `"hero"`.
- `{Name.Protag}` — keyed access; uses cached `Sex["Protag"]` result to index into
  `NamesMarkov`, producing a Markov-generated name.
- `{Person.Protag.a}` — keyed access with article accessor. `Person.Protag` is rendered
  first (producing e.g. `"flashing-eyed, erring explorer, subjected to adverse
  conditions"`), then `.a` returns `"a"` or `"an"` based on the first character.
  Because `Person.Protag` is cached, the subsequent `{Person.Protag}` does not
  re-evaluate the factory.
- `{He.Protag}` — uses cached `Sex["Protag"]` to select pronoun.
- `{Weapon.Protag}` — keyed pick selection; guaranteed distinct from `Status.Protag`'s
  weapon selection if `Status` selected `"{Weapon[key]}-wielding"`.

**[4] `Sex: [male, female]`**

Two-item `reuse` list. With seed `"testing-Protag"`, `Sex` selects `"male"`. This
selection is cached and used by `hero`, `Name`, `he`, `He`, and `Person` whenever they
access `Sex[key]` with key `"Protag"`.

**[5] `hero` — conditional gender word**

```yaml
hero:
  - "{'heroine' if Sex[key] == 'female' else 'hero'}"
```

The `key` variable in the ftemplate expression refers to `context["key"]`, which is set
to the current scope key (e.g., `"Protag"`) during a keyed Database access. `Sex[key]`
accesses the `Sex` Database with the same key, returning the cached `Sex["Protag"]`
value (`"male"` or `"female"`). This conditional returns `"heroine"` for female
characters and `"hero"` for male characters.

**[6] `Name` — Markov name via nested subscript**

```yaml
Name:
  - >
    {NamesMarkov[Sex[key]][key]}
```

This is a nested subscript expression:
1. `Sex[key]` — accesses `Sex` Database with the current scope key; returns `"male"` or `"female"`.
2. `NamesMarkov[result]` — accesses the `NamesMarkov` Databag with the gender string; returns the corresponding Markov Database.
3. `[key]` — accesses the Markov Database with the current scope key; triggers name generation with the scoped seed.

The `>` YAML block scalar folds the multiline string into a single line. After
dedenting and stripping, the stored template is `{NamesMarkov[Sex[key]][key]}`.

**[7] `Person` — composite description using keyed access**

```yaml
Person:
  - "{Physical[key]}, {Status[key]} {Occupation[key]}, {Motivation}"
```

All three attribute accesses (`Physical[key]`, `Status[key]`, `Occupation[key]`) use
the current scope key, ensuring that properties are consistently scoped to the same
character. `Motivation` is accessed without a key (returns `str(Motivation)` using the
base seed), meaning all characters share the same motivation in a single render pass.

**[8] `Status`, `Physical`, `Weapon`, `Occupation`, `Motivation` — pick mode**

All five are `mode: pick` lists. Each item can only be selected once per render pass.
This guarantees uniqueness across characters within a single story. `Status` includes
the template item `"{Weapon[key]}-wielding"`, which references the `Weapon` Database
with the scope key — this item produces compound status strings like
`"whip-wielding"`.

**[9] Normative test vectors for this grammar**

| Seed | Expected output |
|------|----------------|
| `"testing"` | `"Our hero, Owenry, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip."` |
| RNG from `get_rng("foo")`, first call | `"Our hero, Carter, is a lithe, married scientist, subjected to adverse conditions. He carries a whip."` |
| RNG from `get_rng("foo")`, second call | `"Our heroine, Avery, is a superbly fit, rifle-wielding millionaire, swayed by pretense. She carries a rifle."` |

---

## Grammar 3: `characters_jinja.yaml`

The Jinja2 equivalent of `characters.yaml`. It uses `render: jinja2`, `{{ }}` variable
substitution, and `{% if %}` control blocks instead of ftemplate expressions. The
logical structure and rules are identical to `characters.yaml`, except:

1. Template syntax is Jinja2 throughout.
2. `Name` uses `Names[Sex[key]][key]` (selecting from the small curated name lists in
   `names.yaml`) instead of `NamesMarkov[Sex[key]][key]`. This produces traditional
   names rather than Markov-generated names.

```yaml
include:
  - names

render: jinja2

Begin:
  - "{{Description}}"

Description:
  - Our {{hero.Protag}}, {{Name.Protag}}, is {{Person.Protag.a}} {{Person.Protag}}. {{He.Protag}} carries a {{Weapon.Protag}}.

Sex:
  - male
  - female

hero:
  - >
    {% if Sex[key] == 'female' %}heroine{% else %}hero{% endif %}

Name:
  - >
    {{Names[Sex[key]][key]}}

he:
  - >
    {% if Sex[key] == 'female' %}she{% else %}he{% endif %}

He:
  - >
    {% if Sex[key] == 'female' %}She{% else %}He{% endif %}

Person:
  - "{{Physical[key]}}, {{Status[key]}} {{Occupation[key]}}, {{Motivation}}"

Status:
  - mode: pick
  - married
  - lawless
  - erring
  - benevolent
  - resentful
  - subtle
  - normal
  - "{{Weapon[key]}}-wielding"

Motivation:
  - mode: pick
  - in love
  - of ideals
  - influenced by an obligation
  - subjected to adverse conditions
  - swayed by pretense
  - influenced by the occult and the mysterious

Physical:
  - mode: pick
  - "tall"
  - "flashing-eyed"
  - "supernaturally strong"
  - "superbly fit"
  - "lithe"
  - "well-muscled"

Weapon:
  - mode: pick
  - "sword"
  - "pistol"
  - "laser"
  - "whip"
  - "saber"
  - "rifle"

Occupation:
  - mode: pick
  - "scientist"
  - "adventurer"
  - "explorer"
  - "archaeologist"
  - "pilot"
  - "soldier"
  - "hunter"
  - "millionaire"
```

### Annotations

**[1] `render: jinja2`**

This top-level key causes all TextRule templates in this file to be evaluated with the
Jinja2 engine. The `names.yaml` module (which has no `render` key) uses ftemplate for
its own rules; each grammar file's render strategy applies only to its own rules.

**[2] Jinja2 `{{ }}` substitution**

The Jinja2 double-brace syntax replaces ftemplate's single-brace syntax. In YAML,
`{{ }}` within a double-quoted string is passed as literal characters to the YAML
parser and then to Jinja2. Example: `"{{Description}}"` is a Jinja2 template that
evaluates the variable `Description`.

**[3] Jinja2 `{% if %}` blocks in `hero`, `he`, `He`**

```yaml
hero:
  - >
    {% if Sex[key] == 'female' %}heroine{% else %}hero{% endif %}
```

The `>` YAML block scalar allows the Jinja2 block tags to be written on their own line
for readability. After YAML processing and stripping, the stored template is:
`{% if Sex[key] == 'female' %}heroine{% else %}hero{% endif %}`.

The Jinja2 `{% if %}` block produces whitespace-free output when the tag and content
are run together without newlines. This is intentional: the rendered value is either
`"heroine"` or `"hero"` with no surrounding spaces.

**[4] `Name` — curated list access instead of Markov generation**

```yaml
Name:
  - >
    {{Names[Sex[key]][key]}}
```

This uses `Names` (the small curated Databag) rather than `NamesMarkov`. With seed
`"testing"` and key `"Protag"`:
- `Sex["Protag"]` selects `"male"` (same as in `characters.yaml`).
- `Names["male"]` is a three-item `reuse` list: `["Noah", "Liam", "William"]`.
- `Names["male"]["Protag"]` uses effective seed `"testing-Protag"` to select from
  this list, producing `"Noah"`.

This explains the different name in TC-INT-002 (`"Noah"`) versus TC-INT-001
(`"Owenry"`): same seed, same character, but different name-selection mechanism.

**[5] Jinja2 undefined variable behavior**

When a variable referenced in a Jinja2 template is not present in the Context, the
reference implementation renders the literal Jinja2 `DebugUndefined` string
(`"{{ VariableName }}"`) rather than raising an error. This differs from ftemplate,
which raises a `NameError`. Grammar authors should be aware of this difference when
debugging.

**[6] Normative test vector for this grammar**

| Seed | Expected output |
|------|----------------|
| `"testing"` | `"Our hero, Noah, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip."` |

The output is identical to TC-INT-001 except for the name (`"Noah"` vs `"Owenry"`),
because:
- `Sex["Protag"]` selects `"male"` identically (same seed, same `Sex` rule).
- `Physical["Protag"]`, `Status["Protag"]`, `Occupation["Protag"]`, `Motivation`,
  and `Weapon["Protag"]` all use `pick` mode with the same seed, selecting identically.
- Only `Name["Protag"]` differs: `Names["male"]` selects `"Noah"` rather than Markov
  generating `"Owenry"`.

---

## Grammar 4: `test_ratchet.yaml`

A minimal grammar that exercises the `ratchet` selection mode in isolation. It is the
normative reference for TC-INT-003 and TC-INT-005.

```yaml
Begin:
  - "{Colors.first} {Colors.second} {Colors.third} {Colors.fourth}"

Colors:
  - mode: ratchet
  - red
  - blue
  - green
```

### Annotations

**[1] `Colors` — ratchet mode with three items**

The `mode: ratchet` element is consumed during parsing. The item list is `["red",
"blue", "green"]` (three items). The ratchet index starts at `0` for each new render
pass.

**[2] `Begin` — four keyed accesses to `Colors`**

```yaml
Begin:
  - "{Colors.first} {Colors.second} {Colors.third} {Colors.fourth}"
```

The template references `Colors` four times with four different keys: `"first"`,
`"second"`, `"third"`, `"fourth"`. Because the ratchet factory ignores keys and
simply advances its index on each call, the four accesses produce:

| Access | Index before call | Result | Index after call |
|--------|------------------|--------|-----------------|
| `Colors.first` | 0 | `"red"` | 1 |
| `Colors.second` | 1 | `"blue"` | 2 |
| `Colors.third` | 2 | `"green"` | 0 (wraps) |
| `Colors.fourth` | 0 | `"red"` | 1 |

The expected output is `"red blue green red"` for any seed.

**[3] Seed independence**

The ratchet factory does not consult `context["seed"]`. The output `"red blue green
red"` is identical regardless of the seed passed to `render_story`. This is what
TC-INT-003 and TC-INT-005 exploit: the seed `"test"` in TC-INT-003 and any three seeds
in TC-INT-005 all produce the same result.

**[4] State reset between render passes**

The ratchet index is part of the factory closure constructed during `parse_grammar_file`.
Each call to `render_story` triggers a new `parse_grammar_file`, which constructs a
new factory closure with a fresh index starting at `0`. The index does not persist
across `render_story` calls. TC-INT-005 verifies this: three separate `render_story`
calls each independently produce `"red blue green red"`.

**[5] Normative test vector for this grammar**

| Seed | Expected output |
|------|----------------|
| Any (including `"test"`) | `"red blue green red"` |

---

## Cross-Reference: Test Cases and Grammar Files

| Test case | Grammar file(s) | Seed | Expected output |
|-----------|----------------|------|----------------|
| TC-INT-001 | `characters.yaml`, `names.yaml` | `"testing"` | `"Our hero, Owenry, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip."` |
| TC-INT-002 | `characters_jinja.yaml`, `names.yaml` | `"testing"` | `"Our hero, Noah, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip."` |
| TC-INT-003 | `test_ratchet.yaml` | `"test"` | `"red blue green red"` |
| TC-INT-004 (first call) | `characters.yaml`, `names.yaml` | RNG from `get_rng("foo")` | `"Our hero, Carter, is a lithe, married scientist, subjected to adverse conditions. He carries a whip."` |
| TC-INT-004 (second call) | `characters.yaml`, `names.yaml` | Same RNG (advanced) | `"Our heroine, Avery, is a superbly fit, rifle-wielding millionaire, swayed by pretense. She carries a rifle."` |
| TC-INT-005 | `test_ratchet.yaml` | Any (three calls) | `"red blue green red"` (all three) |
| TC-MARKOV-008 | `characters.yaml`, `names.yaml` | `"testing"` (key `"Protag"`) | Markov name `"Owenry"` |

---

## Notes on YAML Encoding

All four grammar files must be encoded as UTF-8. YAML block scalars (`>` for folded,
`|` for literal) are used in `characters.yaml` and `characters_jinja.yaml` to improve
readability of multi-expression templates. The PrestoPlot parser normalizes these
values by dedenting and stripping whitespace before storing the template string.

The files must be parsed with a safe YAML loader. Unsafe YAML constructs (Python
object tags, executable YAML) are not supported.
