"""Shared floor label formatting for UI selectors."""

from typing import Iterable, Optional


def format_floor_label_from_index(floor_index: int, elevation: float) -> str:
    """Format floor labels as G/F, 1/F, 2/F with elevation text."""
    if floor_index <= 0:
        return f"G/F ({elevation:+.2f})"
    return f"{floor_index}/F ({elevation:+.2f})"


def format_floor_label_from_elevation(
    elevation: float,
    floor_levels: Optional[Iterable[float]] = None,
    tolerance: float = 0.01,
) -> str:
    """Format a floor label from elevation using ordered floor levels when available."""
    if floor_levels is None:
        return f"Z = {elevation:.2f}m"

    sorted_levels = sorted(floor_levels)
    for index, level in enumerate(sorted_levels):
        if abs(level - elevation) < tolerance:
            return format_floor_label_from_index(index, elevation)

    return f"Z = {elevation:.2f}m"


def format_floor_label_from_floor_number(floor: int, story_height: float) -> str:
    """Format a floor label from floor index and story height."""
    elevation = float(floor) * float(story_height)
    return format_floor_label_from_index(floor, elevation)
