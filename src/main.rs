use anyhow::Result;
use glob::glob;
use imara_diff::intern::InternedInput;
use imara_diff::{diff, Algorithm, UnifiedDiffBuilder};
use serde::{Deserialize, Serialize};
use slug::slugify;
use std::collections::{HashMap, HashSet};
use std::fmt::{Display, Formatter};
use std::fs::OpenOptions;
use std::fs::{read_to_string, File};
use std::io::prelude::*;
use std::path::{Path, PathBuf};
use structopt::StructOpt;
use thiserror::Error;

const MAX_LINE_LENGTH: usize = 80;

#[derive(Debug, StructOpt)]
#[structopt(about = "Taxonomy of crypto open source repositories")]
#[structopt(name = "crypto-ecosystems", rename_all = "kebab-case")]
enum Cli {
    /// Sort all of the toml files
    Sort {
        /// Path to top level directory containing ecosystem toml files
        data_path: String,
    },

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

struct ValidationStats {
    ecosystem_count: usize,
    repo_count: usize,
    missing_count: usize,
    errors: Vec<ValidationError>,
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

fn validate_ecosystems(ecosystem_map: &EcosystemMap) -> ValidationStats {
    let mut errors = vec![];
    let mut repo_set = HashSet::new();
    let mut tagmap: HashMap<String, u32> = HashMap::new();
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

        //let mut sorted_subs = vec![];
        let mut sort_error = UnsortedEcosystem {
            ecosystem: ecosystem.title.clone(),
            repo_diff: None,
            sub_eco_diff: None,
            github_org_diff: None,
        };
        if let Some(sub_ecosystems) = &ecosystem.sub_ecosystems {
            for sub in sub_ecosystems {
                if !ecosystem_map.contains_key(sub) {
                    errors.push(ValidationError::MissingSubecosystem {
                        parent: ecosystem.title.clone(),
                        child: sub.clone(),
                    });
                }
            }
            sort_error.sub_eco_diff = find_misordered_elements_diff(sub_ecosystems);
        }

        if let Some(github_orgs) = &ecosystem.github_organizations {
            sort_error.github_org_diff = find_misordered_elements_diff(github_orgs);
        }

        if let Some(repos) = &ecosystem.repo {
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
                if let Some(tags) = &repo.tags {
                    for tag in tags {
                        let counter = tagmap.entry(tag.to_string()).or_insert(0);
                        *counter += 1;
                    }
                }
                let url_type = parse_repo_url_type(&repo.url);
                match url_type {
                    RepoUrlType::GithubUnnormalized
                    | RepoUrlType::GithubTreeish
                    | RepoUrlType::GithubUserOrOrganization
                    | RepoUrlType::InvalidUrl => errors.push(ValidationError::InvalidRepoUrl {
                        url: repo.url.clone(),
                        url_type,
                    }),
                    _ => {}
                }
            }
            let repo_urls: Vec<String> = repos.iter().map(|x| x.url.clone()).collect();
            sort_error.repo_diff = find_misordered_elements_diff(&repo_urls);
        }

        if !(has_sub_ecosystems || has_orgs || has_repos) {
            errors.push(ValidationError::EmptyEcosystem(ecosystem.title.clone()));
        }

        if sort_error.sub_eco_diff.is_some()
            || sort_error.github_org_diff.is_some()
            || sort_error.repo_diff.is_some()
        {
            errors.push(ValidationError::UnsortedEcosystem(sort_error));
        }
    }

    ValidationStats {
        ecosystem_count: ecosystem_map.len(),
        repo_count: repo_set.len(),
        missing_count,
        errors,
    }
}

fn canonical_path(repo_root: &Path, eco_title: &str) -> PathBuf {
    let slug = slugify(eco_title);
    if slug.is_empty() {
        panic!("Empty Slug for {}", eco_title);
    }
    repo_root
        .join("ecosystems")
        .join(&slug[..1])
        .join(format!("{}.toml", &slug))
}

fn write_ecosystem_to_toml(repo_root: &Path, eco: &Ecosystem) -> Result<()> {
    let toml_file_path = canonical_path(repo_root, &eco.title);
    let mut output = String::new();
    output.push_str(&format!(
        "# Ecosystem Level Information\ntitle = \"{}\"\n\n",
        eco.title
    ));

    let mut sub_eco_vec: Vec<String> = eco.sub_ecosystems.iter().flatten().cloned().collect();
    sub_eco_vec.sort_by_key(|k| k.to_lowercase());
    let mut sub_ecosystems = String::new();
    serde::Serialize::serialize(
        &sub_eco_vec,
        toml::ser::ValueSerializer::new(&mut sub_ecosystems),
    )
    .expect("Valid sub ecosystems");
    if sub_ecosystems.len() > MAX_LINE_LENGTH {
        let mut sub_eco_string = String::from("sub_ecosystems = [\n");
        for sub in sub_eco_vec {
            sub_eco_string.push_str(&format!("  \"{}\",\n", sub));
        }
        sub_eco_string.push_str("]\n\n");
        output.push_str(&sub_eco_string);
    } else {
        output.push_str(&format!("sub_ecosystems = {}\n\n", sub_ecosystems));
    }

    let mut github_org_vec: Vec<String> =
        eco.github_organizations.iter().flatten().cloned().collect();
    github_org_vec.sort_by_key(|k| k.to_lowercase());
    let mut github_orgs = String::new();
    serde::Serialize::serialize(
        &github_org_vec,
        toml::ser::ValueSerializer::new(&mut github_orgs),
    )
    .expect("Valid github organizations");
    if github_orgs.len() > MAX_LINE_LENGTH {
        let mut github_org_string = String::from("github_organizations = [\n");
        for org in github_org_vec {
            github_org_string.push_str(&format!("  \"{}\",\n", org));
        }
        github_org_string.push_str("]\n\n");
        output.push_str(&github_org_string);
    } else {
        output.push_str(&format!("github_organizations = {}\n\n", github_orgs));
    }

    output.push_str("# Repositories\n");
    let mut sorted_repos: Vec<&Repo> = eco.repo.iter().flatten().collect();
    sorted_repos.sort_by_key(|k| k.url.to_lowercase());
    let mut i = 0;
    let mut included = HashSet::new();
    for repo in &sorted_repos {
        if included.contains(&repo.url.to_lowercase()) {
            continue;
        }
        included.insert(repo.url.to_lowercase());
        output.push_str(&format!("[[repo]]\nurl = \"{}\"\n", repo.url));
        if let Some(ref tags) = repo.tags {
            if !tags.is_empty() {
                let mut tag_toml = String::new();
                serde::Serialize::serialize(&tags, toml::ser::ValueSerializer::new(&mut tag_toml))
                    .expect("Valid tags");
                output.push_str(&format!("tags = {}\n", tag_toml));
            }
        }
        if let Some(true) = repo.missing {
            output.push_str("missing = true\n");
        }
        i += 1;
        if i < sorted_repos.len() {
            output.push('\n');
        }
    }

    if std::fs::create_dir_all(toml_file_path.parent().unwrap()).is_err() {
        println!("Error Making dir: {:?}", toml_file_path);
    }
    let mut file = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(true)
        .open(toml_file_path)?;
    file.write_all(output.as_bytes())?;
    Ok(())
}

fn validate(data_path: String) -> Result<()> {
    let toml_files = get_toml_files(Path::new(&data_path))?;
    match parse_toml_files(&toml_files) {
        Ok((ecosystem_map, title_errors)) => {
            let mut stats = validate_ecosystems(&ecosystem_map);
            stats.errors.extend(title_errors);
            if stats.errors.is_empty() {
                println!(
                    "Validated {} ecosystems and {} repos ({} missing)",
                    stats.ecosystem_count, stats.repo_count, stats.missing_count,
                );
            } else {
                for err in stats.errors {
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
            let mut stats = validate_ecosystems(&ecosystem_map);
            stats.errors.extend(title_errors);
            if !stats.errors.is_empty() {
                for err in stats.errors {
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

fn sort(data_path_str: &str) -> Result<()> {
    let data_path = Path::new(data_path_str);
    let toml_files = get_toml_files(data_path)?;
    match parse_toml_files(&toml_files) {
        Ok((ecosystem_map, title_errors)) => {
            let mut unsorted_count = 0;
            if !title_errors.is_empty() {
                println!("Please fix the following errors before sorting");
                for err in title_errors {
                    print!("\t{}", err);
                }
                std::process::exit(-1);
            }
            let stats = validate_ecosystems(&ecosystem_map);
            for error in stats.errors {
                if let ValidationError::UnsortedEcosystem(unsorted_eco) = error {
                    println!("Sorting Ecosystem: {}", unsorted_eco.ecosystem);
                    if let Some(eco) = ecosystem_map.get(&unsorted_eco.ecosystem) {
                        write_ecosystem_to_toml(data_path, eco)?;
                    }
                    unsorted_count += 1;
                }
            }
            if unsorted_count == 0 {
                println!("All ecosystems sorted");
            }
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
        Cli::Sort { data_path } => {
            sort(&data_path)?;
        }
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
