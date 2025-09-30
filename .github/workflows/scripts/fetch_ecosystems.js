import fs from "fs";
import fetch from "node-fetch";

const ORG = "ethereum"; 
const API_URL = `https://api.github.com/orgs/${ORG}/repos?per_page=100`;

async function fetchRepos() {
  const res = await fetch(API_URL, {
    headers: { "User-Agent": "crypto-ecosystems" },
  });

  if (!res.ok) {
    console.error("Failed to fetch:", res.status, res.statusText);
    return [];
  }

  const data = await res.json();
  return data.map((repo) => ({
    name: repo.name,
    description: repo.description,
    url: repo.html_url,
    stars: repo.stargazers_count,
    language: repo.language,
  }));
}

async function main() {
  const repos = await fetchRepos();

  const ecosystems = {
    org: ORG,
    updated: new Date().toISOString(),
    repos,
  };

  fs.writeFileSync("ecosystems.json", JSON.stringify(ecosystems, null, 2));
  console.log(`✅ Updated ecosystems.json with ${repos.length} repos`);
}

main();
