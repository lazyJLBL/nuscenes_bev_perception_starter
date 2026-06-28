"""
Matplotlib plotting defaults shared by visualization scripts.
"""

from __future__ import annotations

from functools import lru_cache

import matplotlib
from matplotlib import font_manager


@lru_cache(maxsize=1)
def configure_matplotlib_chinese() -> str | None:
    """Configure matplotlib to use an installed Chinese-capable font."""
    preferred_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "SimSun",
        "Microsoft JhengHei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
    ]
    installed_fonts = {font.name for font in font_manager.fontManager.ttflist}

    selected_font = next((font for font in preferred_fonts if font in installed_fonts), None)
    if selected_font is None:
        return None

    matplotlib.rcParams["font.sans-serif"] = [selected_font, "DejaVu Sans"]
    matplotlib.rcParams["font.family"] = "sans-serif"
    matplotlib.rcParams["axes.unicode_minus"] = False
    return selected_font
