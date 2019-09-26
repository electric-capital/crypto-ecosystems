# Crypto Ecosystems
[![MIT license](http://img.shields.io/badge/license-MIT-brightgreen.svg)](http://opensource.org/licenses/MIT)
[![Build Status](https://dev.azure.com/electric-capital/crypto-ecosystems/_apis/build/status/electric-capital.crypto-ecosystems?branchName=master)](https://dev.azure.com/electric-capital/crypto-ecosystems/_build/latest?definitionId=1&branchName=master)
[![All Contributors](https://img.shields.io/badge/all_contributors-14-orange.svg?style=flat-square)](#contributors-)

🌲 Crypto Ecosystems is a taxonomy for sharing data around open source cryptocurrency, blockchain, and decentralized ecosystems and tying them to github organizations and code repositories.  All of the ecosystems are specified in [TOML](https://github.com/toml-lang/toml) configuration files.

This repository is not complete, and hopefully it never is as there are new ecosystems created everyday.

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

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/jubos"><img src="https://avatars3.githubusercontent.com/u/41347?v=4" width="100px;" alt="Curtis Spencer"/><br /><sub><b>Curtis Spencer</b></sub></a><br /><a href="https://github.com/electric-capital/crypto-ecosystems/commits?author=jubos" title="Code">💻</a> <a href="#content-jubos" title="Content">🖋</a> <a href="https://github.com/electric-capital/crypto-ecosystems/commits?author=jubos" title="Documentation">📖</a></td>
    <td align="center"><a href="https://github.com/mariashen"><img src="https://avatars2.githubusercontent.com/u/6494377?v=4" width="100px;" alt="Maria Shen"/><br /><sub><b>Maria Shen</b></sub></a><br /><a href="#content-mariashen" title="Content">🖋</a></td>
    <td align="center"><a href="https://github.com/puntium"><img src="https://avatars0.githubusercontent.com/u/20433492?v=4" width="100px;" alt="puntium"/><br /><sub><b>puntium</b></sub></a><br /><a href="#content-puntium" title="Content">🖋</a></td>
    <td align="center"><a href="http://timothymccallum.com.au"><img src="https://avatars2.githubusercontent.com/u/9831342?v=4" width="100px;" alt="Timothy McCallum"/><br /><sub><b>Timothy McCallum</b></sub></a><br /><a href="#content-tpmccallum" title="Content">🖋</a></td>
    <td align="center"><a href="https://ake.wtf"><img src="https://avatars1.githubusercontent.com/u/10195782?v=4" width="100px;" alt="Ake Gaviar"/><br /><sub><b>Ake Gaviar</b></sub></a><br /><a href="#content-akegaviar" title="Content">🖋</a></td>
    <td align="center"><a href="https://bitcoindev.network"><img src="https://avatars3.githubusercontent.com/u/7654306?v=4" width="100px;" alt="Gr0kchain"/><br /><sub><b>Gr0kchain</b></sub></a><br /><a href="#content-gr0kchain" title="Content">🖋</a></td>
    <td align="center"><a href="https://kincaidoneil.com"><img src="https://avatars1.githubusercontent.com/u/6435238?v=4" width="100px;" alt="Kincaid O'Neil"/><br /><sub><b>Kincaid O'Neil</b></sub></a><br /><a href="#content-kincaidoneil" title="Content">🖋</a></td>
  </tr>
  <tr>
    <td align="center"><a href="https://github.com/kristapsk"><img src="https://avatars2.githubusercontent.com/u/4500994?v=4" width="100px;" alt="Kristaps Kaupe"/><br /><sub><b>Kristaps Kaupe</b></sub></a><br /><a href="#content-kristapsk" title="Content">🖋</a></td>
    <td align="center"><a href="https://github.com/mike1729"><img src="https://avatars3.githubusercontent.com/u/4404982?v=4" width="100px;" alt="Michal Swietek"/><br /><sub><b>Michal Swietek</b></sub></a><br /><a href="#content-mike1729" title="Content">🖋</a></td>
    <td align="center"><a href="http://philippewang.info/"><img src="https://avatars0.githubusercontent.com/u/3776012?v=4" width="100px;" alt="Philippe Wang"/><br /><sub><b>Philippe Wang</b></sub></a><br /><a href="#content-pw374" title="Content">🖋</a></td>
    <td align="center"><a href="http://nethermind.io"><img src="https://avatars1.githubusercontent.com/u/498913?v=4" width="100px;" alt="Tomasz Kajetan Stańczak"/><br /><sub><b>Tomasz Kajetan Stańczak</b></sub></a><br /><a href="#content-tkstanczak" title="Content">🖋</a></td>
    <td align="center"><a href="https://github.com/gcharang"><img src="https://avatars3.githubusercontent.com/u/21151592?v=4" width="100px;" alt="gcharang"/><br /><sub><b>gcharang</b></sub></a><br /><a href="#content-gcharang" title="Content">🖋</a></td>
    <td align="center"><a href="https://github.com/pikatos"><img src="https://avatars3.githubusercontent.com/u/2621796?v=4" width="100px;" alt="pikatos"/><br /><sub><b>pikatos</b></sub></a><br /><a href="#content-pikatos" title="Content">🖋</a></td>
    <td align="center"><a href="https://github.com/benjyz"><img src="https://avatars3.githubusercontent.com/u/5390515?v=4" width="100px;" alt="Benjamin Cordes"/><br /><sub><b>Benjamin Cordes</b></sub></a><br /><a href="#content-benjyz" title="Content">🖋</a> <a href="https://github.com/electric-capital/crypto-ecosystems/commits?author=benjyz" title="Documentation">📖</a></td>
  </tr>
</table>

<!-- markdownlint-enable -->
<!-- prettier-ignore-end -->
<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
