use failure::{Fail, Fallible};
use glob::glob;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::{read_to_string, File};
use std::path::{Path, PathBuf};
use structopt::StructOpt;

type Result<T> = std::result::Result<T, failure::Error>;

#[derive(Debug, StructOpt)]
#[structopt(about = "Taxonomy of crypto open source repositories")]
#[structopt(name = "crypto-ecosystems", rename_all = "kebab-case")]
enum Cli {
    /// Validate all of the toml configuration files
    Validate {
        /// Path to top level directory containing ecosystem toml files
        data_path: String,
    },
    /// Export list of ecosystems and repos to a JSON file
    Export {
        /// Path to top level directory containing ecosystem toml files
        data_path: String,

        /// JSON File to export the list of repos
        output_path: String,
    },
}

#[derive(Debug, Deserialize, Serialize)]
struct Ecosystem {
    pub title: String,
    pub github_organizations: Option<Vec<String>>,
    pub sub_ecosystems: Option<Vec<String>>,
    pub repo: Option<Vec<Repo>>,
}

#[derive(Debug, Deserialize, Serialize)]
struct Repo {
    pub url: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
}

#[derive(Debug, Fail)]
enum CEError {
    #[fail(display = "Toml Parse Error in {}: {}", path, toml_error)]
    TomlParseError {
        path: String,
        toml_error: toml::de::Error,
    },
    #[fail(display = "Ecosystem Data Integrity Issue: {}", _0)]
    EcosystemDataError(String),
}

type EcosystemMap = HashMap<String, Ecosystem>;

fn get_toml_files(dir: &Path) -> Result<Vec<PathBuf>> {
    let glob_pattern = format!("{}/**/*.toml", dir.display());
    let mut paths = vec![];
    for entry in glob(&glob_pattern).expect("Failed to read glob pattern") {
        match entry {
            Ok(path) => {
                paths.push(path);
            }
            Err(e) => println!("{:?}", e),
        }
    }
    Ok(paths)
}

fn parse_toml_files(paths: &[PathBuf]) -> Result<EcosystemMap> {
    let mut ecosystems: HashMap<String, Ecosystem> = HashMap::new();
    for toml_path in paths {
        let contents = read_to_string(toml_path)?;
        match toml::from_str::<Ecosystem>(&contents) {
            Ok(ecosystem) => {
                let title = ecosystem.title.clone();
                ecosystems.insert(title, ecosystem);
            }
            Err(err) => {
                return Err(CEError::TomlParseError {
                    path: toml_path.display().to_string(),
                    toml_error: err,
                })?;
            }
        }
    }
    Ok(ecosystems)
}

fn validate_ecosystems(ecosystem_map: &EcosystemMap) -> Result<()> {
    let mut tagmap: HashMap<String, u32> = HashMap::new();
    let mut repo_set = HashSet::new();
    for ecosystem in ecosystem_map.values() {
        if let Some(ref sub_ecosystems) = ecosystem.sub_ecosystems {
            for sub in sub_ecosystems {
                if !ecosystem_map.contains_key(sub) {
                    return Err(CEError::EcosystemDataError(format!(
                        "Missing subecosystem: {}",
                        sub
                    )))?;
                }
            }
        }
        if let Some(ref repos) = ecosystem.repo {
            for repo in repos {
                repo_set.insert(repo.url.clone());
                if let Some(tags) = &repo.tags {
                    for tag in tags {
                        let counter = tagmap.entry(tag.to_string()).or_insert(0);
                        *counter += 1;
                    }
                }
            }
        }
    }
    println!(
        "Validated {} ecosystems and {} repos",
        ecosystem_map.len(),
        repo_set.len(),
    );
    println!("\nTags");
    for (tag, count) in tagmap {
        println!("\t{}: {}", tag, count);
    }
    Ok(())
}

fn validate(data_path: String) -> Fallible<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok(ecosystem_map) => {
            if let Err(err) = validate_ecosystems(&ecosystem_map) {
                println!("{}", err);
                std::process::exit(-1);
            }
        }
        Err(err) => {
            println!("\t{}", err);
            std::process::exit(-1);
        }
    };
    Ok(())
}

fn export(data_path: String, output_path: String) -> Fallible<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok(ecosystem_map) => {
            if let Err(err) = validate_ecosystems(&ecosystem_map) {
                println!("{}", err);
                std::process::exit(-1);
            }
            serde_json::to_writer_pretty(File::create(output_path)?, &ecosystem_map)?;
        }
        Err(err) => {
            println!("\t{}", err);
            std::process::exit(-1);
        }
    };
    Ok(())
}

fn main() -> Fallible<()> {
    let args = Cli::from_args();
    match args {
        Cli::Validate { data_path } => {
            validate(data_path)?;
        }
        Cli::Export {
            data_path,
            output_path,
        } => export(data_path, output_path)?,
    }
    Ok(())
}
