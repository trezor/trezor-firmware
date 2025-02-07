from __future__ import annotations

from site_scons import models

from . import ui_bolt, ui_caesar, ui_delizia


def get_ui_module(model: str, stage: str):
    ui_modules = {
        "delizia": ui_delizia,
        "caesar": ui_caesar,
        "bolt": ui_bolt,
    }

    layout = models.get_model_ui(model)

    if layout == "delizia" and stage == "prodtest":
        layout = "bolt"

    return ui_modules[layout]


def init_ui(
    model: str,
    stage: str,
    rust_features: list[str],
):
    conf = models.get_model_ui_conf(model)
    get_ui_module(model, stage).init_ui(stage, conf, rust_features)


def get_ui_layout(model: str):
    return get_ui_module(model, "firmware").get_ui_layout()


def get_ui_layout_path(model: str):
    return get_ui_module(model, "firmware").get_ui_layout_path()
