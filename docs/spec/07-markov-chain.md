# 07 — Markov Chain

This document specifies the character-level Markov chain text generator used by
PrestoPlot's `markov` selection mode. The algorithm, data structures, and generation
procedure are all normative. An implementation that follows this specification exactly
will produce test-vector-compatible output.

The Markov chain generator is derived from Peter Corbett's CGI random name generator.
Its primary use case is generating plausible names and words that resemble a training
corpus phonetically and visually, without reproducing exact entries.

---

## Overview

The Markov chain operates at the **character level**, not the word level. It learns
which characters tend to follow which sequences of characters in the training corpus,
then uses those learned transitions to generate new character sequences of similar
character.

**Key design decisions**:

- **Character-level**: transitions are between individual characters, not words or
  syllables.
- **Fixed chain length**: the prefix width `chainlen` is set at construction time and
  determines how much prior context is used to predict each next character.
- **Space padding**: the beginning of each training name is represented by spaces,
  allowing the generator to learn how names tend to start.
- **Newline terminator**: the end of each training name is represented by `"\n"`,
  allowing the generator to learn when names tend to end.
- **Seeded generation**: the same seed always produces the same generated name from
  the same trained chain.

---

## Data Structure: MarkovChainDict

The `MarkovChainDict` is a mapping from prefix strings to lists of suffix characters.
It is the internal state of a trained Markov chain.

### Schema

```
MarkovChainDict = map[string → list[string]]
```

Each key is a prefix string of exactly `chainlen` characters. Each value is a list of
single-character strings that have been observed to follow that prefix in the training
corpus. The same suffix character may appear multiple times in the list; frequency of
appearance encodes transition probability.

### Operations

| Operation | Signature | Semantics |
|---|---|---|
| `add_key(prefix, suffix)` | `(string, string) → void` | Appends `suffix` to the list at `prefix`. Creates the list if the key is absent. |
| `get_suffix(prefix, rng)` | `(string, RNG) → string` | Calls `rng.choice(self[prefix])` and returns the selected character. If the list is empty, behavior is undefined (see Constraints). |

### Missing prefix lookup

Accessing a prefix that was never added during training returns an empty list, not an
error. An error arises only when `get_suffix` is called on an empty list (because
`rng.choice([])` fails). This is a corpus-adequacy constraint, not a lookup error.

---

## Training Algorithm

### Inputs

| Parameter | Type | Constraints |
|---|---|---|
| `source_names` | list of strings | Non-empty. Each string is one training example. |
| `chainlen` | integer | Must be in `[1, 10]` inclusive. |

### Validation

Chain length must satisfy `1 <= chainlen <= 10`. Values outside this range must raise
a `ValueError` before any training occurs. The bounds must not be silently clamped.

### Per-name training procedure

For each name `W` in `source_names`:

**Step 1 — construct the padded name**:

```
spacer = (" " * chainlen) + W
```

The padded name is exactly `chainlen` space characters followed by the name string.
This padding represents the "start of name" state in the Markov chain.

**Step 2 — add interior transitions**:

For each integer `i` from `0` to `len(W) - 1` inclusive:

```
prefix = spacer[i : i + chainlen]
suffix = spacer[i + chainlen]
add_key(prefix, suffix)
```

Because `spacer` is `chainlen` characters longer than `W`, the index
`i + chainlen` always falls within the bounds of `spacer`, and `spacer[i + chainlen]`
is exactly `W[i]` — the `i`-th character of the original name.

**Step 3 — add the end-of-name transition**:

```
prefix = spacer[len(W) : len(W) + chainlen]
suffix = "\n"
add_key(prefix, suffix)
```

This adds a transition from the last `chainlen` characters of the name to the newline
terminator character.

### Worked example

Training on `W = "Noah"` with `chainlen = 2`:

```
spacer = "  Noah"   (two spaces + "Noah")

Step 2 (interior transitions):
  i=0: prefix = spacer[0:2] = "  ", suffix = spacer[2] = "N"  → add_key("  ", "N")
  i=1: prefix = spacer[1:3] = " N", suffix = spacer[3] = "o"  → add_key(" N", "o")
  i=2: prefix = spacer[2:4] = "No", suffix = spacer[4] = "a"  → add_key("No", "a")
  i=3: prefix = spacer[3:5] = "oa", suffix = spacer[5] = "h"  → add_key("oa", "h")

Step 3 (end-of-name transition):
  prefix = spacer[4:6] = "ah", suffix = "\n"               → add_key("ah", "\n")
```

After training on `"Noah"` alone, the chain maps:

| Prefix | Suffixes |
|---|---|
| `"  "` | `["N"]` |
| `" N"` | `["o"]` |
| `"No"` | `["a"]` |
| `"oa"` | `["h"]` |
| `"ah"` | `["\n"]` |

With more training names, the lists grow longer and transitions become probabilistic.

---

## Generation Algorithm

### Inputs

| Parameter | Type | Default | Description |
|---|---|---|---|
| `start` | string | `""` | Characters to begin the generated name with. May be empty. |
| `max_length` | integer | `10` | Maximum number of characters in the output. Must be positive. |
| `seed` | string or null | `None` | Seed for the RNG. `None` uses the global non-deterministic RNG. |

### Algorithm

1. **Construct the RNG**: `rng = get_rng(seed)`.

2. **Compute the initial prefix**:
   - Take the last `chainlen` characters of `start`: `prefix = start[-chainlen:]`.
   - If `start` has fewer than `chainlen` characters (including when `start = ""`),
     pad on the left with spaces: `prefix = (" " * chainlen + start)[-chainlen:]`.
   - For the common case `start = ""`: `prefix = " " * chainlen`.

3. **Initialize**: `name = start`.

4. **Loop**:

   a. `suffix = markov.get_suffix(prefix, rng)`

   b. If `suffix == "-"`: skip this iteration (continue without appending). This
      handles a historical edge case in the reference corpus. The hyphen character
      is never appended to the generated name.

   c. If `suffix == "\n"` or `len(name) >= max_length`: exit the loop.

   d. `name = name + suffix`

   e. `prefix = prefix[1:] + suffix`
      (Drop the oldest character from the prefix, append the new suffix.)

5. **Return** `name`. The returned string does not include any terminator character.

### Generation example

Using the chain trained on `["Noah"]` above, with `chainlen = 2`, `start = ""`,
`seed = None` (illustrative — exact output depends on RNG state):

```
Initial prefix = "  "

Iteration 1: get_suffix("  ") → "N"   (only option); name = "N";   prefix = " N"
Iteration 2: get_suffix(" N") → "o"   (only option); name = "No";  prefix = "No"
Iteration 3: get_suffix("No") → "a"   (only option); name = "Noa"; prefix = "oa"
Iteration 4: get_suffix("oa") → "h"   (only option); name = "Noah"; prefix = "ah"
Iteration 5: get_suffix("ah") → "\n"  (only option); loop exits.

Output: "Noah"
```

With a richer training corpus, multiple options exist at each step and the RNG
selects among them.

---

## NameGenerator

The `NameGenerator` is the public interface to the Markov chain. It wraps a
`MarkovChainDict` and provides a callable interface for generating names.

### Construction

```
NameGenerator(source_names: list[string], chainlen: int = 2)
```

1. Validate `chainlen` in `[1, 10]`. Raise `ValueError` if out of range.
2. Initialize an empty `MarkovChainDict`.
3. Call the training algorithm with `source_names` and `chainlen`.

### `get_random_name(start, max_length, seed)`

Runs the generation algorithm as specified above with the given parameters.
Equivalent to calling the generation algorithm directly on the internal
`MarkovChainDict`.

### Iterator protocol

`NameGenerator` is an iterator. Calling `next(generator)` is equivalent to calling
`get_random_name()` with default parameters (empty start, max_length 10, no seed).
This enables usage patterns like:

```python
names = NameGenerator(corpus, chainlen=2)
first_five = [next(names) for _ in range(5)]
```

---

## Constraints

| Parameter | Constraint | Error on violation |
|---|---|---|
| `chainlen` | `1 <= chainlen <= 10` | `ValueError` |
| `source_names` | Non-empty list | Undefined: generation will fail at first `get_suffix` call |
| `start` | Any string, including empty | No error; padded automatically |
| `max_length` | Positive integer | Undefined behavior for `max_length <= 0` |

**Corpus adequacy**: if the training corpus is too small or `chainlen` is too large
relative to the name lengths, some prefixes encountered during generation may have no
recorded suffixes. This is not an error during training, but `get_suffix` on an empty
list will raise an error during generation. This is a usage constraint, not a
specification defect.

---

## Usage in Grammar Mode

When a ListRule has `mode: markov`, the Markov chain generator is used as the
selection factory. The behavior is as follows:

### Training corpus

The list items are treated as raw strings — the training corpus. They are **not**
evaluated as template expressions. Each item is used verbatim as a training name.

### Factory call behavior

At each factory call, the generator:

1. Constructs a new `NameGenerator` from the list items and the chain length read from
   `context.get("markov_chainlen", 2)`.
2. Calls `get_random_name` with:
   - `start = context.get("start_markov", "")`
   - `seed = get_seed(context)`
3. Returns the generated string.

**Note**: constructing a new `NameGenerator` on every factory call is the reference
behavior. Implementations may cache the trained chain for performance, provided the
cached chain is invalidated if the corpus or chain length changes.

### Context parameters

| Context key | Type | Default | Effect |
|---|---|---|---|
| `markov_chainlen` | integer | `2` | Chain length passed to `NameGenerator`. |
| `start_markov` | string | `""` | Starting sequence passed to `get_random_name`. |
| `seed` | string | (required) | Passed to `get_random_name` as the RNG seed. |

These parameters may be set by the caller via `render_story` keyword arguments or
`--markov-chainlen` / `--markov-start` CLI flags.

---

## Normative Test Vector

The following defines a normative test case that conforming implementations must pass.

### Training corpus

The following 43 names (comma-separated for readability; each name is one training
example, with any leading or trailing whitespace stripped):

```
Noah, Liam, William, Mason, James, Benjamin, Jacob, Michael, Elijah, Ethan,
Alexander, Oliver, Daniel, Lucas, Matthew, Aiden, Jackson, Logan, David, Joseph,
Samuel, Henry, Owen, Sebastian, Gabriel, Carter, Jayden, John, Luke, Anthony,
Isaac, Dylan, Wyatt, Andrew, Joshua, Christopher, Grayson, Jack, Julian, Ryan,
Jaxon, Levi, Nathan
```

### Parameters

| Parameter | Value |
|---|---|
| `chainlen` | `2` |
| `start` | `""` |
| `seed` | `"testing-Protag"` |

### Expected output

```
"Owenry"
```

This seed (`"testing-Protag"`) corresponds to the scoped seed derived when
`render_story("characters", seed="testing")` accesses the `Name` rule with key
`"Protag"`, as described in `11-test-specification.md`.

### Derivation

The seed `"testing-Protag"` is passed to `get_rng`, which constructs
`Random("testing-Protag")`. The Markov chain trained on the 43 names above generates
`"Owenry"` from this RNG.

A conforming implementation must produce exactly `"Owenry"` when given these inputs,
subject to the cross-language compatibility conditions described in `06-seed-and-context.md`.
