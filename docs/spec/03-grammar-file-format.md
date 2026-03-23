# 03 — Grammar File Format

This document is the normative reference for the YAML grammar file format used by
PrestoPlot. A grammar file describes a **module**: a named collection of rules that
the generation engine uses to produce text.

Any conforming implementation must parse grammar files exactly as specified here to
guarantee compatibility with existing grammar libraries.

---

## Overview

A grammar file is a YAML 1.1 document. The file encodes a single module. The
top-level value must be a YAML mapping (dictionary). Each key in the mapping is
either a **special key** (with processing semantics) or a **rule name** (whose
value defines what the rule produces).

**File naming:** The module name is the file stem — the filename without the `.yaml`
extension. Storage adapters use module names as lookup keys, not file paths.

Examples:

| File             | Module name    |
|------------------|----------------|
| `names.yaml`     | `names`        |
| `characters.yaml`| `characters`   |

---

## Special Top-Level Keys

Special keys are processed before rule definitions. They are **consumed** (removed
from the data map) during parsing and do not appear as rules in the context.

### `include`

_(Optional)_

```yaml
include:
  - module-name-one
  - module-name-two
```

**Value:** A YAML sequence of module name strings (without `.yaml` extension).

**Semantics:** Before processing this module's own rules, the parser loads each
listed module in order and merges its rules into the current rendering context.
Cycles are silently broken: if a module name has already been visited in the current
load chain, it is skipped.

**Ordering:** Rules from earlier includes can be overridden by rules from later
includes, and all included rules can be overridden by the current module's own rules.
This is because parsing proceeds in order: includes first, then current module.

**Example:**

```yaml
include:
  - names
  - locations
```

This loads `names.yaml` and `locations.yaml` before processing the current file.

---

### `render`

_(Optional; default: `ftemplate`)_

```yaml
render: jinja2
```

**Value:** One of the following strings:

| Value       | Engine                          |
|-------------|---------------------------------|
| `ftemplate` | f-string-style template engine  |
| `jinja2`    | Jinja2 template engine          |
| `jinja`     | Alias for `jinja2`              |

**Semantics:** Selects the template engine used to render all TextRules defined in
this module. Included modules retain whatever render strategy they declared; the
current module's `render` setting applies only to the rules defined in this file.

**Error:** Any value other than the three listed above is a configuration error and
must cause the parser to raise an error before generating any output.

---

## Rule Values

Each non-special top-level key defines a named rule. The type of the YAML value
determines the rule type.

### String Value — TextRule

```yaml
Greeting: "Hello, {Name}!"
```

A YAML scalar string value creates a **TextRule**. The string is a template that is
evaluated lazily, using the module's configured render strategy, when the rule is
referenced during generation.

**Whitespace normalisation** is applied before storage (see [Text Whitespace
Normalisation](#text-whitespace-normalisation)).

---

### List Value — ListRule (Database)

```yaml
Colors:
  - red
  - blue
  - green
```

A YAML sequence creates a **ListRule**, backed by a **Database** that holds a
selection function over the items. The default selection mode is `reuse` (random
selection with replacement).

Each item in the list is itself a value and is parsed recursively: items may be
strings (TextRules), maps (Databags), or even nested lists (though nesting lists
inside lists is unusual).

See [Mode Detection in Lists](#mode-detection-in-lists) for how the first element
may override the default selection mode.

---

### Map/Dict Value — StructRule (Databag)

```yaml
Names:
  male:
    - Noah
    - Liam
  female:
    - Emma
    - Olivia
```

A YAML mapping value creates a **StructRule**, backed by a **Databag**. A Databag
is a dictionary-like container whose values are themselves parsed rules. Keys are
strings; values may be any rule type (list, string, or nested map).

Databag values support both key and attribute access syntax. In ftemplate mode:

```
{Names[Sex[key]][key]}
```

In Jinja2 mode:

```
{{Names[Sex[key]][key]}}
```

---

### Boolean Value — Pass-through

```yaml
IsEnabled: true
```

A YAML boolean (`true` / `false`) is stored in the context as-is and is available
in templates. It is **not** wrapped in any container type.

---

## Mode Detection in Lists

The **first element** of a list value may be a mode-specifier that controls how the
remaining items are selected. A mode-specifier is recognised by the following rules:

1. The first element must be a YAML mapping (not a string or list).
2. That mapping must have **exactly one key**.
3. That key must be `mode`.
4. Multi-key maps or maps whose single key is not `mode` are treated as ordinary
   data items (Databags), not mode specifiers.

When a mode-specifier is detected, it is **consumed** (removed from the item list)
before the items are processed. The remaining elements become the candidates for
selection.

### Valid Modes

| Mode      | Semantics                                                                                       |
|-----------|-------------------------------------------------------------------------------------------------|
| `reuse`   | **(Default)** Random selection with replacement. Each reference to the rule picks independently from the full item list. |
| `pick`    | Random selection without replacement. Each access removes an item from the candidate list. Once all items have been picked, the list is exhausted. |
| `ratchet` | Sequential selection. Returns items in order: first access returns item 0, second returns item 1, etc. Wraps back to item 0 when the list is exhausted. Does not depend on the RNG. |
| `markov`  | Markov chain generation. Builds a character-level Markov model from the item strings and generates novel strings matching the statistical patterns. Items must be strings. |
| `list`    | Returns all items as an ordered list (a Datalist) rather than selecting from them.             |

**Example:**

```yaml
Weapon:
  - mode: pick
  - sword
  - pistol
  - laser
```

---

## Text Whitespace Normalisation

Before a TextRule template string is stored, the following normalisation steps are
applied:

1. **Dedent:** Remove the common leading whitespace prefix shared by all lines
   (equivalent to Python's `textwrap.dedent`).
2. **Strip:** Remove all leading and trailing whitespace from the resulting string.

These steps are applied to the string value after YAML parsing. YAML block scalars
are therefore processed by the YAML parser first, and normalisation applies to the
resulting string.

**Practical consequences:**

- A YAML folded scalar (`>`): YAML collapses newlines into spaces and strips the
  trailing newline, producing a single line. Normalisation then strips any surrounding
  whitespace. This is the idiomatic way to write long single-line templates:

  ```yaml
  Description:
    - >
      Our {hero.Protag}, {Name.Protag}, is {Person.Protag.a} {Person.Protag}.
  ```

- A YAML literal scalar (`|`): YAML preserves internal newlines. Normalisation
  strips leading/trailing whitespace only, leaving embedded newlines intact. Use
  this for multi-line template output.

---

## Template Syntax: ftemplate Mode

The `ftemplate` engine evaluates template strings using Python f-string–style
expression syntax. Single curly braces delimit expressions.

### Simple Variable Substitution

```
{RuleName}
```

Evaluates the named rule from the rendering context and substitutes its string
representation. If `RuleName` refers to a Database (ListRule), a value is selected
according to the rule's mode and the current seed.

**Example:**

```yaml
Begin:
  - "The treasure is hidden near {Location}."
```

---

### Keyed Access (Scoped Seed)

```
{RuleName.key}
```

Accesses the Database for `RuleName` using the attribute `key`. Internally, the seed
used for selection is scoped as `"{current_seed}-{key}"`. This ensures that the same
key always returns the same value within a single render pass, enabling consistent
cross-references between rules.

**Example:**

```yaml
Description:
  - "{Name.hero} wielded a {Weapon.hero}."
```

Both `Name.hero` and `Weapon.hero` use the same scoped seed derived from `hero`,
but they draw from independent databases (Name and Weapon), so they produce
independently generated values that are consistently associated with the same
character.

---

### Subscript Keyed Access

```
{RuleName[key]}
```

Bracket notation is equivalent to attribute notation for Databases and Databags. Use
bracket notation when the key is itself a dynamic expression.

```
{Names[Sex[key]][key]}
```

Evaluation proceeds inside-out:

1. `Sex[key]` evaluates to a string such as `"male"` or `"female"`.
2. `Names["male"]` (or `Names["female"]`) returns the corresponding sub-Database.
3. That sub-Database is accessed with `[key]`, applying seed scoping.

---

### Conditional Expressions

The full expression language of the host implementation is available inside `{ }`.
In the Python reference implementation, this is a Python expression:

```yaml
hero:
  - "{'heroine' if Sex[key] == 'female' else 'hero'}"
```

The result of the expression is converted to a string.

---

### Article Access

`RenderedString` values expose article properties that select the correct English
indefinite article based on the first character of the rendered value:

| Syntax              | Returns                                                  |
|---------------------|----------------------------------------------------------|
| `{Rule.key.a}`      | `"a"` or `"an"` based on the rendered value of `Rule.key` |
| `{Rule.key.an}`     | Alias for `.a`                                           |
| `{Rule.key.A}`      | Capitalised: `"A"` or `"An"`                            |
| `{Rule.key.An}`     | Alias for `.A`                                           |

**Rule:** if the rendered string begins with a vowel (`a`, `e`, `i`, `o`, `u`,
case-insensitive), the article is `"an"` / `"An"`; otherwise `"a"` / `"A"`.

**Example:**

```yaml
Description:
  - "She is {Person.Protag.an} {Person.Protag}."
```

Could render as `"She is an explorer."` or `"She is a soldier."`.

---

## Template Syntax: Jinja2 Mode

Declare Jinja2 mode at the module level:

```yaml
render: jinja2
```

In Jinja2 mode, the template engine uses standard Jinja2 delimiters:

| Delimiter | Purpose              |
|-----------|----------------------|
| `{{ }}`   | Variable substitution / expression output |
| `{% %}`   | Control flow tags (`if`, `for`, etc.)     |
| `{# #}`   | Comments (not rendered)                   |

### Variable Substitution

```yaml
Begin:
  - "{{Description}}"
```

### Control Flow

```yaml
hero:
  - >
    {% if Sex[key] == 'female' %}heroine{% else %}hero{% endif %}
```

### Subscript Access

Bracket notation works identically to ftemplate mode — keys may be dynamic:

```yaml
Name:
  - >
    {{Names[Sex[key]][key]}}
```

### Undefined Variable Behaviour

The Jinja2 engine is configured with `DebugUndefined`. An undefined variable renders
as the literal string `{{ varname }}` rather than raising an error. This makes
debugging easier: undefined references appear verbatim in the output rather than
causing a crash.

### Filters

Standard Jinja2 filters are available:

```yaml
Shout:
  - "{{Description | upper}}"
```

---

## Full Example: characters.yaml

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
  - tall
  - flashing-eyed
  - supernaturally strong
  - superbly fit
  - lithe
  - well-muscled

Weapon:
  - mode: pick
  - sword
  - pistol
  - laser
  - whip
  - saber
  - rifle

Occupation:
  - mode: pick
  - scientist
  - adventurer
  - explorer
  - archaeologist
  - pilot
  - soldier
  - hunter
  - millionaire
```

This file includes `names.yaml` (which defines `Names` and `NamesMarkov`). The
`Begin` rule delegates to `Description`. `Description` uses keyed access (`.Protag`)
to ensure that `hero`, `Name`, `Person`, `He`, and `Weapon` all refer to the same
character across the sentence. `Status` uses `pick` mode so no adjective is repeated;
`Weapon` likewise.

---

## Full Example: test_ratchet.yaml

```yaml
Begin:
  - "{Colors.first} {Colors.second} {Colors.third} {Colors.fourth}"

Colors:
  - mode: ratchet
  - red
  - blue
  - green
```

**Expected output:** `"red blue green red"`

Explanation: `Colors` uses `ratchet` mode. The four keyed accesses (`.first`,
`.second`, `.third`, `.fourth`) each trigger the ratchet independently because each
key creates a distinct cache entry in the Database. The first access returns `"red"`
(index 0), the second returns `"blue"` (index 1), the third returns `"green"`
(index 2), and the fourth wraps back to `"red"` (index 0 again).

Note: ratchet state is not keyed by the attribute name; the ratchet is a stateful
counter shared across all accesses to the same Database. The keyed attribute names
(`.first`, `.second`, etc.) cause four separate calls into the ratchet factory, which
advances the counter on each call.

---

## Parsing Algorithm Summary

The following pseudocode captures the normative parsing order. Implementations must
follow this order to produce correct results.

```
function parse_grammar_file(storage, module_name, context, visited):
    if module_name in visited:
        return context          # cycle detected — skip silently
    visited.add(module_name)

    doc = storage.resolve_module(module_name)   # mutable copy

    includes = doc.pop("include", [])
    for name in includes:
        context = parse_grammar_file(storage, name, context, visited)

    render_strategy = parse_render_strategy(doc.pop("render", "ftemplate"))

    for key, value in doc.items():
        context[key] = parse_value(value, render_strategy, context)

    return context


function parse_value(value, render_strategy, context):
    if value is a list:
        mode, items = extract_mode(value)   # consumes first element if mode-specifier
        return Database(selection_function(mode, items, render_strategy), context)
    if value is a mapping:
        return Databag({k: parse_value(v, render_strategy, context) for k, v in value})
    if value is a bool:
        return value
    # otherwise: string
    return RenderableText(normalise_whitespace(value), render_strategy, context)


function extract_mode(items):
    if items is non-empty
       and items[0] is a mapping
       and len(items[0]) == 1
       and "mode" in items[0]:
        mode = items.pop(0)["mode"]
    else:
        mode = "reuse"
    return (mode, items)
```
