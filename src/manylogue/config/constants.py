"""Cross-cutting constants — contracts shared between packages.

Keep this file short: a value belongs here only when two or more packages rely
on it. A constant used by a single module is that module's implementation
detail and should stay next to the code that gives it meaning (e.g. storage
filenames, the skip sentinel). This package imports nothing from manylogue, so
anything may import from here without creating a cycle.
"""

# The human participant's canonical author name — the value carried by
# Message.author on human-sent messages and reserved in every roster. A constant
# for now; becomes a per-chat value later, when the human can set their own
# display name.
HUMAN_NAME = "Human"

# Every file Manylogue reads or writes is UTF-8.
ENCODING = "utf-8"
