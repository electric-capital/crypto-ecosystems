\# Contributing to Crypto Ecosystems



Thank you for your interest in contributing to Crypto Ecosystems! 🎉



This guide will help you add new ecosystems, repositories, and make improvements to the project.



\## Table of Contents

\- \[Getting Started](#getting-started)

\- \[Adding New Ecosystems](#adding-new-ecosystems)

\- \[Adding Repositories](#adding-repositories)

\- \[Connecting Ecosystems](#connecting-ecosystems)

\- \[Migration File Format](#migration-file-format)

\- \[Testing Your Changes](#testing-your-changes)

\- \[Submitting Your Contribution](#submitting-your-contribution)



\## Getting Started



1\. \*\*Fork the repository\*\* to your GitHub account

2\. \*\*Clone your fork\*\* locally:

&nbsp;  ```bash

&nbsp;  git clone https://github.com/YOUR\_USERNAME/crypto-ecosystems.git

&nbsp;  cd crypto-ecosystems

&nbsp;  ```

3\. \*\*Create a new branch\*\* for your changes:

&nbsp;  ```bash

&nbsp;  git checkout -b add-new-ecosystem

&nbsp;  ```



\## Adding New Ecosystems



To add a new ecosystem, create a migration file in the `migrations/` directory.



\### Migration File Naming Convention

```

migrations/YYYY-MM-DDThhmmss\_description\_of\_your\_migration

```



\*\*Example:\*\*

```

migrations/2025-10-03T153000\_add\_solana\_ecosystem

```



\### Migration File Content



Use the Domain Specific Language (DSL) keywords:



\#### 1. \*\*Add Ecosystem\*\* - `ecoadd`

```

-- Add a new ecosystem

ecoadd Solana

```



\#### 2. \*\*Add Repository\*\* - `repadd`

```

-- Add repositories to the ecosystem

repadd Solana https://github.com/solana-labs/solana #protocol

repadd Solana https://github.com/project-serum/serum-dex #defi

```



\*\*Available Tags:\*\*

\- `#protocol` - Core protocol repositories

\- `#defi` - Decentralized Finance

\- `#nft` - Non-Fungible Tokens

\- `#wallet` - Wallet implementations

\- `#developer-tool` - Development tools

\- `#bridge` - Cross-chain bridges

\- `#oracle` - Oracle services

\- `#dao` - Decentralized Autonomous Organizations



\#### 3. \*\*Connect Ecosystems\*\* - `ecocon`

```

-- Connect sub-ecosystems to parent ecosystems

ecocon Ethereum Uniswap

ecocon Bitcoin Lightning

```



\### Complete Example Migration File



\*\*File:\*\* `migrations/2025-10-03T153000\_add\_solana\_ecosystem`



```

-- Add Solana ecosystem

ecoadd Solana



-- Add core protocol repos

repadd Solana https://github.com/solana-labs/solana #protocol

repadd Solana https://github.com/solana-labs/solana-program-library #protocol



-- Add DeFi projects

repadd Solana https://github.com/project-serum/serum-dex #defi

repadd Solana https://github.com/solana-labs/solana-web3.js #developer-tool



-- Add sub-ecosystem

ecoadd Serum

repadd Serum https://github.com/project-serum/serum-ts #developer-tool

ecocon Solana Serum

```



\## Adding Repositories



If you want to add repositories to an \*\*existing ecosystem\*\*, simply create a migration file with `repadd` commands:



\*\*File:\*\* `migrations/2025-10-03T154500\_add\_ethereum\_repos`



```

-- Add new Ethereum repositories

repadd Ethereum https://github.com/ethereum/go-ethereum #protocol

repadd Ethereum https://github.com/OpenZeppelin/openzeppelin-contracts #developer-tool

repadd Ethereum https://github.com/Uniswap/v3-core #defi

```



\## Connecting Ecosystems



To establish parent-child relationships between ecosystems:



```

-- Polygon is a sub-ecosystem of Ethereum

ecoadd Polygon

ecocon Ethereum Polygon



-- Optimism is a Layer 2 of Ethereum

ecoadd Optimism

ecocon Ethereum Optimism

```



\## Migration File Format



\### Rules:

1\. \*\*Comments\*\* start with `--`

2\. \*\*One command per line\*\*

3\. \*\*Datetime format:\*\* `YYYY-MM-DDThhmmss` (ISO 8601 without colons)

4\. \*\*No special characters\*\* in filenames except underscore `\_`

5\. \*\*Descriptive names\*\* for clarity



\### Good Examples:

```

migrations/2025-10-03T120000\_add\_bitcoin\_lightning

migrations/2025-10-03T130000\_add\_defi\_protocols

migrations/2025-10-03T140000\_connect\_layer2\_networks

```



\### Bad Examples:

```

migrations/2025-10-03\_new\_stuff

migrations/add\_repos

migrations/2025:10:03T12:00:00\_update

```



\## Testing Your Changes



Before submitting, test your migration:



\### On Linux/Mac:

```bash

./run.sh export test\_output.jsonl

```



\### On Windows:

```bash

\# Install Zig if not already installed

\# Then run:

zig build run -- export test\_output.jsonl

```



Check if your changes appear in the output:

```bash

\# On Linux/Mac

cat test\_output.jsonl | grep "your\_ecosystem\_name"



\# On Windows

findstr "your\_ecosystem\_name" test\_output.jsonl

```



\## Submitting Your Contribution



1\. \*\*Commit your changes:\*\*

&nbsp;  ```bash

&nbsp;  git add migrations/

&nbsp;  git commit -m "Add Solana ecosystem with core repositories"

&nbsp;  ```



2\. \*\*Push to your fork:\*\*

&nbsp;  ```bash

&nbsp;  git push origin add-new-ecosystem

&nbsp;  ```



3\. \*\*Create a Pull Request:\*\*

&nbsp;  - Go to the original repository on GitHub

&nbsp;  - Click "New Pull Request"

&nbsp;  - Select your branch

&nbsp;  - Fill in the PR template with:

&nbsp;    - \*\*Description:\*\* What ecosystems/repos you added

&nbsp;    - \*\*Motivation:\*\* Why they should be included

&nbsp;    - \*\*Testing:\*\* Confirm you tested the migration



4\. \*\*PR Title Format:\*\*

&nbsp;  ```

&nbsp;  Add \[Ecosystem Name] ecosystem

&nbsp;  Add repositories to \[Ecosystem Name]

&nbsp;  Connect \[Child] to \[Parent] ecosystem

&nbsp;  ```



\## Quality Guidelines



\### Repository Requirements:

\- ✅ Must be \*\*open source\*\*

\- ✅ Must be related to \*\*blockchain/crypto/web3\*\*

\- ✅ Must be \*\*actively maintained\*\* (or historically significant)

\- ✅ Must have a \*\*valid GitHub URL\*\*

\- ❌ No private repositories

\- ❌ No spam or low-quality projects



\### Ecosystem Requirements:

\- ✅ Must be a \*\*recognized blockchain ecosystem\*\*

\- ✅ Must have multiple \*\*active repositories\*\*

\- ✅ Must be \*\*publicly documented\*\*



\## Need Help?



\- 📖 Check the \[README.md](README.md) for usage examples

\- 🐛 Report bugs in \[Issues](https://github.com/PROFADAM/crypto-ecosystems/issues)

\- 💬 Ask questions in \[Discussions](https://github.com/PROFADAM/crypto-ecosystems/discussions)

\- 📧 Contact: \[Your Contact Info]



\## Code of Conduct



\- Be respectful and constructive

\- Focus on the technology, not personal opinions

\- Provide accurate information

\- Help others learn and contribute



\## License



By contributing, you agree that your contributions will be licensed under the MIT License.



---



Thank you for helping build the most comprehensive crypto ecosystem taxonomy! 🚀

