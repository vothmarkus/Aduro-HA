"""Test bootstrap that keeps protocol tests independent of Home Assistant."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).parents[1]
CUSTOM_COMPONENTS = ROOT / "custom_components"
ADURO = CUSTOM_COMPONENTS / "aduro"

# Importing a submodule normally executes custom_components/aduro/__init__.py,
# which requires a complete Home Assistant runtime. These tests deliberately
# exercise the protocol/model layer in isolation.
custom_components = ModuleType("custom_components")
custom_components.__path__ = [str(CUSTOM_COMPONENTS)]
sys.modules.setdefault("custom_components", custom_components)

aduro = ModuleType("custom_components.aduro")
aduro.__path__ = [str(ADURO)]
sys.modules.setdefault("custom_components.aduro", aduro)
