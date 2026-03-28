"""Visual and typographic scorers.

These scorers measure properties of a name as it appears on screen or paper:
letter balance, keyboard distance, visual weight distribution.
"""

from brand.registry import scorers


# ---------------------------------------------------------------------------
# Letter anatomy constants
# ---------------------------------------------------------------------------

_ASCENDERS = set('bdfhklt')
_DESCENDERS = set('gjpqy')
_NEUTRAL = set('aceimnorsuvwxz')


# ---------------------------------------------------------------------------
# Scorers
# ---------------------------------------------------------------------------


@scorers.register(
    'letter_balance',
    description='Visual balance of ascenders, descenders, and neutral letters',
)
def letter_balance(name: str) -> dict:
    """Analyze the visual balance of a name's letter anatomy.

    Returns proportions of ascenders (b,d,f,h,k,l,t), descenders (g,j,p,q,y),
    and neutral height letters.  A balanced name has a mix; heavy-descender
    names look "bottom-heavy" as wordmarks.

    >>> result = letter_balance('brand')
    >>> result['ascender_ratio']
    0.2
    """
    name_lower = name.lower()
    n = len(name_lower) or 1
    asc = sum(1 for c in name_lower if c in _ASCENDERS)
    desc = sum(1 for c in name_lower if c in _DESCENDERS)
    neut = sum(1 for c in name_lower if c in _NEUTRAL)

    return {
        'ascender_ratio': round(asc / n, 2),
        'descender_ratio': round(desc / n, 2),
        'neutral_ratio': round(neut / n, 2),
        'has_ascenders': asc > 0,
        'has_descenders': desc > 0,
    }


# ---------------------------------------------------------------------------
# Keyboard distance
# ---------------------------------------------------------------------------

# QWERTY keyboard layout positions (row, col) for distance computation
_QWERTY_POS = {
    'q': (0, 0), 'w': (0, 1), 'e': (0, 2), 'r': (0, 3), 't': (0, 4),
    'y': (0, 5), 'u': (0, 6), 'i': (0, 7), 'o': (0, 8), 'p': (0, 9),
    'a': (1, 0), 's': (1, 1), 'd': (1, 2), 'f': (1, 3), 'g': (1, 4),
    'h': (1, 5), 'j': (1, 6), 'k': (1, 7), 'l': (1, 8),
    'z': (2, 0), 'x': (2, 1), 'c': (2, 2), 'v': (2, 3), 'b': (2, 4),
    'n': (2, 5), 'm': (2, 6),
}


def _key_distance(a: str, b: str) -> float:
    """Euclidean distance between two keys on QWERTY layout."""
    if a not in _QWERTY_POS or b not in _QWERTY_POS:
        return 0.0
    r1, c1 = _QWERTY_POS[a]
    r2, c2 = _QWERTY_POS[b]
    return ((r1 - r2) ** 2 + (c1 - c2) ** 2) ** 0.5


@scorers.register(
    'keyboard_distance',
    description='Average keyboard distance between consecutive letters (lower=easier to type)',
)
def keyboard_distance(name: str) -> float:
    """Mean Euclidean distance between consecutive key presses on QWERTY.

    Lower scores indicate easier-to-type names.

    >>> keyboard_distance('asdf')  # adjacent keys
    1.0
    >>> keyboard_distance('qz')  # far apart
    2.0
    """
    name_lower = name.lower()
    if len(name_lower) < 2:
        return 0.0

    distances = [
        _key_distance(a, b) for a, b in zip(name_lower[:-1], name_lower[1:])
    ]
    return round(sum(distances) / len(distances), 2) if distances else 0.0


@scorers.register(
    'name_length',
    description='Character count of the name',
)
def name_length(name: str) -> int:
    """Return the length of the name.

    >>> name_length('brand')
    5
    """
    return len(name)
