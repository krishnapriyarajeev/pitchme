"""Find the numbers in a piece of text, written as digits or as words.

Used to check that a rewritten answer does not bring in a figure the user
never said and the playbook does not hold. "forty dollars" and "$40" are
the same number.
"""

from __future__ import annotations

import re

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
_SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000}

_DIGITS = re.compile(r"\d[\d,]*(?:\.\d+)?")
_TOKEN = re.compile(r"[a-z]+|\d[\d,]*(?:\.\d+)?")


def _normal(value: float) -> str:
    return str(int(value)) if value == int(value) else f"{value:g}"


def numbers_in(text: str) -> set[str]:
    """Every number in `text`, as plain strings ("40", "2.5", "1000").
    Small words such as "one" in "one of our customers" count too, which
    errs on the safe side for a fact check."""
    found = {_normal(float(m.replace(",", ""))) for m in _DIGITS.findall(text)}
    total = current = 0
    in_number = False
    for token in _TOKEN.findall(text.lower()):
        if token in _UNITS or token in _TENS:
            current += _UNITS.get(token, 0) + _TENS.get(token, 0)
            in_number = True
        elif token in _SCALES and in_number:
            scale = _SCALES[token]
            if scale == 100:
                current *= scale
            else:
                total += current * scale
                current = 0
        elif token == "and" and in_number:
            continue
        else:
            if in_number:
                found.add(_normal(total + current))
            total = current = 0
            in_number = False
    if in_number:
        found.add(_normal(total + current))
    return found


def unsupported_numbers(text: str, *sources: str) -> tuple[str, ...]:
    """Numbers in `text` that appear in none of `sources`, sorted."""
    known: set[str] = set()
    for source in sources:
        known |= numbers_in(source)
    return tuple(sorted(numbers_in(text) - known, key=lambda n: float(n)))
