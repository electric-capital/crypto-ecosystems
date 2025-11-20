<h3 align="center">
</h3>
Open Dev Data is a taxonomy of open source blockchain, web3, cryptocurrency, and decentralized ecosystems and their code repositories.  This dataset is not complete, and hopefully it never will be as there are new ecosystems and repositories created every day.

## How to use this taxonomy
The taxonomy can be used to generate the set of crypto ecosystems, their corresponding sub ecosystems, and repositories at a particular time.
### 🖼️ GUI Mode
You can use the taxonomy viewer at [Open Dev Data](https://opendevdata.org).  Here you can query for ecosystems and repos as well as export all of the repos for specific ecosystems.
<div align="center">
<img width="800" alt="image" src="https://github.com/user-attachments/assets/8003fa92-6874-42d8-a398-7b1741964498" />
</div>

### 💻 CLI Mode

## Installation

The easiest way to use the CLI tools is with `uvx` (no installation required):

```bash
# Run directly with uvx (downloads and runs the latest version)
uvx open-dev-data --help
```

Or install with `uv`:

```bash
# Install with uv
uv tool install open-dev-data

# Run after installation
open-dev-data --help
```

Alternatively, install from source:

```bash
# Clone the repository
git clone https://github.com/electric-capital/open-dev-data.git
cd open-dev-data

# Install with uv
uv sync

# Run commands
uv run open-dev-data --help
```

## Available Commands

### Taxonomy Commands

#### Validate
Validate all migrations in the taxonomy:
```bash
open-dev-data validate
open-dev-data validate -r ./migrations  # Specify custom migrations directory
```

#### Export
Export the taxonomy to JSON format:
```bash
# Export all ecosystems
open-dev-data export output.jsonl

# Export a single ecosystem
open-dev-data export -e Bitcoin bitcoin.jsonl

# Export with custom migrations directory
open-dev-data export -r ./migrations output.jsonl

# Export taxonomy state at a specific date
open-dev-data export -m 2023-12-31 output.jsonl
```

The export format is one json entry per line like the following:
```json
{"eco_name":"Bitcoin","branch":["Lightning"],"repo_url":"https://github.com/alexbosworth/balanceofsatoshis","tags":["#developer-tool"]}
{"eco_name":"Bitcoin","branch":["Lightning"],"repo_url":"https://github.com/bottlepay/lnd","tags":[]}
```
By using the branch attribute, you can see how particular repos are attributed to the parent ecosystem.

### Data Commands

#### Download
Download parquet files from the Open Dev Data manifest:
```bash
# Download all files to a directory (creates version-specific subfolder)
open-dev-data download -o ./data

# Download with 8 concurrent workers
open-dev-data download -o ./data -w 8

# Resume interrupted download (skips existing files with matching checksums)
open-dev-data download -o ./data --resume
```

Downloads are organized by version (e.g., `./data/20251119T124952/`) and validated using blake3 checksums.

#### Duckify
Import parquet files into a DuckDB database:
```bash
# Import all parquet files from a directory
open-dev-data duckify -i ./data/20251119T124952 -o odd.duckdb
```

DuckDB is a fantastic database product for local analytics.  Please reserve about 100GB to work with both the parquet files and duckdb.

#### TUI (Interactive SQL Interface)
Launch an interactive SQL interface powered by Harlequin:
```bash
# Download lite dataset and open interactive SQL interface
open-dev-data tui --lite

# Force refresh cached data
open-dev-data tui --lite --refresh

# Open existing DuckDB file
open-dev-data tui --db ./database.duckdb

# Clear cached data
open-dev-data tui --clear-cache
```

The TUI provides an interactive interface to explore the data with:
- SQL query editor with syntax highlighting
- Results viewer with sorting and filtering
- Schema browser
- Query history

## Quick Start Example

Here's a complete workflow to download and explore the data:

```bash
# 1. Download the lite dataset and launch interactive SQL interface
uvx open-dev-data tui --lite

# Or, for full control:

# 2. Download all parquet files
uvx open-dev-data download -o ./data --resume

# 3. Import into DuckDB
uvx open-dev-data duckify -i ./data/20251119T124952 -o ecosystem.duckdb --show-schema

# 4. Open in interactive SQL interface
uvx open-dev-data tui --db ecosystem.duckdb
```

## How to update the taxonomy
There is a domain specific language (DSL) containing the keywords that can make changes to the taxonomy.  You specify migrations by using files of the format
```bash
migrations/YYYY-MM-DDThhmmss_description_of_your_migration
```

The datetime format is a loosely ISO8601 but without the ':' characters to make them valid files on Windows.

Some examples migration filenames could be:
```bash
migrations/2009-01-03T181500_add_bitcoin
migrations/2015-07-30T152613_add_ethereum
```

Simply create your new migration and add changes to the taxonomy using the keywords discussed below.

## Data Format

### Example: Adding an ecosystem and connecting it.
```lua
-- Add ecosystems with the ecoadd keyword.  You can start a line with -- to denote a comment.
ecoadd Lightning
-- Add repos to ecosystems using the repadd keyword
repadd Lightning https://github.com/lightningnetwork/lnd #protocol
-- Connect ecosystems using the ecocon keyword.
-- The following connects Lighting as a sub ecosystem of Bitcoin.
ecocon Bitcoin Lighting
```
  
## License and Attribution

### Dual Licensing

**Open Dev Data** uses dual licensing to cover different types of content:

#### Code - MIT License
All software code in this project is licensed under the [MIT License](LICENSE-MIT.md).

This includes:
- All source code files (.py, .js, etc.)
- Scripts and build configurations
- Software libraries and modules

#### Data and Documentation - CC BY 4.0
All data, documentation, and creative works in this project are licensed under the [Creative Commons Attribution 4.0 International License (CC BY 4.0)](LICENSE-CC-BY.md).

This includes:
- Ecosystem taxonomy data and parquet files
- Documentation files
- Examples and tutorials

See the full [LICENSE.md](LICENSE.md) for complete details and disclaimers.

### How to Give Attribution for Open Dev Data

When using **Open Dev Data** in your project:

**For Code Usage (MIT License):**
- Include a copy of the MIT License
- Provide attribution to Electric Capital

**For Data Usage (CC BY 4.0):**

Attribution needs to have 3 components:

1. **Source**: "Open Dev Data by Electric Capital"
2. **Link**: https://github.com/electric-capital/open-dev-data
3. **License**: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)

**Optional but encouraged:**
Everyone in the crypto ecosystem benefits from additions to this repository.
It is a help to everyone to include an ask to contribute next to your attribution.

Sample request language: "If you're working in open source crypto, submit your repository here to be counted."

#### Sample Attribution

Data Source: [Open Dev Data by Electric Capital](https://github.com/electric-capital/open-dev-data)
License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

If you're working in open source crypto, submit your repository [here](https://github.com/electric-capital/open-dev-data) to be counted.