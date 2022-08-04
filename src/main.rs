use anyhow::Result;
use glob::glob;
use regex::Regex;
use reqwest;
use scraper::{Html, Selector};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fmt::{Display, Formatter};
use std::fs;
use std::fs::{read_to_string, File};
use std::path::{Path, PathBuf};
use structopt::StructOpt;
use thiserror::Error;

#[derive(Debug, StructOpt)]
#[structopt(about = "Taxonomy of crypto open source repositories")]
#[structopt(name = "crypto-ecosystems", rename_all = "kebab-case")]
enum Cli {
    /// Validate all of the toml configuration files
    Validate {
        /// Path to top level directory containing ecosystem toml files
        data_path: String,
    },
    /// Update all of the toml configuration files with latest git stats
    Update {
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
    pub toml_path: Option<PathBuf>,
    pub github_organizations: Option<Vec<String>>,
    pub sub_ecosystems: Option<Vec<String>>,
    pub repo: Option<Vec<Repo>>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
struct Repo {
    pub url: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tags: Option<Vec<String>>,
    pub last_commit: Option<String>,
    pub last_commit_time: Option<String>,
    pub status: Option<String>,
    pub stats: Option<HashMap<String, u32>>,
}

#[derive(Debug)]
struct FieldSelector {
    selector: Selector,
    fields: HashMap<String, u8>,
}

#[derive(Debug, Error)]
enum CEError {
    #[error("Toml Parse Error in {path:?}: {toml_error:?}")]
    TomlParseError {
        path: String,
        toml_error: toml::de::Error,
    },
    #[error("Toml Serialization Error in {contents:?}: {toml_error:?}")]
    TomlSerializationError {
        contents: String,
        toml_error: toml::ser::Error,
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
            Ok(mut ecosystem) => {
                let title = ecosystem.title.clone();
                ecosystem.toml_path = Option::from(toml_path.clone());
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

fn write_toml_file(ecosystem: Ecosystem) -> Result<(), CEError> {
    if ecosystem.toml_path.is_some() {
        match toml::to_string(&ecosystem) {
            Ok(toml_string) => {
                fs::write(&ecosystem.toml_path.unwrap(), &toml_string)
                    .expect("TODO: panic message");
            }
            Err(err) => {
                return Err(CEError::TomlSerializationError {
                    contents: serde_json::to_string_pretty(&ecosystem).unwrap(),
                    toml_error: err,
                })?;
            }
        }
    }
    Ok(())
}

async fn validate_ecosystems(ecosystem_map: &EcosystemMap) -> Vec<ValidationError> {
    let mut tagmap: HashMap<String, u32> = HashMap::new();
    let mut repo_set = HashSet::new();
    let mut errors = vec![];
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
    errors
}

async fn update_ecosystems(ecosystem_map: &EcosystemMap) -> () {
    for ecosystem in ecosystem_map.values() {
        println!("Getting updated stats for {}", ecosystem.title);
        let mut ecosystem_latest = ecosystem.clone();
        if let Some(ref repos) = ecosystem.repo {
            let mut repos_clone = repos.clone();
            for (index, repo) in repos.iter().enumerate() {
                let url_clone = repo.url.clone();
                let tags_clone = repo.tags.clone();
                let repo_latest = get_latest_repo_details(url_clone, tags_clone).await;
                repos_clone[index] = repo_latest
            }
            ecosystem_latest.repo = Option::from(repos_clone);
        }
        match write_toml_file(ecosystem_latest) {
            Err(err) => {
                println!("{:?}", err)
            }
            _ => {}
        }
    }
}

fn get_github_selectors() -> Vec<FieldSelector> {
    Vec::from([
        FieldSelector {
            selector: Selector::parse("div.mt-2 strong").unwrap(),
            fields: HashMap::from([
                (String::from("stars"), 0),
                (String::from("watching"), 1),
                (String::from("forks"), 2),
            ]),
        },
        FieldSelector {
            selector: Selector::parse("div.Details strong").unwrap(),
            fields: HashMap::from([
                (String::from("branches"), 0),
                (String::from("tag_count"), 1),
            ]),
        },
        FieldSelector {
            selector: Selector::parse("div.file-navigation strong").unwrap(),
            fields: HashMap::from([(String::from("commits"), 0)]),
        },
    ])
}

async fn get_latest_repo_details(repo_url: String, tags: Option<Vec<String>>) -> Repo {
    let selectors = get_github_selectors();
    let response = reqwest::get(&repo_url).await.unwrap();
    let status = String::from(response.status().clone().as_str());
    let body = response.text().await.unwrap();
    let body_parsed = Html::parse_fragment(&*body);
    let last_commit = find_commit_hash(body);
    let mut last_commit_time = None;
    if last_commit.is_some() {
        last_commit_time = get_latest_commit(&repo_url, &last_commit.as_ref().unwrap()).await;
    }
    let mut repo = Repo {
        url: repo_url,
        tags,
        last_commit,
        last_commit_time,
        status: Option::from(status),
        stats: None,
    };
    let mut stats: HashMap<String, u32> = HashMap::new();
    for field_selector in selectors {
        let elements = parse_numbers_from_elements(&body_parsed, field_selector.selector);
        for (field_name, field_index) in field_selector.fields {
            stats.insert(
                field_name,
                *elements.get(field_index as usize).unwrap_or(&0),
            );
        }
    }
    repo.stats = Option::from(stats);
    repo
}

fn find_commit_hash(body: String) -> Option<String> {
    let commit_regex = Regex::new(r"tree-commit/([a-z0-9]+)").unwrap();
    for capture in commit_regex.captures_iter(&body) {
        let last_commit = String::from(&capture[1]);
        return Option::from(last_commit);
    }
    None
}

fn parse_numbers_from_elements(html: &Html, selector: Selector) -> Vec<u32> {
    html.select(&selector)
        .map(|el| el.inner_html().to_string().trim().parse().unwrap_or(0))
        .collect()
}

async fn get_latest_commit(repo_url: &String, latest_commit: &str) -> Option<String> {
    let latest_commit_url = format!("{}/commit/{}", &repo_url, latest_commit);
    let latest_response = reqwest::get(&latest_commit_url).await.unwrap();
    let latest_commit_body = latest_response.text().await.unwrap();
    let datetime_re =
        Regex::new(r#"relative-time datetime="(\d{4}-\d{2}-\d{2}T\d{2}:\d{2})"#).unwrap();
    for cap in datetime_re.captures_iter(&latest_commit_body) {
        return Some(cap[1].to_owned());
    }
    None
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

async fn update(data_path: String) -> Result<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok(ecosystem_map) => {
            update_ecosystems(&ecosystem_map).await;
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
        Ok(ecosystem_map) => {
            let errors = validate_ecosystems(&ecosystem_map).await;
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
        Cli::Validate { data_path } => validate(data_path).await?,
        Cli::Update { data_path } => update(data_path).await?,
        Cli::Export {
            data_path,
            output_path,
        } => export(data_path, output_path).await?,
    }
    Ok(())
}
