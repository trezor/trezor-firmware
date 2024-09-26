from __future__ import annotations

from site_scons import models

from . import mercury, tr, tt


def get_ui_module(model: str):
    ui_modules = {
        "mercury": mercury,
        "tr": tr,
        "tt": tt,
    }

    return ui_modules[models.get_model_ui(model)]


def init_ui(
    model: str,
    stage: int,
    defines: list[str | tuple[str, str]],
    sources: list[str],
    rust_features: list[str],
):
    conf = models.get_model_ui_conf(model)
    get_ui_module(model).init_ui(stage, conf, defines, sources, rust_features)


def get_ui_layout(model: str):
    return get_ui_module(model).get_ui_layout()


def get_ui_layout_path(model: str):
    return get_ui_module(model).get_ui_layout_path()
