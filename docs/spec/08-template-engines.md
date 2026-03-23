# 08 — Template Engines

This document specifies the two template engines supported by PrestoPlot: `ftemplate`
and `jinja2`. Both implement the `TemplateEnginePort` defined in `02-ports-and-adapters.md`.
This document is normative throughout.

---

## Overview

A template engine is responsible for evaluating a template string — a text containing
embedded expressions — against a rendering Context and returning the resulting string.
Template engines in PrestoPlot are driven adapters: they implement a port and may be
replaced by any conforming implementation.

Both engines share the same port contract:

```
render(
  template:    string,
  source_path: string,
  context:     map[string, any]
) → RenderedString
```

The returned value is always a `RenderedString` — a string subtype that carries
article-generation properties. See `10-article-generation.md` for the full
specification of those properties.

---

## TemplateEnginePort

### Parameters

| Parameter | Type | Description |
|---|---|---|
| `template` | string | The template text to evaluate. May contain embedded expressions. |
| `source_path` | string | Identifies the source of the template (e.g., `"characters:Name"`). Used only in error messages; does not affect the output. |
| `context` | map[string, any] | Variable bindings available to the template. Includes the seed, user variables, and all Grammar rules parsed into the current render pass. |

### Return value

A `RenderedString`: a string with the following additional properties:

| Property | Alias | Value |
|---|---|---|
| `.a` | `.an` | `"a"` or `"an"` depending on the first character of the string |
| `.A` | `.An` | `"A"` or `"An"` — the capitalized form of `.a` / `.an` |

See `10-article-generation.md` for the complete article-selection algorithm.

### Error contract

On any rendering failure:

1. Log the error at ERROR level, including: the `source_path`, the `template` string,
   and the exception details.
2. Re-raise the exception (do not swallow it). The caller is responsible for handling
   or propagating the error.

---

## ftemplate Engine

**Identifier**: `ftemplate`

**Default**: yes. When no `render:` key is present in a Grammar file, `ftemplate` is
used.

### Semantics

The template string is treated as the body of a Python f-string. Substrings enclosed
in `{...}` are evaluated as expressions in the rendering Context. All other characters
are included in the output verbatim.

The expression evaluation environment is the Context map: every key in the Context is
available as a name in the expression.

### Expression capabilities

The ftemplate engine must support the following expression forms:

| Form | Example | Semantics |
|---|---|---|
| Variable reference | `{RuleName}` | Coerces `context["RuleName"]` to string. For Database and Databag objects, this triggers selection and rendering. |
| Attribute access | `{RuleName.key}` | Accesses attribute `key` on the object at `context["RuleName"]`. For Database objects, this triggers key-scoped selection. |
| Item access | `{RuleName[key]}` | Equivalent to attribute access for Database objects; also valid for Datalist (integer index) and Databag (string key). |
| Nested access | `{Names[Sex[key]][key]}` | Item and attribute access may be arbitrarily nested. |
| String comparison | `{'she' if Sex[key] == 'female' else 'he'}` | Conditional expression using string equality. |
| String method calls | `{Name.hero.upper()}` | String methods called on rendered values. |
| Any expression | `{', '.join([A.k, B.k])}` | Any expression the host language can evaluate in the given namespace. |

The minimum required capabilities for conformance are:

1. Variable access by name from Context.
2. Attribute access and item access on Context values.
3. String equality comparison.
4. Conditional (ternary) expressions.
5. String method calls on rendered values.

### Reference implementation mechanism

In the Python reference implementation, rendering is performed by:

```python
exec("result = eval(f'''f{result!r}''')", global_ctx, local_ctx)
```

This constructs a Python f-string from the template at runtime and evaluates it with
the Context as the global namespace. This is a Python-specific mechanism. A non-Python
implementation must satisfy the **behavioral contract**, not replicate the mechanism.
The behavioral contract is: all expressions in `{...}` are evaluated with the full
Context as the variable namespace, and the result is concatenated with the literal
portions of the template.

### Error handling

On any exception during template evaluation:

1. Log at ERROR level: `source_path`, `template`, and the exception.
2. Re-raise the original exception without wrapping.

An undefined variable name in an expression raises a `NameError` (or the equivalent in
the implementation language). This is not caught; it propagates to the caller.

### Grammar file declaration

```yaml
render: ftemplate
```

This is the default; the key may be omitted entirely.

### Examples

```yaml
# Template: simple variable substitution
Begin:
  - "{Greeting}, {Name}!"

# Template: attribute access (key-scoped)
Begin:
  - "{Name.Protag} confronts {Name.Antag}."

# Template: conditional expression
pronoun:
  - "{'she' if Sex[key] == 'female' else 'he'}"

# Template: article property
Begin:
  - "{Person.An} {Person} walks into the room."
  # Produces: "An astronaut walks into the room."
  # or:       "A doctor walks into the room."

# Template: string method
Begin:
  - "{Name.hero.upper()} won the tournament."
```

---

## jinja2 Engine

**Identifier**: `jinja2` (alias: `jinja`)

### Semantics

The template string is rendered using the Jinja2 template engine. The full Context map
is passed as the template rendering variables.

Jinja2 provides a richer templating language than ftemplate, including control flow
constructs, filters, and macros.

### Syntax

| Construct | Syntax | Description |
|---|---|---|
| Variable substitution | `{{ expression }}` | Evaluates and outputs the expression. |
| Statement | `{% statement %}` | Control flow: `if`, `for`, `set`, `block`, etc. |
| Comment | `{# comment #}` | Ignored by the renderer. |
| Filter | `{{ value \| filter }}` | Applies a Jinja2 filter to the value (e.g., `\| upper`, `\| capitalize`). |

### Undefined variable behavior

The `jinja2` engine is configured with **DebugUndefined** mode. When a template
references a variable name that is not present in the Context, the output includes
the literal Jinja2 undefined marker for that variable rather than raising an error
or substituting an empty string.

For example, if `{unknown_var}` is referenced in a Jinja2 template and `unknown_var`
is not in the Context, the output will contain `{{ unknown_var }}` verbatim. This
allows partial rendering for debugging purposes.

**Normative**: this behavior must be replicated. The undefined behavior must not be
`Undefined` (which raises on access) or `ChainableUndefined` (which returns empty
string). It must be `DebugUndefined` semantics specifically.

### Error handling

On a `TemplateError` (or equivalent template rendering exception):

1. Log at ERROR level: `source_path`, `template`, and the exception.
2. Construct a detailed error message. If the exception includes source location
   information (line number and source text):
   - Include the `source_path`.
   - Include the 1-based line number.
   - Include the text of the failing line (prefixed with `"-->"` for readability).
3. If the exception does not include source location information:
   - Include the `source_path` and the full `template` string.
4. Raise a domain-level error (e.g., `ValueError`) with the constructed message,
   chaining the original template exception as the cause.

**Note**: the error message format is informative, not normative. Implementations must
log and raise; the exact message format may vary.

### Grammar file declaration

```yaml
render: jinja2
```

or equivalently:

```yaml
render: jinja
```

### Examples

```yaml
render: jinja2

# Template: conditional (Jinja2 style)
hero:
  - >
    {% if Sex[key] == 'female' %}heroine{% else %}hero{% endif %}

# Template: variable substitution
Begin:
  - "{{ Name.Protag }} faces {{ Name.Antag }} in the final battle."

# Template: filter
title:
  - "{{ Name.hero | capitalize }} of the Ancient Order"

# Template: for loop
roster:
  - >
    The party consists of:
    {% for member in members %}
    - {{ member }}
    {% endfor %}
```

---

## Selecting an Engine

### Per-module declaration

The `render:` key at the top level of a YAML Grammar file sets the template engine for
all `TextRule` instances defined in that file.

```yaml
render: jinja2   # or: ftemplate (default)
```

Any value other than `ftemplate`, `jinja2`, or `jinja` is a parse error that must
cause the parser to raise an exception before any rendering occurs.

### Scope of the declaration

The `render:` key applies only to the Grammar file in which it appears. Each included
Grammar file uses the engine declared in its own file. There is no inheritance of
render strategy across include boundaries.

**Example**: if `story.yaml` declares `render: jinja2` and includes `names.yaml`
which has no `render:` declaration (defaulting to `ftemplate`), then:

- All TextRules defined in `story.yaml` are rendered with `jinja2`.
- All TextRules defined in `names.yaml` are rendered with `ftemplate`.

### Mixing engines

A single render pass may use both engines simultaneously if the Grammar and its
includes declare different engines. The engine used for a given TextRule is fixed at
parse time (captured when the TextRule is constructed) and does not change at render
time.

---

## RenderedString

Both template engines return a `RenderedString` — a string subtype that provides
article-generation properties.

### Definition

A `RenderedString` is a string that additionally supports:

| Property | Alias | Returns |
|---|---|---|
| `.a` | `.an` | `"a"` or `"an"` based on the first character |
| `.A` | `.An` | `"A"` or `"An"` — the capitalized form |

The article is determined by inspecting the first character of the string value
(lowercased). If the first character is one of `{a, e, i, o, u}`, the article is
`"an"`. Otherwise the article is `"a"`.

For the complete algorithm, including edge cases for empty strings, see
`10-article-generation.md`.

### Usage in templates

`RenderedString` article properties are accessed as attributes in template expressions:

```yaml
# ftemplate syntax:
Begin:
  - "{Person.an.capitalize()} {Person} enters."

# Produces: "An astronaut enters." or "A doctor enters."
```

```yaml
render: jinja2

# Jinja2 syntax (accessing article as attribute on the rendered value):
Begin:
  - "{{ Person.an | capitalize }} {{ Person }} enters."
```

### Implementation note

`RenderedString` must be a proper subtype of string in the implementation language —
not a wrapper object. Template expressions that produce a `RenderedString` must be
usable anywhere a plain string is expected, including string concatenation, `upper()`,
`lower()`, and other string operations.

---

## Conformance Requirements Summary

| Requirement | ftemplate | jinja2 |
|---|---|---|
| Variable access from Context | Required | Required |
| Attribute and item access on Context values | Required | Required |
| String comparison and conditional expressions | Required | Required |
| String method calls on rendered values | Required | Via filters |
| DebugUndefined mode for missing variables | N/A | Required |
| Returns `RenderedString` with article properties | Required | Required |
| Logs and re-raises on error | Required | Required |
| Detailed error message with source location | N/A | Required |
