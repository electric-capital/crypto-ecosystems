**V1.2 UPDATE [2024]:** Read about the Crypto Ecosystems taxonomy's update to Version 1.2 [here](https://github.com/electric-capital/crypto-ecosystems/releases/tag/1.2).

# Crypto Ecosystems

[MIT license with attribution](https://github.com/electric-capital/crypto-ecosystems/blob/master/LICENSE)

🌲 Crypto Ecosystems is a taxonomy for sharing data around open source blockchain, Web3, cryptocurrency, and decentralized ecosystems and tying them to GitHub organizations and code repositories. All of the ecosystems are specified in [TOML](https://github.com/toml-lang/toml) configuration files.

## Table of Contents
- [Overview](#crypto-ecosystems)
- [How to Contribute](#how-to-contribute)
  - [Via Pull Request](#option-1-opening-a-pull-request)
  - [Via Form Submission](#option-2-complete-the-ecosystem-submission-form)
- [Attribution Guidelines](#how-to-give-attribution-for-usage-of-the-electric-capital-crypto-ecosystems)
- [Detailed Contribution Guide](#how-to-contribute-step-by-step-guide)
  - [Adding New Ecosystem](#option-1-adding-a-new-ecosystem-eg-blockchain)
  - [Adding Sub-ecosystem](#option-2-adding-a-new-sub-ecosystem)
  - [Adding Repository](#option-3-adding-a-new-repo-or-organization)
- [FAQ](#frequently-asked-questions)

This repository is not complete, and hopefully it never is as there are new ecosystems and repositories created every day.

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
github_organizations = ["https://github.com/bitcoin", "https://github.com/bitcoin-core", "https://github.com/bitcoinj", "https://github.com/btcsuite", "https://github.com/libbitcoin", "https://github.com/rust-bitcoin"]

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
3. Logo: [Link to logo](static/electric_capital_logo_transparent.png)

Optional:
Everyone in the crypto ecosystem benefits from additions to this repository.
It is a help to everyone to include an ask to contribute next to your attribution.

Sample request language: "If you’re working in open source crypto, submit your repository here to be counted."

<ins>Sample attribution</ins>

Data Source: [Electric Capital Crypto Ecosystems Mapping](https://github.com/electric-capital/crypto-ecosystems)

If you’re working in open source crypto, submit your repository [here](https://github.com/electric-capital/crypto-ecosystems) to be counted.

## How to Contribute (Step-by-Step Guide)

There are three types of contributions you can make to this data set:

1. Adding a new ecosystem (e.g. a new layer 1 blockchain)
2. Adding a new sub-ecosystem (e.g. a big organisation that has multiple repos within the above ecosystem)
3. Adding a new repo (e.g. an individual project within the ecosystem/sub-ecosystem) or organization

This may sound confusing. It is perhaps even more confusing because whilst there are these different data sources/structures, all of them sit within one directory (data/ecosystems) as `.toml` files.

To make things easier, we've made the following roadmap for you to follow depending on which of the above 3 types of contributions you're trying to make. 

### Option 1: Adding a new ecosystem (e.g. blockchain)

If you're adding a totally new ecosystem that has no parents (e.g. Cosmos/Ethereum), then follow this path. You're most likely adding a new L1 blockchain, so let's take the fictitious example of a new chain called `EasyA Chain`. Follow these steps:

1. Go to the `data/ecosystems` directory
2. Find the folder named the first letter of the ecosystem you're adding. Here, it's the letter `E` because our L1 is called `EasyA Chain`.
3. Open the folder
4. Inside the folder, create a new `.toml` file named after your L1 in kebab-case. Here, it will be called `easya-chain.toml`. The full path will now be `data/ecosystems/e/easya-chain.toml`.
5. Add the following 2 required fields:

```toml
# Required field number 1: Name of the ecosystem
title = "EasyA Chain"

# Required field number 2: List of associated GitHub organizations
github_organizations = ["https://github.com/EasyA-Tech"]
```
6. Make your PR! ✅

Remember that this is a hierarchy. If you're adding a Cosmos appchain, therefore, you should be following Option 2 below (since it will be a sub-ecosystem of Cosmos).

Please note: As a time saving measure, you **do not** need to add all the repos within your GitHub organizations to the `.toml` file as individual repos, because our system automatically fetches all repos within the organization.  These will be reflected in our periodic exports of our internal database of repos.

We will explain below when and why you should add repos to an ecosystem.

### Option 2: Adding a new sub-ecosystem

If you're adding a new sub-ecosystem (in other words, it has a parent, like a blockchain or a layer 0), then follow these steps. Again, we'll be using the fictitious `EasyA Chain` L1 blockchain as an example. However, this time, we'll be adding the new `EasyA Community Wallet` sub-ecosystem to it.

1. Go to the `data/ecosystems` directory
2. Find the folder named the first letter of the name of the ecosystem which the project you're adding is part of. Here, it's the letter `E` because our L1 is called `EasyA Chain`.
3. Open the folder. Here, it's the `E` folder.
4. Inside the folder, find the `.toml` file that has the ecosystem's name. Here, following our `EasyA Chain` example, it will be `easya-chain.toml`. The full path to the ecosystem will be `data/ecosystems/e/easya-chain.toml`.
5. Open this file. Inside the ecosystem file, you will see something that looks like this:

```toml
title = "EasyA Chain"

github_organizations = ["https://github.com/EasyA-Tech"]
```
6. You will then need to do one of two things.

    1. If there are no sub-ecosystems yet, add your sub-ecosystem by adding the following line:

    ```toml
    sub_ecosystems = ["EasyA Community Wallet"]
    ```

    2. If you see a line starting with `sub_ecosystems` already, then simple add your sub-ecosystem to the list:

    ```toml
    sub_ecosystems = ["Pre-existing Sub-Ecosystem", "EasyA Community Wallet"]
    ```
Overall, your file should then look something like this:

```toml
title = "EasyA Chain"

sub_ecosystems = ["EasyA Community Wallet"] # This is the line we changed

github_organizations = ["https://github.com/EasyA-Tech"]
```

7. Once you've added your sub-ecosystem's name to the parent ecosystem file, go back to the `data/ecosystems` directory.
8. This time, find the folder that is the first letter of the name of the sub-ecosystem you're adding. Here, it also happens to be the letter `E` because our sub-ecosystem is called `EasyA Community Wallet`.
9. Open the folder. Here, it's the `E` folder.
10. Inside the folder, create the `.toml` file that has the sub-ecosystem's name. Here, following our `EasyA Community Wallet` example, it will be `easya-community-wallet.toml`. The full path to the ecosystem will be `data/ecosystems/e/easya-community-wallet.toml`.
11. Add the following 2 required fields:

```toml
# Required field number 1: Name of the sub-ecosystem
title = "EasyA Community Wallet"

# Required field number 2: List of associated GitHub organizations
github_organizations = ["https://github.com/EasyA-Community-Wallet"]
```
12. Make your PR! ✅

If you prefer videos, you can also see the above steps done live [here](https://www.loom.com/share/f23aab8c675940a9998b228ea1e179b7).

If you've been following along closely, you'll have noticed that the steps after adding the sub-ecosystem to the parent ecosystem are exactly the same a Option 1 (adding a totally new ecosystem that has no parents). That's because this taxonomy is based on ancestry. Any sub-ecosystem is basically just an ecosystem in its own right (it's not like a sub-ecosystem is any less valuable). The ecosystem and sub-ecosystem dichotomy is merely there so we can see the relationship between different ecosystems. You can keep adding sub-ecosystems to sub-ecosystems ad infinitum (forever).


### Option 3: Adding a new repo or organization

The system automatically pulls in all repos listed under a GitHub organization within an ecosystem. For example, when the system sees the below ecosystem, it will automatically account for all the repos under the `EasyA-Tech` GitHub organization.

```toml
title = "EasyA Chain"

github_organizations = ["https://github.com/EasyA-Tech"]
```
So don't worry! You don't need to add every single repo if it's already part of an organization that's in the data set.

To add a new organization, simply append its full GitHub URL to the list of organizations in the associated ecosystem. Let's take the example of adding an organization with the URL `https://github.com/EasyA-Community` as part of the `EasyA Chain` ecosystem. 

You would follow these steps:

1. Go to the `data/ecosystems` directory
2. Find the folder named the first letter of the name of the ecosystem which the organization you're adding is part of. Here, it's the letter `E` because our ecosystem is called `EasyA Chain`.
3. Open the folder. Here, it's the `E` folder.
4. Inside the folder, find the `.toml` file that has the ecosystem's name. Here, following our `EasyA Chain` example, it will be `easya-chain.toml`. The full path to the ecosystem will be `data/ecosystems/e/easya-chain.toml`.
5. Open this file. Inside the ecosystem file, you will see something that looks like this:

```toml
title = "EasyA Chain"

github_organizations = ["https://github.com/EasyA-Tech"]
```
6. Simply add your GitHub organization URL to the list. Here, ours is `https://github.com/EasyA-Community` so we'll add that: 

```toml
title = "EasyA Chain"

github_organizations = ["https://github.com/EasyA-Tech", "https://github.com/EasyA-Community"]
```
7. Make your PR! ✅

When, then, should you add repos? You only need to add a repo directly to an ecosystem if:

1. ✅ It is not owned by a GitHub organization already listed in an ecosystem file (those `.toml` files) 
2. ✅ It is not itself an ecosystem/sub-ecosystem (in which case you'd be adding it as an ecosystem)

The types of projects that will commonly get added as individual repos are: 
- Documentation
- Wallets
- Utility Libraries
- Smaller protocols

Usually these will be repos created by the community (so not already accounted for under the ecosystem/sub-ecosystem GitHub organization). Use that as a rough heuristic here. If the repo you're adding is actually one of many repos all in the same ecosystem, and in fact the organization only contributes to that one ecosystem, then you should almost certainly be adding your organization instead.

If you're happy that you should be adding this repo, then here's how to do it. Let's take the example of a community contributor with the GitHub handle `Platonicsocrates` who's created a helper library for the `EasyA Chain` but also contributes to other projects (so we shouldn't add their whole organization/profile). Their repo URL `https://github.com/platonicsocrates/easya-helpers`. 

You would follow these steps to add it:

1. Go to the `data/ecosystems` directory
2. Find the folder named the first letter of the name of the ecosystem which the repo you're adding is part of. Here, it's the letter `E` because our ecosystem is called `EasyA Chain`.
3. Open the folder. Here, it's the `E` folder.
4. Inside the folder, find the `.toml` file that has the ecosystem's name. Here, following our `EasyA Chain` example, it will be `easya-chain.toml`. The full path to the ecosystem will be `data/ecosystems/e/easya-chain.toml`.
5. Open this file. Inside the ecosystem file, you will see something that looks like this:

```toml
title = "EasyA Chain"

github_organizations = ["https://github.com/EasyA-Tech"]
```
6. Simply add the following three lines at the end of the `.toml` file:

```toml
[[repo]]
url = "https://github.com/platonicsocrates/easya-helpers" # Replace this URL with your repo url
tags = [ "Library"] # This line is optional
```

If there are already other repos in the ecosystem, just add the above as new lines (unlike adding organizations or sub-ecosystems, these aren't lists). For example, if the ecosystem already has a repo, we will just add it below as follows:

```toml

# Repo that's already been added
[[repo]]
url = "https://github.com/platonicsocrates/easya-js"
tags = [ "Library"] 

# Our new repo
[[repo]]
url = "https://github.com/platonicsocrates/easya-helpers" # Replace this URL with your repo url
tags = [ "Library"] # This line is optional
```
7. Make your PR! ✅


Thank you for contributing and for reading the contribution guide! ❤️

## Frequently Asked Questions

### Q: What is considered a valid ecosystem?
A: An ecosystem can be any blockchain, protocol, platform or significant project in the crypto space that has multiple repositories or sub-projects associated with it.

### Q: How are sub-ecosystems different from regular ecosystems?
A: Sub-ecosystems are projects that are built on top of or are closely related to a parent ecosystem. For example, Lightning Network is a sub-ecosystem of Bitcoin.

### Q: Can I add multiple organizations to one ecosystem?
A: Yes, you can add as many relevant GitHub organizations as needed to an ecosystem. Just append them to the `github_organizations` list.

### Q: What tags should I use for repositories?
A: Common tags include: "Protocol", "Documentation", "Wallet", "Library", "Tools", "DeFi", "NFT", "Gaming". Choose tags that best describe the repository's purpose.
