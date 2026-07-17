"""Prompt builder — maps user-adjustable sliders to English prompt fragments for ComfyUI."""

LENGTH_MAP: list[tuple[float, float, str]] = [
    (0.0, 0.3, "short"),
    (0.3, 0.6, "medium length"),
    (0.6, 1.0, "long"),
]

CURL_MAP: list[tuple[float, float, str]] = [
    (0.0, 0.2, "straight"),
    (0.2, 0.6, "wavy"),
    (0.6, 1.0, "curly"),
]

COLOR_MAP: dict[str, str] = {
    "black": "black",
    "brown": "brown",
    "red": "red",
    "blue": "blue",
    "purple": "purple",
    "blonde": "blonde",
    "gray": "gray",
    "pink": "pink",
}


def _map_value(value: float, mapping: list[tuple[float, float, str]]) -> str:
    """Map a 0-1 slider value to a label using threshold ranges."""
    for low, high, label in mapping:
        if low <= value < high:
            return label
    return mapping[-1][2]


def build_adjusted_prompt(
    base_prompt: str,
    length: float = 0.5,
    curl: float = 0.0,
    color: str = "black",
) -> str:
    """Build a prompt string from base prompt + user-adjustable parameters.

    Strategy: inject length/curl/color description before the word "hair"
    in the original prompt, or prepend if "hair" isn't found.
    The img trigger word required by PhotoMaker is preserved.
    """
    length_desc = _map_value(length, LENGTH_MAP)
    curl_desc = _map_value(curl, CURL_MAP)
    color_desc = COLOR_MAP.get(color, "black")

    style_desc = f"{length_desc} {curl_desc} {color_desc} hair"

    if "img" in base_prompt:
        return f"{style_desc}, {base_prompt}"

    return f"{style_desc}, {base_prompt}, img"
