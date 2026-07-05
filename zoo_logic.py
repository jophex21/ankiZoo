from __future__ import annotations

from typing import List, Tuple

from . import config


def tile_cost(owned_count: int) -> int:
    conf = config.get_config()
    base = int(conf.get("tileExpandBaseCost", 25))
    per_owned = int(conf.get("tileExpandCostPerOwned", 8))
    return base + per_owned * owned_count


def is_adjacent(tile: Tuple[int, int], owned_tiles: List[List[int]]) -> bool:
    x, y = tile
    owned_set = {(t[0], t[1]) for t in owned_tiles}
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if (x + dx, y + dy) in owned_set:
            return True
    return False


def in_bounds(tile: Tuple[int, int], grid_size: int) -> bool:
    x, y = tile
    return 0 <= x < grid_size and 0 <= y < grid_size


def can_buy_tile(tile: Tuple[int, int], owned_tiles: List[List[int]], grid_size: int) -> Tuple[bool, str]:
    owned_set = {(t[0], t[1]) for t in owned_tiles}
    if tile in owned_set:
        return False, "Tile already owned."
    if not in_bounds(tile, grid_size):
        return False, "Tile out of bounds."
    if not is_adjacent(tile, owned_tiles):
        return False, "Tile must be adjacent to an owned tile."
    return True, ""
