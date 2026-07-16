use anyhow::{Context, Result, anyhow, bail};
use serde::Deserialize;
use std::collections::{HashMap, HashSet};

use crate::args::Project;
use crate::helpers::workspace_dir;

#[derive(Deserialize)]
pub struct ModelConfig {
    /// Model identifier (e.g. "T3W1"). Not part of model.toml; populated by
    /// [`ModelConfig::load`] from the directory the config was read from.
    #[serde(skip)]
    pub model_id: String,
    pub mcu: String,
    pub default_board: String,
    pub features: Vec<String>,
    #[serde(default)]
    pub secmon: bool,
    #[serde(default)]
    pub project_overrides: HashMap<String, ModelProjectOverride>,
    /// Signing tool for bootloader/bootloader_ci. Defaults to "headertool".
    #[serde(default)]
    pub bootloader_header_tool: Option<String>,
}

impl ModelConfig {
    pub fn load(model_id: &str) -> Result<Self> {
        let path = workspace_dir()?
            .join("models")
            .join(model_id)
            .join("model.toml");
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read model config: {}", path.display()))?;
        let mut config: ModelConfig = toml::from_str(&content)
            .with_context(|| format!("Failed to parse model config: {}", path.display()))?;
        config.model_id = model_id.to_string();
        Ok(config)
    }

    pub fn is_stm32f4(&self) -> bool {
        matches!(self.mcu.as_str(), "stm32f427" | "stm32f429")
    }

    pub fn has_feature(&self, name: &str) -> bool {
        self.features.iter().any(|f| f == name)
    }

    pub fn mcu_feature(&self) -> String {
        format!("mcu_{}", self.mcu)
    }

    pub fn target_triple(&self) -> Result<&'static str> {
        match self.mcu.as_str() {
            "stm32f427" | "stm32f429" => Ok("thumbv7em-none-eabihf"),
            "stm32u58" | "stm32u5g" | "stm32u5a" => Ok("thumbv8m.main-none-eabihf"),
            mcu => Err(anyhow!("Unknown MCU: {mcu}")),
        }
    }

    pub fn openocd_target(&self) -> Result<&'static str> {
        match self.mcu.as_str() {
            "stm32f427" | "stm32f429" => Ok("target/stm32f4x.cfg"),
            "stm32u58" | "stm32u5g" | "stm32u5a" => Ok("target/stm32u5x.cfg"),
            mcu => Err(anyhow!("Unknown MCU: {mcu}")),
        }
    }
}

pub struct Peripheral {
    pub name: String,
    pub features: Vec<String>,
}

pub struct BoardConfig {
    pub header: String,
    /// Header with the emulator configuration for this board. Present only for
    /// boards that support being emulated; selected instead of `header` when
    /// building the emulator.
    pub emulator_header: Option<String>,
    pub peripherals: Vec<Peripheral>,
}

impl BoardConfig {
    pub fn load(model_id: &str, board_id: &str) -> Result<Self> {
        let path = workspace_dir()?
            .join("models")
            .join(model_id)
            .join("boards")
            .join(format!("{}.toml", board_id));
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read board config: {}", path.display()))?;
        Self::parse(&content)
            .with_context(|| format!("Failed to parse board config: {}", path.display()))
    }

    fn parse(content: &str) -> Result<Self> {
        let value: toml::Value = toml::from_str(content)?;
        let table = value
            .as_table()
            .ok_or_else(|| anyhow!("Board config must be a TOML table"))?;

        let header = table
            .get("header")
            .and_then(|v| v.as_str())
            .ok_or_else(|| anyhow!("Board config missing 'header' field"))?
            .to_string();

        let emulator_header = table
            .get("emulator_header")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        let mut peripherals = Vec::new();
        for (key, val) in table {
            if key == "header" || key == "emulator_header" {
                continue;
            }
            let periph_table = val
                .as_table()
                .ok_or_else(|| anyhow!("invalid peripheral '{key}': expected table"))?;
            let features = periph_table
                .values()
                .filter_map(|v| v.as_str())
                .map(|s| s.to_string())
                .collect();
            peripherals.push(Peripheral {
                name: key.clone(),
                features,
            });
        }

        Ok(BoardConfig {
            header,
            emulator_header,
            peripherals,
        })
    }
}

#[derive(Deserialize)]
pub struct ProjectProfile {
    pub uses: Vec<String>,
    pub elf_sections: Vec<String>,
    /// Body sections used when the model has secmon and the binary needs a
    /// separately-signed body concatenated with a plain header.
    #[serde(default)]
    pub secmon_body_sections: Option<Vec<String>>,
    #[serde(default)]
    pub secmon_header_sections: Option<Vec<String>>,
    /// STM32F4 only: pad address and second-bank sections for split firmware.
    /// Part1 reuses `elf_sections`; only the bank2 extension is F4-specific.
    #[serde(default)]
    pub split_pad_to: Option<String>,
    #[serde(default)]
    pub split_part2_sections: Option<Vec<String>>,
}

impl ProjectProfile {
    pub fn load(project: Project) -> Result<Self> {
        let pkg = project.package_name(false);
        let path = workspace_dir()?
            .join("projects")
            .join(pkg)
            .join("project.toml");
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read project profile: {}", path.display()))?;
        toml::from_str(&content)
            .with_context(|| format!("Failed to parse project profile: {}", path.display()))
    }
}

#[derive(Deserialize, Default, Clone)]
pub struct ModelProjectOverride {
    #[serde(default)]
    pub exclude: Vec<String>,
}

pub struct BoardFeatures {
    pub features: Vec<String>,
    pub board_header: String,
}

pub fn resolve_board_features(
    model_config: &ModelConfig,
    board_id: &str,
    project: Project,
    emulator: bool,
) -> Result<BoardFeatures> {
    let board_config = BoardConfig::load(&model_config.model_id, board_id)?;
    let project_profile = ProjectProfile::load(project)?;
    let pkg = project.package_name(false);
    let model_override = model_config
        .project_overrides
        .get(pkg)
        .cloned()
        .unwrap_or_default();

    let uses: HashSet<&str> = project_profile.uses.iter().map(|s| s.as_str()).collect();
    let exclude: HashSet<&str> = model_override.exclude.iter().map(|s| s.as_str()).collect();

    let mut features = Vec::new();

    // Model-intrinsic features filtered by project profile then model exceptions
    for f in &model_config.features {
        if uses.contains(f.as_str()) && !exclude.contains(f.as_str()) {
            features.push(f.clone());
        }
    }

    // Board peripheral features filtered by project profile then model exceptions
    for periph in &board_config.peripherals {
        if uses.contains(periph.name.as_str()) && !exclude.contains(periph.name.as_str()) {
            features.push(periph.name.clone());
            for f in &periph.features {
                // Peripheral feature values must be crate-qualified (e.g.
                // "io/touch_ft3168", "sys/sdram_..."), so the owning crate is explicit.
                if !f.contains('/') {
                    bail!(
                        "board peripheral '{}': feature '{f}' must be crate-qualified (e.g. \"io/{f}\")",
                        periph.name
                    );
                }
                features.push(f.clone());
            }
        }
    }

    // MCU feature
    features.push(model_config.mcu_feature());

    // The emulator reuses the emulated board's feature set but swaps in the
    // board's emulator configuration header.
    let board_header = if emulator {
        board_config.emulator_header.ok_or_else(|| {
            anyhow!(
                "Board '{board_id}' of model '{}' does not support emulation (missing 'emulator_header')",
                model_config.model_id
            )
        })?
    } else {
        board_config.header
    };

    Ok(BoardFeatures {
        features,
        board_header,
    })
}
