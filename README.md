# Crypto Ecosystems

[MIT license with attribution](https://github.com/electric-capital/crypto-ecosystems/blob/master/LICENSE)

🌲 Crypto Ecosystems is a taxonomy for sharing data around open source blockchain, Web3, cryptocurrency, and decentralized ecosystems and tying them to GitHub organizations and code repositories. All of the ecosystems are specified in [TOML](https://github.com/toml-lang/toml) configuration files.

This repository is not complete, and hopefully it never is as there are new ecosystems and repositories created everyday.

## How to Contribute

There's a couple of ways you can help grow this initiative.

### Option 1: Opening a Pull Request

You can make any .toml file for an ecosystem under the `/data/ecosystems` directory or edit an existing one to help improve data around an ecosystem.

You can fork this repository and open a PR from the forked repo to this repo. If you are not sure how to do that, you can follow the tutorial [in this video](https://www.loom.com/share/f23aab8c675940a9998b228ea1e179b7).

#### Data Format

An example configuration file for the Bitcoin ecosystem looks like this:

```toml
# Ecosystem Level Information
title = "Bitcoin"

# Sub Ecosystems
# These are the titles of other ecosystems in different .toml files in the /data/ecosystems directory
sub_ecosystems = [ "Lightning", "RSK Smart Bitcoin", "ZeroNet"]

# GitHub Organizations
# This is a list of links to associated GitHub organizations.
github_organizations = ["https://github.com/bitcoin", "https://github.com/bitcoin-core", "https://github.com/bitcoinj", "https://github.com
/btcsuite", "https://github.com/libbitcoin", "https://github.com/rust-bitcoin"]

# Repositories
# These are structs including a url and tags for a git repository. These URLs do not necessarily have to be on GitHub.
[[repo]]
url = "https://github.com/bitcoin/bitcoin"
tags = [ "Protocol"]

[[repo]]
url = "https://github.com/bitcoinbook/bitcoinbook"
tags = [ "Documentation"]

[[repo]]
url = "https://github.com/bitcoin-wallet/bitcoin-wallet"
tags = [ "Wallet"]

```

By specifying the data as evolving config files in git, we benefit from a long term, auditable database that is both human and machine readable.

### Option 2: Complete the Ecosystem Submission form

If you are not a developer or you find making a commit too difficult, you can use this Airtable based alternative below.

You can [visit the form here](https://airtable.com/shrN4vZMlBLm3Dap8), fill it, submit it and we'll take care of the rest :)

## How to Give Attribution For Usage of the Electric Capital Crypto Ecosystems

To use the Electric Capital Crypto Ecosystems Map, you will need an attribution.

Attribution needs to have 3 components:

1. Source: “Electric Capital Crypto Ecosystems Mapping”
2. Link: https://github.com/electric-capital/crypto-ecosystems
3. Logo: [Link to logo](https://drive.google.com/file/d/1DAX6wmcbtia7kaP5AaUWyg6t-ZEW9z22/view?usp=sharing)

Optional:
Everyone in the crypto ecosystem benefits from additions to this repository.
It is a help to everyone to include an ask to contribute next to your attribution.

Sample request language: "If you’re working in open source crypto, submit your repository here to be counted."

<ins>Sample attribution</ins>

Data Source: [Electric Capital Crypto Ecosystems Mapping](https://github.com/electric-capital/crypto-ecosystems)

If you’re working in open source crypto, submit your repository [here](https://github.com/electric-capital/crypto-ecosystems) to be counted.
