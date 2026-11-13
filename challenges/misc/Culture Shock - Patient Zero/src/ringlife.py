"""Ring Life — B3/S23 with a radius-2 neighbor ring.

Shared by the challenge server (src/app.py) and the reference solution
(solution/solve.py). Pure Python, no third-party dependencies, so it can be
imported and unit-tested without Flask installed.

The board is row-major: ``cells[row * cols + col]``.
"""

from __future__ import annotations

from dataclasses import dataclass

# Radius of the neighbor ring. 1 = classic Moore neighborhood (8 cells),
# 2 = the 16 cells at Chebyshev distance exactly 2 (border of a 5x5 block).
RING_RADIUS = 2

# Board edges are hard walls: anything outside the grid is permanently dead
# (no toroidal wrapping). Matches the client page.
WRAP = False

# Refuse boards larger than this so a hostile upload cannot spin the worker.
MAX_CELLS = 40000

ALIVE_CHARS = frozenset("Oo#Xx1*")
DEAD_CHARS = frozenset(".0 -")


class BoardError(ValueError):
    """Raised when a submitted board cannot be parsed."""


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
    """Render a board in the same plain-text format the web page exports."""
    lines = [
        "# ringlife v1",
        f"# rule: B3/S23, neighbor ring r={RING_RADIUS}, wrap={WRAP}",
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


def step(cells, cols: int, rows: int, radius: int = RING_RADIUS, wrap: bool = WRAP):
    """Advance one generation under B3/S23."""
    next_cells = [0] * (cols * rows)

    for index in range(cols * rows):
        neighbors = count_neighbors(cells, cols, rows, index, radius, wrap)
        # B3: exactly 3 neighbors births a dead cell.
        # S23: 2 or 3 neighbors keeps a live cell alive.
        if neighbors == 3 or (cells[index] and neighbors == 2):
            next_cells[index] = 1

    return next_cells


def run(cells, cols: int, rows: int, generations: int = 10, radius: int = RING_RADIUS,
        wrap: bool = WRAP):
    """Advance ``generations`` generations and return the resulting cells."""
    current = list(cells)
    for _ in range(generations):
        current = step(current, cols, rows, radius, wrap)
    return current


def evolve(board: Board, generations: int = 10) -> Board:
    """Return a new Board advanced by ``generations`` generations."""
    cells = run(board.cells, board.cols, board.rows, generations)
    return Board(board.cols, board.rows, board.generation + generations, tuple(cells))


def same_board(a: Board, b: Board) -> bool:
    """True when two boards have identical dimensions and cells."""
    return a.cols == b.cols and a.rows == b.rows and tuple(a.cells) == tuple(b.cells)

