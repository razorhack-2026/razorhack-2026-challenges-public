"""Culture Shock: Adapt or Die — colony growth engine (GM/server side only).

This module holds the growth law, and the growth law is the answer to the
challenge. It is used by the challenge server (``src/app.py``), the reference
solution (``solution/solve.py``) and the GM build scripts — and by nothing else.
The competitor's web page contains **no simulation code at all** and only ever
sees the *result* of applying this module, through ``POST /observe``.

Pure Python, no third-party dependencies.

The board is row-major: ``cells[row * cols + col]``.
"""

from __future__ import annotations

from dataclasses import dataclass

# Radius of the neighbor ring. 1 = classic Moore neighbourhood (8 cells);
# 2 = the 16 cells at Chebyshev distance exactly 2 (the border of a 5x5 block).
# This part is public: both earlier challenges in the sequence state it.
RING_RADIUS = 2

# Board edges are hard walls: anything outside the grid is permanently dead.
WRAP = False

# Refuse boards larger than this so a hostile upload cannot spin a worker.
MAX_CELLS = 40000

# ── The growth law (the secret this challenge is about) ─────────────────────
# A dead cell is born when its ring holds a count in BIRTH; a live cell survives
# when its ring holds a count in SURVIVE, and dies otherwise.
BIRTH = frozenset({2})
SURVIVE = frozenset({2, 3, 4, 5})

# Canonical spelling of the law: the notation a competitor must submit.
RULE_NOTATION = "B2/S2345"

ALIVE_CHARS = frozenset("Oo#Xx1*")
DEAD_CHARS = frozenset(".0 -")


class BoardError(ValueError):
    """Raised when a submitted board cannot be parsed."""


class RuleError(ValueError):
    """Raised when a submitted growth law is not valid notation."""


@dataclass(frozen=True)
class Board:
    cols: int
    rows: int
    generation: int
    cells: tuple

    def alive(self) -> int:
        return sum(self.cells)


def ring_offsets(radius: int = RING_RADIUS):
    """Offsets of every cell at Chebyshev distance exactly ``radius``."""
    return tuple(
        (dx, dy)
        for dy in range(-radius, radius + 1)
        for dx in range(-radius, radius + 1)
        if max(abs(dx), abs(dy)) == radius
    )


_RING_CACHE = {r: ring_offsets(r) for r in range(1, 6)}


def _as_int(value):
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# ── Growth law notation ─────────────────────────────────────────────────────
# Accepted forms: "B2/S2345", "b2/s2345", "2/2345", "B2S2345". Digits are
# neighbour counts 0-8; order and duplicates do not matter. Malformed input
# raises RuleError so a typo is never silently treated as a wrong answer.

def format_rule(birth=BIRTH, survive=SURVIVE) -> str:
    """Render a law in B/S notation, e.g. ``B2/S2345``."""
    births = "".join(str(n) for n in sorted(birth))
    survives = "".join(str(n) for n in sorted(survive))
    return f"B{births}/S{survives}"


def _parse_counts(chunk: str, label: str) -> frozenset:
    digits = set()
    for ch in chunk:
        if ch not in "0123456789":
            raise RuleError(f'{label} must be neighbour counts 0-8, not "{ch}"')
        digits.add(int(ch))
    return frozenset(digits)


def parse_rule(text: str):
    """Parse B/S notation into ``(birth, survive)`` sets of neighbour counts."""
    if not isinstance(text, str):
        raise RuleError("growth law must be text")

    cleaned = "".join(text.split()).upper()
    if not cleaned:
        raise RuleError("growth law is empty")

    # Tolerate the "B2S2345" spelling by inserting the separator.
    if "/" not in cleaned:
        if "S" in cleaned:
            cleaned = cleaned.replace("S", "/S", 1)
        else:
            raise RuleError("write the law as B<births>/S<survivals>, e.g. B3/S23")

    if cleaned.count("/") != 1:
        raise RuleError("write the law as B<births>/S<survivals>, e.g. B3/S23")

    birth_text, survive_text = cleaned.split("/")

    if birth_text.startswith("B"):
        birth_text = birth_text[1:]
    elif birth_text.startswith("S"):
        raise RuleError("the part before '/' is the birth law (B...), not survival")

    if survive_text.startswith("S"):
        survive_text = survive_text[1:]
    elif survive_text.startswith("B"):
        raise RuleError("the part after '/' is the survival law (S...), not birth")

    if not survive_text:
        raise RuleError("the survival law after '/' is empty")

    return (
        _parse_counts(birth_text, "birth law"),
        _parse_counts(survive_text, "survival law"),
    )


def matches_rule(text: str) -> bool:
    """True when ``text`` names this challenge's growth law."""
    try:
        birth, survive = parse_rule(text)
    except RuleError:
        return False
    return birth == BIRTH and survive == SURVIVE


# ── Board format ────────────────────────────────────────────────────────────
# Header lines are optional and deliberately say nothing about the growth law.

def parse(text: str) -> Board:
    """Parse the plain-text board format produced by the web page.

    Header lines are optional; the grid itself is one line per row using
    ``O``/``#``/``1`` etc. for alive and ``.``/``0``/space for dead. Short rows
    are padded with dead cells.
    """
    if not isinstance(text, str):
        raise BoardError("board state must be text")

    meta = {}
    rows = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if not rows and ":" in line:
            key, _, value = line.partition(":")
            key = key.strip().lower()
            if key.replace("_", "").isalnum():
                meta[key] = value.strip()
                continue

        rows.append(line)

    if not rows:
        raise BoardError("board state contains no rows")

    cols = max(len(line) for line in rows)
    if cols * len(rows) > MAX_CELLS:
        raise BoardError(
            f"board is {cols}x{len(rows)}, larger than the {MAX_CELLS}-cell limit"
        )

    cells = [0] * (cols * len(rows))
    for row, line in enumerate(rows):
        padded = line.ljust(cols, ".")
        for col, ch in enumerate(padded):
            if ch in ALIVE_CHARS:
                cells[row * cols + col] = 1
            elif ch not in DEAD_CHARS:
                raise BoardError(
                    f'unexpected character "{ch}" on row {row + 1}, column {col + 1}'
                )

    declared_cols = _as_int(meta.get("cols"))
    declared_rows = _as_int(meta.get("rows"))
    if declared_cols is not None and declared_cols != cols:
        raise BoardError(f"header says {declared_cols} columns but the board has {cols}")
    if declared_rows is not None and declared_rows != len(rows):
        raise BoardError(f"header says {declared_rows} rows but the board has {len(rows)}")

    generation = max(0, _as_int(meta.get("generation")) or 0)

    return Board(cols=cols, rows=len(rows), generation=generation, cells=tuple(cells))


def serialize(board: Board) -> str:
    """Render a board in the same plain-text format the web page exports.

    Deliberately carries no growth-law header: this text is sent to the browser.
    """
    lines = [
        "# culture v3",
        f"cols: {board.cols}",
        f"rows: {board.rows}",
        f"generation: {board.generation}",
    ]
    for row in range(board.rows):
        start = row * board.cols
        lines.append(
            "".join("O" if board.cells[start + col] else "." for col in range(board.cols))
        )
    return "\n".join(lines) + "\n"


# ── Simulation ──────────────────────────────────────────────────────────────

def count_neighbors(cells, cols: int, rows: int, index: int, radius: int = RING_RADIUS,
                    wrap: bool = WRAP) -> int:
    """Count live cells on the ring of the given radius around ``index``."""
    ring = _RING_CACHE.setdefault(radius, ring_offsets(radius))
    row, col = divmod(index, cols)
    total = 0

    for dx, dy in ring:
        n_row = row + dy
        n_col = col + dx
        if wrap:
            n_row %= rows
            n_col %= cols
        elif not (0 <= n_row < rows and 0 <= n_col < cols):
            continue
        total += cells[n_row * cols + n_col]

    return total


def step(cells, cols: int, rows: int, birth=BIRTH, survive=SURVIVE,
         radius: int = RING_RADIUS, wrap: bool = WRAP):
    """Advance one generation under the given law (this challenge's by default)."""
    next_cells = [0] * (cols * rows)

    for index in range(cols * rows):
        neighbors = count_neighbors(cells, cols, rows, index, radius, wrap)
        if cells[index]:
            next_cells[index] = 1 if neighbors in survive else 0
        else:
            next_cells[index] = 1 if neighbors in birth else 0

    return next_cells


def run(cells, cols: int, rows: int, generations: int = 1, birth=BIRTH,
        survive=SURVIVE, radius: int = RING_RADIUS, wrap: bool = WRAP):
    """Advance ``generations`` generations and return the resulting cells."""
    current = list(cells)
    for _ in range(generations):
        current = step(current, cols, rows, birth, survive, radius, wrap)
    return current


def evolve(board: Board, generations: int = 1) -> Board:
    """Return a new Board advanced by ``generations`` generations."""
    cells = run(board.cells, board.cols, board.rows, generations)
    return Board(board.cols, board.rows, board.generation + generations, tuple(cells))


def same_board(a: Board, b: Board) -> bool:
    """True when two boards have identical dimensions and cells."""
    return a.cols == b.cols and a.rows == b.rows and tuple(a.cells) == tuple(b.cells)
