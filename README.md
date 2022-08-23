# Crypto Ecosystems
[![MIT license](http://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT)

🌲 Crypto Ecosystems is a taxonomy for sharing data around open source blockchain, Web3, cryptocurrency, and decentralized ecosystems and tying them to GitHub organizations and code repositories.  All of the ecosystems are specified in [TOML](https://github.com/toml-lang/toml) configuration files.

This repository is not complete, and hopefully it never is as there are new ecosystems and repositories created everyday.

[Browse Ecosystems Here](https://electric-capital.github.io)

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
