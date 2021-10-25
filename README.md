# Crypto Ecosystems
[![MIT license](http://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT)
[![All Contributors](https://img.shields.io/badge/all_contributors-16-orange.svg?style=flat-square)](#contributors-)

🌲 Crypto Ecosystems is a taxonomy for sharing data around open source cryptocurrency, blockchain, and decentralized ecosystems and tying them to github organizations and code repositories.  All of the ecosystems are specified in [TOML](https://github.com/toml-lang/toml) configuration files.

This repository is not complete, and hopefully it never is as there are new ecosystems and repositories created everyday.

[Browse Ecosystems Here](https://electric-capital.github.io)

#### Data Format

An example configuration file for the Bitcoin ecosystem looks like this:

```toml
# Ecosystem Level Information
title = "Bitcoin"

# Sub Ecosystems
# These are the titles of other ecosystems in different .toml files in the /data/ecosystems directory
sub_ecosystems = [ "Lightning", "RSK Smart Bitcoin", "ZeroNet"]

# Github Organizations
# This is a list of links to associated github organizations.
github_organizations = ["https://github.com/bitcoin", "https://github.com/bitcoin-core", "https://github.com/bitcoinj", "https://github.com
/btcsuite", "https://github.com/libbitcoin", "https://github.com/rust-bitcoin"]

# Repositories
# These are structs including a url and tags for a git repository.  These URLS do not have to be on github.
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

#### How to Contribute

✍️ You can make any .toml file for an ecosystem in the /data/ecosystems directory or edit an existing one to help improve data around an ecosystem.  Pull Requests are encouraged. 
