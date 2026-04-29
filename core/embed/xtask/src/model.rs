use anyhow::{Context, Result};
use clap::ValueEnum;

use crate::helpers;

#[derive(ValueEnum, Debug, Clone, Copy, PartialEq, Eq)]
pub enum Model {
    #[value(name = "d001")]
    D001,
    #[value(name = "d002")]
    D002,
    #[value(name = "t2t1")]
    T2T1,
    #[value(name = "t2b1")]
    T2B1,
    #[value(name = "t3b1")]
    T3B1,
    #[value(name = "t3t1")]
    T3T1,
    #[value(name = "t3w1")]
    T3W1,
}

impl Model {
    /// Returns the cargo feature to pass to select this model.
    /// Uses `models/model_*` dep-feature syntax so project crates don't need
    /// their own `model_*` feature declarations.
    pub fn feature_name(self) -> String {
        format!("models/model_{}", self.model_id().to_lowercase())
    }

    /// Returns the model ID used in artifact naming
    pub fn model_id(self) -> &'static str {
        match self {
            Model::D001 => "D001",
            Model::D002 => "D002",
            Model::T2T1 => "T2T1",
            Model::T2B1 => "T2B1",
            Model::T3B1 => "T3B1",
            Model::T3T1 => "T3T1",
            Model::T3W1 => "T3W1",
        }
    }

    /// Returns the path to the model-specific memory.ld file
    pub fn model_memory_ld(self) -> Result<std::path::PathBuf> {
        let mem_ld = helpers::workspace_dir()?
            .join("models")
            .join(self.model_id())
            .join("memory.ld")
            .canonicalize()
            .with_context(|| format!("Failed to locate memory.ld for model {}", self.model_id()))?;
        Ok(mem_ld)
    }
}
