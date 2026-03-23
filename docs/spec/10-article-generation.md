# 10 — Article Generation

This document specifies the article accessor properties that PrestoPlot exposes on all
rendered string values and unrendered text objects. These properties allow grammar
authors to produce grammatically correct English indefinite articles (`"a"` or `"an"`)
for any generated string without branching logic in the grammar itself.

This document is normative throughout. Any implementation that claims conformance to
the PrestoPlot specification must implement the article accessor behavior described
here, available on the types described in the Availability section.

---

## Overview

When a grammar template references a rule and needs the appropriate indefinite article
for the generated value, it would otherwise require a conditional expression:

```yaml
# Without article accessors — verbose
Begin:
  - "{'an' if Occupation[key][0].lower() in 'aeiou' else 'a'} {Occupation[key]}"
```

Article accessors eliminate this boilerplate. Every rendered string and text object
exposes `.a`, `.an`, `.A`, and `.An` properties, so the template becomes:

```yaml
Begin:
  - "{Occupation.hero.an} {Occupation.hero}"
```

---

## Article Properties [Normative]

All four properties are computed from the same character — the first character of the
string — and differ only in case and the alias relationship.

| Property | Returns | Notes |
|----------|---------|-------|
| `.an` | `"an"` if the first character (lowercased) is in `{a, e, i, o, u}`, else `"a"` | Primary lowercase property |
| `.a` | Identical to `.an` | Alias; both must be supported |
| `.An` | `"An"` if first character (lowercased) is a vowel, else `"A"` | Primary capitalized property |
| `.A` | Identical to `.An` | Alias; both must be supported |

The alias relationships are strict: `.a` and `.an` must always return the same value,
and `.A` and `.An` must always return the same value. Implementations must not make one
a derived computation of the other in a way that could produce different results.

---

## Vowel Set [Normative]

The vowel set is fixed:

```
{ 'a', 'e', 'i', 'o', 'u' }
```

Only these five characters are considered vowels. This is intentional. The
implementation does not handle phonetic edge cases.

### Explicit Non-Cases [Normative]

The following are treated as consonants (article `"a"`) by design:

| Character / Pattern | Example | Article | Reason excluded from vowel set |
|--------------------|---------|---------|-------------------------------|
| `h` | `"hour"` | `"a"` | Silent-h words not detected |
| `y` | `"yttrium"` | `"a"` | y-as-vowel not detected |
| `u` (when sounding like "you") | `"university"` | `"a"` | Long-u words not detected |
| Any digit | `"8-hour shift"` | `"a"` | Digits are not vowel characters |
| Any punctuation | `"(extra)"` | `"a"` | Punctuation is not a vowel character |

These exclusions are normative. A conforming implementation must match the reference
behavior rather than attempt phonetic correctness. Grammar authors who require handling
of these edge cases must use conditional template expressions.

---

## Algorithm [Normative]

To compute the article for a string value `s`:

1. If `s` is empty: behavior is undefined. See the Edge Cases section.
2. Take the first character: `c = s[0]`.
3. Lowercase it: `c_lower = c.lower()` (or locale-independent ASCII lowercasing).
4. If `c_lower` is in `{'a', 'e', 'i', 'o', 'u'}`:
   - `.an` and `.a` return `"an"`.
   - `.An` and `.A` return `"An"`.
5. Otherwise:
   - `.an` and `.a` return `"a"`.
   - `.An` and `.A` return `"A"`.

---

## Edge Cases [Normative]

### Empty String

Accessing any article property on an empty string is **undefined behavior**. The string
has no first character; the algorithm cannot proceed. Conforming implementations may:

- Raise an `IndexError` (or equivalent).
- Return a default value such as `"a"`.

Implementations should document their chosen behavior. Grammar authors must ensure that
any rule accessed for article computation will produce a non-empty string.

### Non-ASCII First Character

Characters outside the ASCII range are treated as consonants. The lowercasing in step 3
of the algorithm must not depend on locale-specific Unicode case folding. Only the five
ASCII vowel characters `a`, `e`, `i`, `o`, `u` (in both cases: `A`, `E`, `I`, `O`,
`U`) trigger the `"an"` article.

---

## Availability [Normative]

Article properties must be available on the following types:

### RenderedStr

`RenderedStr` is the string subtype returned by all template engine calls. It wraps an
ordinary string and adds article properties.

**Caching**: article properties on `RenderedStr` are computed at most once and cached.
The first access computes the value; subsequent accesses return the cached value. This
is an optimization; the caching must not be observable to callers (the result is
always the same).

**Implementation**: in the reference implementation, `RenderedStr` subclasses `str` and
uses `functools.cached_property` for `.an` and `.An`. The aliases `.a` and `.A` are
class-level assignments (`a = an`, `A = An`) pointing to the same property object.

### Text and RenderableText

`Text` and `RenderableText` are the unrendered template wrapper objects. They expose
article properties computed from the string coercion of their underlying value
(`str(self.value)`).

**Caching**: the reference implementation stores the computed article in an instance
variable after first access. The property getter checks for the cached value before
recomputing.

### Database (via String Delegation) [Normative]

`Database` objects delegate attribute access to `str(self)` when the attribute name
is not found in the Database's own fields or cache and is not a keyed rule access.
Because `str(database)` returns a `RenderedStr`, and `RenderedStr` has article
properties, accessing `.an`, `.a`, `.An`, or `.A` on a `Database` object works through
this delegation.

The full delegation chain is:

```
{Occupation.hero.an}
  → Database.__getattr__("an")
  → "an" not in cache, not an instance field
  → "an" is an attribute of str (via RenderedStr)
  → return str(database).an
  → RenderedStr("explorer").an
  → "an"
```

---

## Usage in Templates [Normative]

### ftemplate Syntax

Article accessors are accessed as attribute chains following a Database key lookup:

```
{Rule.key.property}
```

Examples:

```
{Person.Protag.a}    → "a" or "an"
{Person.Protag.an}   → identical to .a
{Person.Protag.A}    → "A" or "An"
{Person.Protag.An}   → identical to .A
```

Standalone rule access (without a key) also supports article accessors through string
delegation:

```
{Occupation.an}      → "an" if Occupation's value starts with a vowel, else "a"
```

### Jinja2 Syntax

The same attribute chains work in Jinja2 templates:

```
{{ Person.Protag.a }}
{{ Person.Protag.An }}
{{ Occupation.an }}
```

### Combining Article with Value

The most common usage pattern places the article immediately before the rule value:

```yaml
Begin:
  - "She is {Occupation.hero.an} {Occupation.hero}."
  # Produces: "She is an archaeologist." or "She is a pilot."
```

Or using the direct string form without key scoping:

```yaml
Begin:
  - "She is {Occupation.an} {Occupation}."
```

Note: the second form calls `Occupation` twice. With `reuse` mode and the same base
seed, both calls produce the same value (the seeded RNG is initialized with the same
seed each time). However, if `Occupation` uses `pick` mode, the second call would
consume another item. Key scoping is preferred for correctness:

```yaml
Begin:
  - "She is {Occupation.hero.an} {Occupation.hero}."
  # Both accesses use the cached result for key "hero" — safe with any mode.
```

---

## Worked Examples [Normative]

### Example 1: Vowel-initial word

Input string: `"explorer"`.

1. First character: `"e"`.
2. Lowercased: `"e"`.
3. In vowel set `{a, e, i, o, u}`: yes.
4. Results: `.an` → `"an"`, `.a` → `"an"`, `.An` → `"An"`, `.A` → `"An"`.

Template `"is {Person.Protag.a} {Person.Protag}"` with `Person.Protag = "explorer"`
produces `"is an explorer"`.

This is derived from the normative integration test TC-INT-001, which expects:

```
Our hero, Owenry, is a flashing-eyed, erring explorer, subjected to adverse conditions. He carries a whip.
```

The phrase `"is a flashing-eyed"` arises because `"flashing-eyed"` begins with `"f"`,
a consonant. The phrase `"erring explorer"` does not use an article accessor — the
`Person` rule composes `Physical`, `Status`, and `Occupation` directly.

### Example 2: Consonant-initial word

Input string: `"sword"`.

1. First character: `"s"`.
2. Lowercased: `"s"`.
3. In vowel set: no.
4. Results: `.an` → `"a"`, `.a` → `"a"`, `.An` → `"A"`, `.A` → `"A"`.

Template `"He carries {Weapon.hero.an} {Weapon.hero}"` with `Weapon.hero = "sword"`
produces `"He carries a sword"`.

### Example 3: Uppercase vowel-initial word

Input string: `"Explorer"` (capital E).

1. First character: `"E"`.
2. Lowercased: `"e"`.
3. In vowel set: yes.
4. Results: `.an` → `"an"`, `.An` → `"An"`.

Case of the string's first character does not affect the article computation.

### Example 4: Non-alphabetic first character

Input string: `"3 musketeers"`.

1. First character: `"3"`.
2. Lowercased: `"3"` (digit, no change).
3. In vowel set `{a, e, i, o, u}`: no.
4. Results: `.an` → `"a"`.

---

## Conformance Requirements [Normative]

A conforming implementation MUST:

1. Expose `.an`, `.a`, `.An`, and `.A` properties on all rendered strings (the
   equivalent of `RenderedStr`).
2. Make `.a` and `.an` return identical values for any given string.
3. Make `.A` and `.An` return identical values for any given string.
4. Use the vowel set `{a, e, i, o, u}` exclusively. No other characters are treated
   as vowels.
5. Apply case-insensitive matching by lowercasing the first character before checking
   the vowel set.
6. Expose article properties on unrendered text objects (equivalent to `Text` and
   `RenderableText`) computed from their string representation.
7. Expose article properties on `Database` objects via string delegation so that
   `{Rule.key.an}` works in templates.
8. Return `"An"` (with capital `A`, lowercase `n`) from `.An` and `.A` — not `"AN"`
   or `"an"`.
