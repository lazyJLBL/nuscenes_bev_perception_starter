# -*- coding: utf-8 -*-
"""Backward-compatible module config export.

The backend no longer keeps hand-written fake metrics here. Runtime module
metadata comes from ``src.experiments.registry`` so UI cards reflect real
adapter availability and the latest experiment metrics.
"""

from src.experiments.registry import get_module_configs

MODULE_CONFIGS = get_module_configs()
