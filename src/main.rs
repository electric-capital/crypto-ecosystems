#![deny(elided_lifetimes_in_paths)]
use anyhow::Result;
use glob::glob;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fmt::{Display, Formatter};
use std::fs::{read_to_string, File};
use std::path::{Path, PathBuf};
use structopt::StructOpt;
use thiserror::Error;
use regex::Regex;
use std::time::Duration;
use reqwest;
use futures::stream::futures_unordered::FuturesUnordered;
use futures::StreamExt;


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

#[derive(Debug)]
enum ValidationError {
    MissingSubecosystem { parent: String, child: String },
}

impl Display for ValidationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            ValidationError::MissingSubecosystem { parent, child } => {
                write!(f, "Invalid subecosystem for {} -> {}", parent, child)
            }
        }
    }
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct Ecosystem {
    pub title: String,
    pub github_organizations: Option<Vec<String>>,
    pub sub_ecosystems: Option<Vec<String>>,
    pub repo: Option<Vec<Repo>>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct Repo {
    pub url: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
}

#[derive(Debug, Error)]
enum CEError {
    #[error("Toml Parse Error in {path:?}: {toml_error:?}")]
    TomlParseError {
        path: String,
        toml_error: toml::de::Error,
    },
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

async fn validate_ecosystems(ecosystem_map: &EcosystemMap) -> Vec<ValidationError> {
    let mut tagmap: HashMap<String, u32> = HashMap::new();
    let mut repo_set = HashSet::new();
    let mut errors = vec![];
    let mut tasks = FuturesUnordered::new();
    for ecosystem in ecosystem_map.values() {
        if let Some(ref sub_ecosystems) = ecosystem.sub_ecosystems {
            for sub in sub_ecosystems {
                if !ecosystem_map.contains_key(sub) {
                    errors.push(ValidationError::MissingSubecosystem {
                        parent: ecosystem.title.clone(),
                        child: sub.clone(),
                    });
                }
            }
        }
        if let Some(ref repos) = ecosystem.repo {
            for repo in repos {
                repo_set.insert(repo.url.clone());
                let url_clone = repo.url.clone();
                tasks.push(tokio::spawn(async move {
                    get_latest_commit(url_clone).await;
                }));
                if let Some(tags) = &repo.tags {
                    for tag in tags {
                        let counter = tagmap.entry(tag.to_string()).or_insert(0);
                        *counter += 1;
                    }
                }
            }
        }
    }
    if errors.len() == 0 {
        println!(
            "Validated {} ecosystems and {} repos",
            ecosystem_map.len(),
            repo_set.len(),
        );
        println!("\nTags");
        for (tag, count) in tagmap {
            println!("\t{}: {}", tag, count);
        }
    }

    while let Some(finished_task) = tasks.next().await {
        match finished_task {
            Err(e) => { /* e is a JoinError - the task has panicked */},
            Ok(result) => { /* result is the result of get_latest_commit */ }
        }
    }

    errors
}

async fn get_latest_commit(repo_url: String) -> Result<()> {
    let response = reqwest::get(&repo_url).await?;
    eprintln!("Response: {:?} {}", response.version(), response.status());

    let body = response.text().await?;

    let re = Regex::new(r"tree-commit/([a-z0-9]+)").unwrap();
    for cap in re.captures_iter(&body) {
        let latest_commit = &cap[1];
        if !latest_commit.is_empty() {
            println!("Latest commit response {}", latest_commit);
            let latest_commit_url = format!("{}/commit/{}", &repo_url, latest_commit);
            let latest_response = reqwest::get(&latest_commit_url).await?;
            let latest_commit_body = latest_response.text().await?;
            let datetime_re = Regex::new(r#"relative-time datetime="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})"#).unwrap();
            for cap in datetime_re.captures_iter(&latest_commit_body) {
                println!("Latest commit URL {}", &latest_commit_url);
                println!("Latest commit Time\n {:?}", &cap[1]);
            }
        }
    }


    Ok(())
    //yield_now().await
}

async fn validate(data_path: String) -> Result<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok(ecosystem_map) => {
            let errors = validate_ecosystems(&ecosystem_map).await;
            if errors.len() > 0 {
                for err in errors {
                    println!("{}", err);
                }
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

async fn export(data_path: String, output_path: String) -> Result<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok( ecosystem_map) => {
            let errors = validate_ecosystems( &ecosystem_map).await;
            if errors.len() > 0 {
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
#[tokio::main]
async fn main() -> Result<()> {
    let args = Cli::from_args();
    match args {
        Cli::Validate { data_path } => {
            validate(data_path).await?
        }
        Cli::Export {
            data_path,
            output_path,
        } => export(data_path, output_path).await?
    }
    Ok(())
}
