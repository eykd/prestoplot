# PrestoPlot Specification — Overview

## Purpose

PrestoPlot is a generative text grammar engine. Users define grammars as YAML files
containing named rules. Rules may be template strings, lists of alternatives, or
structured key-value maps. The system evaluates these grammars to produce varied,
optionally deterministic text output.

This specification describes the system's behavior in implementation-neutral terms.
A conforming implementation in any language must produce identical output to the
reference Python implementation for all normative test cases.

---

## Architecture

PrestoPlot follows a hexagonal (ports-and-adapters) architecture. The domain core is
independent of all I/O concerns. Adapters on both sides mediate between the core and
external systems.

```
┌──────────────────────────────────────────────────────────────────────┐
│                         DRIVING ADAPTERS                             │
│                                                                      │
│   ┌─────────────┐   ┌─────────────────┐   ┌──────────────────────┐  │
│   │ CLI Adapter │   │  HTTP Adapter   │   │  Programmatic API    │  │
│   │ (presto run)│   │ (presto http)   │   │  (render_story())    │  │
│   └──────┬──────┘   └────────┬────────┘   └──────────┬───────────┘  │
└──────────┼───────────────────┼─────────────────────────┼────────────┘
           │                   │                         │
           ▼                   ▼                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                          DOMAIN CORE                                 │
│                                                                      │
│  ┌─────────────────┐    ┌──────────────────┐    ┌────────────────┐  │
│  │  Grammar Parser │    │ Context Factory  │    │  Seed Manager  │  │
│  │ (parse_grammar_ │    │  (get_context)   │    │  (make_seed,   │  │
│  │      file)      │    │                  │    │   get_rng)     │  │
│  └────────┬────────┘    └────────┬─────────┘    └───────┬────────┘  │
│           │                      │                       │           │
│           └──────────────────────▼───────────────────────┘           │
│                                  │                                   │
│                     ┌────────────▼───────────┐                       │
│                     │     Rule Evaluator     │                       │
│                     │  (Database, Databag,   │                       │
│                     │   Datalist, TextRule)  │                       │
│                     └────────────┬───────────┘                       │
└──────────────────────────────────┼───────────────────────────────────┘
                                   │
           ┌───────────────────────┼────────────────────────┐
           ▼                       ▼                        ▼
┌──────────────────┐   ┌───────────────────────┐   ┌───────────────┐
│   FileStorage    │   │    Template Engine    │   │     RNG       │
│  (YAML / .mp     │   │  (ftemplate / jinja2) │   │  (random,     │
│   file adapter)  │   │                       │   │   seeded)     │
└──────────────────┘   └───────────────────────┘   └───────────────┘
       DRIVEN ADAPTERS
```

---

## Glossary

The following terms are used with precise meanings throughout this specification.

| Term | Definition |
|------|-----------|
| **Module** | A named grammar file. The identifier used to load a grammar. Also called "grammar name." |
| **Grammar** | A parsed collection of named Rules loaded from a Module. In the reference implementation, the Grammar is represented as the rendering Context after parsing. |
| **Rule** | A named entry in a Grammar. Three concrete subtypes exist: TextRule, ListRule, and StructRule. |
| **Stanza** | Synonym for Rule, used when discussing the YAML source format. |
| **Context** | A mutable key-value map threaded through all grammar parsing and rendering operations. Contains at minimum a `seed` key. After parsing, the Context also holds all named Rules as values. |
| **Seed** | A string used to initialize random number generation. When auto-generated, it is a 32-character lowercase hexadecimal string. User-provided seeds may be any string. |
| **Key** | A string used to scope a seed during Database attribute access. Enables the same rule to produce consistent but distinct values in different named scopes (e.g., `protagonist` vs. `antagonist`). |
| **Mode** | The selection strategy for a ListRule. One of: `reuse`, `pick`, `ratchet`, `markov`, or `list`. |
| **RenderStrategy** | The template engine used to evaluate template strings in a Grammar. One of: `ftemplate` (default) or `jinja2`. |
| **Database** | A lazy-evaluating wrapper around a SelectionFactory. Provides per-key caching and seed scoping. String coercion calls the factory without key scoping. |
| **Databag** | A key-value map of Rules (corresponding to a YAML mapping / StructRule). Attribute or key access triggers rendering of the retrieved Rule. |
| **Datalist** | An ordered list of rendered strings produced by `list` mode. Accessed by integer index. |
| **Begin** | The mandatory entry-point Rule in every Grammar file. Rendering always starts here unless an alternative start stanza is specified explicitly. |
| **SelectionFactory** | A callable `(Context) -> value` produced by one of the five selection mode constructors (`choose`, `pick`, `ratchet`, `markovify`, `list`). |
| **ScopedSeed** | A derived seed string formed by concatenating a base seed, a hyphen, and a key string: `"{seed}-{key}"`. |

---

## Document Map

| Document | Contents |
|----------|----------|
| `01-domain-model.md` | Entities, value objects, aggregates, and domain services |
| `02-ports-and-adapters.md` | Hexagonal architecture: all ports and their contracts |
| `03-grammar-file-format.md` | YAML grammar format (normative reference) |
| `04-application-services.md` | Use cases and orchestration |
| `05-selection-modes.md` | Behavioral specification for all five selection modes |
| `06-seed-and-context.md` | Determinism, seed algorithm, and context scoping |
| `07-markov-chain.md` | Markov chain: training, generation, and constraints |
| `08-template-engines.md` | Template engine port contracts and behavior |
| `09-storage-adapters.md` | Storage port contract and adapter implementations |
| `10-article-generation.md` | English article helper (`a`/`an`) behavior |
| `11-test-specification.md` | Unit, integration, and GWT acceptance tests |
| `appendix-a-grammar-examples.md` | Annotated canonical YAML examples |

---

## Normative vs. Informative

Documents `01` through `11` and the appendix are **normative** unless a section is
explicitly marked "(informative)".

- **Normative**: a conforming implementation MUST satisfy these requirements. Deviation
  constitutes non-conformance.
- **Informative**: background information or one possible approach. Implementors may
  choose differently without affecting conformance.

The reference implementation is the Python package at
`src/prestoplot/` in this repository. Where this specification and the reference
implementation conflict, the specification takes precedence for new implementations;
file a bug if the reference implementation deviates.

---

## A Worked Example

The following self-contained grammar file illustrates the core behavior:

```yaml
# greet.yaml

Greeting:
  - Hello
  - Good day
  - Howdy

Name:
  - World
  - Friend
  - Stranger

Begin:
  - "{Greeting}, {Name}!"
```

Calling `render_story(storage, "greet", seed="example")` evaluates the grammar as
follows:

1. The Context is created with `seed = "example"`.
2. The grammar is parsed: `Greeting`, `Name`, and `Begin` are each wrapped in a
   `Database` backed by a `choose` factory (random selection with replacement).
3. Rendering begins at `Begin`. The single template `"{Greeting}, {Name}!"` is
   selected and evaluated.
4. The template references `{Greeting}` and `{Name}`. Each reference coerces its
   Database to a string, which calls the `choose` factory with the current Context.
5. The `choose` factory seeds an RNG from `context["seed"]` (i.e., `"example"`) and
   calls `rng.choice(items)`.
6. The same seed `"example"` is used for both selections, but because `random.Random`
   produces a sequence, the first call yields one item and the second call to a freshly
   seeded `Random("example")` yields the same first item again.

With `seed="example"`, the output is always identical across runs. With a different
seed, a different combination of greeting and name is selected.

> **Note on seed scoping.** When a template references `{Name.hero}` instead of
> `{Name}`, the Database constructs a scoped seed `"example-hero"` before calling the
> factory. This means `{Name.hero}` and `{Name.villain}` each produce consistent but
> independent values within the same render pass — `hero` always gets the same name
> for that seed, and `villain` always gets a different but equally consistent name.

The determinism guarantee: given the same seed string and the same grammar, every
conforming implementation produces the same output.
