"""Scorer auto-registration.

Importing this package triggers registration of all built-in scorers
into the global ``brand.registry.scorers`` registry.
"""

# Import submodules to trigger their @registry.register calls
from brand._scorers import phonetic  # noqa: F401
from brand._scorers import availability  # noqa: F401
from brand._scorers import linguistic  # noqa: F401
from brand._scorers import visual  # noqa: F401
from brand._scorers import composite  # noqa: F401
from brand._scorers import company  # noqa: F401
from brand._scorers import llm  # noqa: F401
