use anyhow::Result;
use glob::glob;
use imara_diff::intern::InternedInput;
use imara_diff::{diff, Algorithm, UnifiedDiffBuilder};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fmt::{Display, Formatter};
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
    /// Export list of ecosystems and repos to a JSON file
    Export {
        /// Path to top level directory containing ecosystem toml files
        data_path: String,
        /// JSON File to export the list of repos
        output_path: String,

        /// Include only repository files
        #[structopt(short, long)]
        only_repos: bool,
    },
}
#[derive(Debug)]
enum ValidationError {
    MissingSubecosystem { parent: String, child: String },

    DuplicateRepoUrl(String),

    TitleError(String),

    EmptyEcosystem(String),

    UnsortedEcosystem(UnsortedEcosystem),

    InvalidRepoUrl { url: String, url_type: RepoUrlType },
}

#[derive(Debug)]
struct UnsortedEcosystem {
    ecosystem: String,
    repo_diff: Option<String>,
    sub_eco_diff: Option<String>,
    github_org_diff: Option<String>,
}

impl Display for ValidationError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            ValidationError::MissingSubecosystem { parent, child } => {
                writeln!(f, "Invalid subecosystem for {} -> {}", parent, child)
            }
            ValidationError::DuplicateRepoUrl(url) => {
                writeln!(f, "Duplicate repo URL: {}", url)
            }
            ValidationError::TitleError(file) => {
                writeln!(f, "Title with leading/trailing space found in file: {}. Please remove the space(s) from your title.", file)
            }
            ValidationError::EmptyEcosystem(file) => {
                writeln!(f, "Ecosystem in file {} has neither organizations nor sub-ecosystems. Please remove this. You can add it back later when/if you find its orgs / repos.", file)
            }
            ValidationError::UnsortedEcosystem(unsorted_eco) => {
                writeln!(
                    f,
                    "{} has the following unsorted data.  You can fix it by moving the entries to the specified locations below",
                    unsorted_eco.ecosystem,
                )?;
                if let Some(ref eco_diff) = unsorted_eco.sub_eco_diff {
                    writeln!(f, "Sub ecosystems\n{}\n", eco_diff)?;
                }
                if let Some(ref org_diff) = unsorted_eco.github_org_diff {
                    writeln!(f, "Github Orgs\n{}\n", org_diff)?;
                }
                if let Some(ref repos) = unsorted_eco.repo_diff {
                    writeln!(f, "Repos\n{}\n", repos)?;
                }
                Ok(())
            }
            ValidationError::InvalidRepoUrl { url, url_type } => match url_type {
                RepoUrlType::GithubUnnormalized => {
                    writeln!(f, "Invalid repo URL: {} in repo section. Please remove the trailing slash for '{}'.", url, url)
                }
                RepoUrlType::GithubUserOrOrganization => {
                    writeln!(f, "Invalid repo URL: {} in repo section. Please specify a github repository instead of a user or organization.", url)
                }
                RepoUrlType::GithubTreeish => {
                    writeln!(f, "Invalid repo URL: {} in repo section. Please remove excess parts of the path like tree or master and use the canonical github repo name.", url)
                }
                RepoUrlType::InvalidUrl => {
                    writeln!(f, "Invalid repo URL: {} in repo section.", url)
                }
                _ => Ok(()),
            },
        }
    }
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
    pub missing: Option<bool>,
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

/// This enum handles a variety of url types that are put into repo url values.
#[derive(Debug)]
enum RepoUrlType {
    GithubUnnormalized,
    GithubUserOrOrganization,
    GithubRepository,
    GithubTreeish,
    OtherServiceRepository,
    InvalidUrl,
}

fn parse_repo_url_type(url: &str) -> RepoUrlType {
    match url::Url::parse(url) {
        Ok(parsed) => match parsed.host_str() {
            Some(host) => match host {
                "github.com" | "www.github.com" => {
                    if url.ends_with('/') {
                        RepoUrlType::GithubUnnormalized
                    } else {
                        let parts: Vec<&str> = parsed.path().split('/').collect();
                        if parts.len() == 3 {
                            RepoUrlType::GithubRepository
                        } else if parts.len() == 2 {
                            RepoUrlType::GithubUserOrOrganization
                        } else {
                            RepoUrlType::GithubTreeish
                        }
                    }
                }
                _ => RepoUrlType::OtherServiceRepository,
            },
            None => RepoUrlType::InvalidUrl,
        },
        Err(_) => RepoUrlType::InvalidUrl,
    }
}

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

fn parse_toml_files(paths: &[PathBuf]) -> Result<(EcosystemMap, Vec<ValidationError>)> {
    let mut ecosystems: HashMap<String, Ecosystem> = HashMap::new();
    let mut errors = Vec::new();
    for toml_path in paths {
        let contents = read_to_string(toml_path)?;
        match toml::from_str::<Ecosystem>(&contents) {
            Ok(ecosystem) => {
                let title = ecosystem.title.clone();
                if title.trim() != title {
                    errors.push(ValidationError::TitleError(toml_path.display().to_string()));
                }
                ecosystems.insert(title, ecosystem);
            }
            Err(err) => {
                Err(CEError::TomlParseError {
                    path: toml_path.display().to_string(),
                    toml_error: err,
                })?;
            }
        }
    }
    Ok((ecosystems, errors))
}

fn find_misordered_elements_diff(strings: &[String]) -> Option<String> {
    if strings.is_empty() {
        return None;
    }

    let before = strings.join("\n").to_string();
    let mut sorted = strings.to_vec();
    sorted.sort_by_key(|x| x.to_lowercase());
    if strings == sorted {
        return None;
    }
    let after = sorted.join("\n").to_string();
    let input = InternedInput::new(before.as_str(), after.as_str());
    let diff = diff(
        Algorithm::Histogram,
        &input,
        UnifiedDiffBuilder::new(&input),
    );
    Some(diff)
}

fn validate_ecosystems(ecosystem_map: &EcosystemMap) -> Vec<ValidationError> {
    let mut errors = vec![];
    let mut repo_set = HashSet::new();
    let mut missing_count = 0;

    for ecosystem in ecosystem_map.values() {
        let has_sub_ecosystems = ecosystem
            .sub_ecosystems
            .as_ref()
            .map_or(false, |sub_ecosystems| !sub_ecosystems.is_empty());

        let has_orgs = ecosystem
            .github_organizations
            .as_ref()
            .map_or(false, |orgs| !orgs.is_empty());

        let has_repos = ecosystem
            .repo
            .as_ref()
            .map_or(false, |repos| !repos.is_empty());

        let mut seen_repos = HashSet::new();
        let mut sorted_repos = ecosystem.repo.clone().unwrap_or_default();

        // Sort the repositories by URL if they exist
        sorted_repos.sort_by(|a, b| a.url.to_lowercase().cmp(&b.url.to_lowercase()));

        // Check if the repos are already sorted, if not, provide the sorted list as an error
        if let Some(repos) = &ecosystem.repo {
            if repos != &sorted_repos {
                // If not sorted, return an error with the full sorted list for the user to copy
                let sorted_list = sorted_repos
                    .iter()
                    .map(|repo| {
                        let mut entry = format!("[[repo]]\nurl = \"{}\"", repo.url);
                        if let Some(true) = repo.missing {
                            entry.push_str("\nmissing = true");
                        }
                        entry
                    })
                    .collect::<Vec<String>>()
                    .join("\n\n");

                errors.push(ValidationError::UnsortedEcosystem(UnsortedEcosystem {
                    ecosystem: ecosystem.title.clone(),
                    repo_diff: Some(format!(
                        "{} is not sorted. Here is the correct sorted order:\n\n{}",
                        ecosystem.title, sorted_list
                    )),
                    sub_eco_diff: None,
                    github_org_diff: None,
                }));
            }

            // Check for duplicate URLs and missing repos
            for repo in repos {
                let lowercase_url = repo.url.to_lowercase();
                if seen_repos.contains(&lowercase_url) {
                    errors.push(ValidationError::DuplicateRepoUrl(repo.url.clone()));
                } else {
                    seen_repos.insert(lowercase_url);
                }
                if let Some(true) = repo.missing {
                    missing_count += 1;
                }
                repo_set.insert(repo.url.clone());
            }
        }

        if !(has_sub_ecosystems || has_orgs || has_repos) {
            errors.push(ValidationError::EmptyEcosystem(ecosystem.title.clone()));
        }
    }

    if errors.is_empty() {
        println!(
            "Validated {} ecosystems and {} repos ({} missing)",
            ecosystem_map.len(),
            repo_set.len(),
            missing_count,
        );
    }

    errors
}


fn validate(data_path: String) -> Result<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok((ecosystem_map, title_errors)) => {
            let mut errors = validate_ecosystems(&ecosystem_map);
            errors.extend(title_errors);
            if !errors.is_empty() {
                for err in errors {
                    print!("{}", err);
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

fn export(data_path: String, output_path: String, only_repos: bool) -> Result<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok((ecosystem_map, title_errors)) => {
            let mut errors = validate_ecosystems(&ecosystem_map);
            errors.extend(title_errors);
            if !errors.is_empty() {
                for err in errors {
                    println!("{}", err);
                }
                std::process::exit(-1);
            }
            if only_repos {
                let mut repo_set: HashMap<&String, Vec<String>> = HashMap::new();
                for ecosystem in ecosystem_map.values() {
                    if let Some(ref repositories) = ecosystem.repo {
                        for repo in repositories {
                            repo_set
                                .entry(&ecosystem.title)
                                .or_default()
                                .push(repo.url.clone());
                        }
                    }
                }
                serde_json::to_writer_pretty(File::create(output_path)?, &repo_set)?;
                return Ok(());
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

fn main() -> Result<()> {
    let args = Cli::from_args();
    match args {
        Cli::Validate { data_path } => {
            validate(data_path)?;
        }
        Cli::Export {
            data_path,
            output_path,
            only_repos,
        } => export(data_path, output_path, only_repos)?,
    }
    Ok(())
}
