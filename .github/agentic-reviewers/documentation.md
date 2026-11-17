# The lens: is the change documented?

**You look for code that changed and whose documentation did not.**

A change is documented when a reader of the code — not of the diff,
not of the commit message — can tell, from the code itself, what the
changed thing does and what it now does differently. The documentation
that counts is the one that ships with the code: the docstring, the
comment above the declaration, the header's description of a field.

## What is a finding

1. **A new public entity with no documentation.** A function, class,
   method, constant, CLI flag, configuration key, or header member that
   the pull request introduces and that nothing explains. A reader meets
   a name and a signature and nothing else.

2. **Documentation that the change made false.** The docstring says
   "returns the daily mean"; the change made it return the median. The
   comment says the channel order is `rainfall, temperature`; the change
   made it `rainfall, air_temp_c`. These are the worst findings: the
   documentation is present, it is confident, and it is wrong.

3. **Documentation that states a value the code owns.** A docstring
   that writes "0.87" when the number lives in the configuration will
   be wrong the day the operator changes the configuration. The
   documentation should name the source of the value ("the basal
   survival of `model_constants.yaml`"), not repeat it. The same goes
   for a channel list, a file name, a band name, a contract version: if
   the code owns it, the documentation must point at it.

4. **Documentation that describes the mechanism, not the effect.** A
   comment that says "loops over the patches" where the interesting
   fact is what the loop decides. A docstring that restates the
   signature. The test is whether a reader could have predicted the
   behaviour from the documentation alone.

5. **A change whose effect is unmentioned anywhere near it.** The
   function's own documentation is fine, but the change breaks the
   promise the *caller's* docstring makes ("the caller must have
   validated the grid"). The caller is then the wrong place to look.

## What is not a finding

* A private helper with a self-evident name and three lines of body.
  The rule is "no obvious names, no narration", not "a comment
  everywhere".
* A test that has no docstring. Tests are read by the person who
  changed them.
* A stylistic preference about wording.
* A documentation change you would have written differently.
* An entity that the change only *moved*. Moving a function is not a
  change of behaviour, and the documentation travelled with it.

## How to be sure

Before you report a finding, check that the documentation really is
absent or really is wrong: open the file, read the declaration and the
comment above it, and compare them. The mechanical signals in the
context tell you which entities changed; they do not tell you what their
documentation says.

Report the case where the documentation is *misleading* before the case
where it is *missing*: a wrong docstring costs a reader more than an
absent one.
