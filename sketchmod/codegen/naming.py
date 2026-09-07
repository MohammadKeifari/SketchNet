"""
Deterministic Python identifiers for graph values.

Every value in the generated script is named after the canvas node that
produced it, so the code can be read side by side with the diagram.  Each
scope (module, ``load_data``, ``forward``, ``train``, ``evaluate``) owns its
own :class:`Names` instance, which keeps identifiers short without ever
colliding.
"""

import keyword
import re

# Never handed out, in any scope: shadowing these would break the script.
GLOBAL_RESERVED = frozenset(keyword.kwlist) | {
    "torch",
    "nn",
    "optim",
    "np",
    "pd",
    "plt",
    "NamedTuple",
    "Optional",
    "Data",
    "Output",
    "Model",
    "DEVICE",
    "load_data",
    "train",
    "evaluate",
    "self",
    "print",
    "len",
    "int",
    "float",
    "range",
    "list",
    "dict",
}


def snake(text) -> str:
    """Turn an arbitrary graph id into a lowercase, Python-safe stem."""
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", str(text)).strip("_").lower()
    if not cleaned:
        return "value"
    if cleaned[0].isdigit():
        return f"v{cleaned}"
    return cleaned


class Names:
    """Allocates unique identifiers and remembers the one chosen per key."""

    def __init__(self, reserved=()):
        self._taken = set(GLOBAL_RESERVED) | {snake(r) for r in reserved}
        self._by_key = {}

    def fresh(self, preferred: str) -> str:
        """Return an unused identifier close to ``preferred``."""
        stem = snake(preferred)
        name = stem
        counter = 2
        while name in self._taken:
            name = f"{stem}_{counter}"
            counter += 1
        self._taken.add(name)
        return name

    def bind(self, key, preferred: str) -> str:
        """Allocate a name for ``key``, or return the one already bound to it."""
        if key not in self._by_key:
            self._by_key[key] = self.fresh(preferred)
        return self._by_key[key]

    def get(self, key):
        return self._by_key.get(key)

    def reserve(self, *names):
        """Mark identifiers as taken without binding them to a key."""
        self._taken.update(snake(n) for n in names)
