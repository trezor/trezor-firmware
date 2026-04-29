use std::collections::{HashMap, HashSet};
use anyhow::{Context, Result, anyhow};
use serde::Deserialize;

use crate::args::Component;
use crate::helpers::workspace_dir;

#[derive(Deserialize)]
pub struct ModelConfig {
    pub mcu: String,
    pub default_board: String,
    pub emulator_board: Option<String>,
    pub features: Vec<String>,
    #[serde(default)]
    pub secmon: bool,
    #[serde(default)]
    pub targets: HashMap<String, ModelTargetOverride>,
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
        toml::from_str(&content)
            .with_context(|| format!("Failed to parse model config: {}", path.display()))
    }

    pub fn is_stm32f4(&self) -> bool {
        matches!(self.mcu.as_str(), "stm32f427" | "stm32f429")
    }

    pub fn mcu_feature(&self) -> String {
        format!("mcu_{}", self.mcu)
    }

    pub fn target_triple(&self) -> Result<&'static str> {
        match self.mcu.as_str() {
            "stm32f427" | "stm32f429" => Ok("thumbv7em-none-eabihf"),
            "stm32u58" | "stm32u5g" => Ok("thumbv8m.main-none-eabihf"),
            mcu => Err(anyhow!("Unknown MCU: {mcu}")),
        }
    }

    pub fn openocd_target(&self) -> Result<&'static str> {
        match self.mcu.as_str() {
            "stm32f427" | "stm32f429" => Ok("target/stm32f4x.cfg"),
            "stm32u58" | "stm32u5g" => Ok("target/stm32u5x.cfg"),
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

        let mut peripherals = Vec::new();
        for (key, val) in table {
            if key == "header" {
                continue;
            }
            let features = val
                .as_table()
                .map(|t| {
                    t.values()
                        .filter_map(|v| v.as_str())
                        .map(|s| s.to_string())
                        .collect()
                })
                .unwrap_or_default();
            peripherals.push(Peripheral {
                name: key.clone(),
                features,
            });
        }

        Ok(BoardConfig { header, peripherals })
    }
}

#[derive(Deserialize)]
pub struct TargetProfile {
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

impl TargetProfile {
    pub fn load(component: Component) -> Result<Self> {
        let pkg = component.package_name(false);
        let path = workspace_dir()?
            .join("projects")
            .join(pkg)
            .join("target.toml");
        let content = std::fs::read_to_string(&path)
            .with_context(|| format!("Failed to read target profile: {}", path.display()))?;
        toml::from_str(&content)
            .with_context(|| format!("Failed to parse target profile: {}", path.display()))
    }
}

#[derive(Deserialize, Default, Clone)]
pub struct ModelTargetOverride {
    #[serde(default)]
    pub exclude: Vec<String>,
}

pub struct BoardFeatures {
    pub features: Vec<String>,
    pub board_header: String,
}

pub fn resolve_board_features(
    model_id: &str,
    model_config: &ModelConfig,
    board_id: &str,
    component: Component,
) -> Result<BoardFeatures> {
    let board_config = BoardConfig::load(model_id, board_id)?;
    let target_profile = TargetProfile::load(component)?;
    let pkg = component.package_name(false);
    let model_override = model_config.targets.get(pkg).cloned().unwrap_or_default();

    let uses: HashSet<&str> = target_profile.uses.iter().map(|s| s.as_str()).collect();
    let exclude: HashSet<&str> = model_override.exclude.iter().map(|s| s.as_str()).collect();

    let mut features = Vec::new();

    // Model-intrinsic features filtered by target profile then model exceptions
    for f in &model_config.features {
        if uses.contains(f.as_str()) && !exclude.contains(f.as_str()) {
            features.push(f.clone());
        }
    }

    // Board peripheral features filtered by target profile then model exceptions
    for periph in &board_config.peripherals {
        if uses.contains(periph.name.as_str()) && !exclude.contains(periph.name.as_str()) {
            features.push(periph.name.clone());
            for f in &periph.features {
                // Values that already contain '/' are crate-qualified (e.g. "sys/sdram_foo").
                // Bare values default to the "io/" crate.
                if f.contains('/') {
                    features.push(f.clone());
                } else {
                    features.push(format!("io/{}", f));
                }
            }
        }
    }

    // MCU feature
    features.push(model_config.mcu_feature());

    Ok(BoardFeatures {
        features,
        board_header: board_config.header,
    })
}
