# The lens: does the code do what it claims?

**You look for a claim — in a docstring, in a comment, in a header — that
the code contradicts.**

This is the defect class that documentation passes find most often, and
it is the one that no test catches: the header says the argument scales
the drying memory, the function discards the argument; the docstring
says the function falls back to the zero array, the function raises; the
comment says the key is written in emission order, the writer emits it
in a different order.

## What is a finding

1. **A parameter that the documentation names and the code ignores.** The
   signature, the header, or the docstring gives a parameter a meaning
   — a scaling, a threshold, a unit — and the body never reads it.
2. **A promise the code breaks.** "Returns `None` when the file is
   missing"; the code raises. "Never writes a value outside the
   raster"; the code writes one. "The order of the keys is the order of
   emission"; the code sorts them.
3. **A claim about a neighbour.** The comment says "the caller
   validates the grid", and the change removed the caller's
   validation.
4. **A docstring that describes the old behaviour.** The change
   rewrote the body and left the prose.
5. **A default that is not the default.** The docstring says the
   default is 30 days; the signature says 7.

## What is not a finding

* A claim that is vague but not false ("handles the edge cases").
* A comment that explains *why* rather than *what*, where the why is
  still true.
* A claim about something outside the pull request's reach (a claim
  about a third-party library's behaviour, unless the change depends on
  it).
* A TODO that says the behaviour is not implemented yet, when the code
  really does not implement it.

## How to be sure

Read the function, not its docstring. Then read the implementation it
calls, when the claim is about what the function does rather than what
it says. A claim is contradicted when the code *cannot* satisfy it —
that is the strongest form of the finding and the one to report. A claim
that merely looks unsatisfied is often a matter of reading.

## The report

For each finding, quote the claim, quote the code that contradicts it,
and name the file and the line of both. The impact is the question the
claim was supposed to answer for somebody.
