# Crypto Ecosystems Taxonomy - Python Implementation

A Python implementation of the crypto-ecosystems taxonomy validation and export system, originally written in Zig. This implementation uses only the Python standard library (Python 3.10+).

## Features

- **Validate**: Validate all migration files and display statistics
- **Export**: Export the taxonomy to JSON Lines format
- **Date Filtering**: Export taxonomy state at specific past dates
- **Single Ecosystem Export**: Export only a specific ecosystem
- **Zero Dependencies**: Uses only Python standard library

## Installation

No installation required! Just use Python 3.10 or newer.

## Usage

### As a Python Module

```bash
# Validate migrations
python -m python validate

# Validate migrations from specific directory
python -m python validate -r /path/to/migrations

# Export all ecosystems
python -m python export output.json

# Export with custom migrations directory
python -m python export -r /path/to/migrations output.json

# Export single ecosystem
python -m python export -e Bitcoin bitcoin.json

# Export with date filter (state as of that date)
python -m python export -m 2015-01-01 historical.json

# Show help
python -m python --help

# Show version
python -m python version
```

### Running Tests

```bash
# Run all tests
python -m unittest discover tests/python -v

# Run specific test module
python -m unittest tests.python.test_taxonomy -v
python -m unittest tests.python.test_timestamp -v
python -m unittest tests.python.test_shlex_parser -v
```

## Commands

### validate

Validates all migrations in a directory and prints statistics.

**Options:**
- `-r, --root DIR`: Directory containing migration files (default: `./migrations`)
- `-h, --help`: Show help message

**Example Output:**
```
┃ 451    Migrations
┃ 7362   Ecosystems
┃ 557789 Repos
┃ 662    Tags
```

### export

Exports the taxonomy to a JSON Lines file.

**Options:**
- `-r, --root DIR`: Directory containing migration files (default: `./migrations`)
- `-e, --ecosystem STR`: Export only a specific ecosystem
- `-m, --max-date STR`: Maximum date to run migrations until (YYYY-MM-DD format)
- `<output>`: Output file path (required)

**JSON Lines Format:**

Each line is a JSON object representing a repository in an ecosystem:

```json
{"eco_name":"Bitcoin","branch":[],"repo_url":"https://github.com/bitcoin/bitcoin","tags":["#protocol"]}
{"eco_name":"Bitcoin","branch":["Lightning"],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}
```

The `branch` field shows the hierarchy path from the top-level ecosystem to the current location.

## Architecture

### Core Components

1. **timestamp.py** - Validates migration file timestamps (YYYY-MM-DDTHHMMSS format)
2. **shlex_parser.py** - Parses shell-like quoted arguments
3. **taxonomy.py** - Core taxonomy management with all data structures and operations
4. **commands.py** - CLI argument parsing and command execution
5. **__main__.py** - Module entry point

### Migration Commands

The system processes migration files with these commands:

- `ecoadd <name>` - Add an ecosystem
- `repadd <eco> <url> [tags...]` - Add a repository to an ecosystem
- `ecocon <parent> <child>` - Connect ecosystems (create hierarchy)
- `ecodis <parent> <child>` - Disconnect ecosystems
- `ecorem <name>` - Remove an ecosystem
- `repmov <old_url> <new_url>` - Rename/move a repository
- `ecomov <old_name> <new_name>` - Rename an ecosystem
- `reprem <eco> <url>` - Remove a repository from an ecosystem

### Data Structures

The Taxonomy class uses Python dictionaries and sets for efficient operations:

- String-to-ID mappings for ecosystems, repos, and tags
- ID-to-string reverse mappings
- Ecosystem-to-repos relationships
- Parent-to-children hierarchy
- Ecosystem-repo-to-tags associations

## Performance

The Python implementation efficiently handles large datasets:

- **Full validation**: 451 migrations, 7362 ecosystems, 557K+ repos in ~1 second
- **Full export**: 4.5M+ JSON lines exported successfully
- **Memory efficient**: Loads migration files incrementally

## Testing

Comprehensive test suite with 27 tests covering:

- Timestamp validation (valid/invalid dates, leap years, time components)
- Shell lexer (quotes, escapes, edge cases)
- All migration commands
- Hierarchical ecosystems
- Date filtering
- JSON export format
- Error handling

All tests use the same test fixtures as the Zig implementation.

## Compatibility

- **Python Version**: 3.10+ (uses modern type hints)
- **Platform**: Cross-platform (Linux, macOS, Windows)
- **Dependencies**: None (standard library only)
- **Output**: Byte-compatible with Zig implementation

## Development

### Project Structure

```
python/
├── __init__.py          # Package initialization
├── __main__.py          # Module entry point
├── commands.py          # CLI handler
├── taxonomy.py          # Core taxonomy logic
├── timestamp.py         # Timestamp validation
├── shlex_parser.py      # Shell lexer
└── README.md           # This file

tests/python/
├── __init__.py
├── test_timestamp.py    # Timestamp tests
├── test_shlex_parser.py # Lexer tests
└── test_taxonomy.py     # Taxonomy tests
```

### Code Style

The code follows Python best practices:

- Type hints for all functions
- Comprehensive docstrings
- PEP 8 style guide
- Clear error messages
- Efficient algorithms

## Differences from Zig Implementation

The Python implementation maintains functional compatibility while adapting to Python idioms:

1. **Memory Management**: Automatic garbage collection instead of manual allocation
2. **Data Structures**: Python dicts/sets instead of HashMap/AutoHashMap
3. **Error Handling**: Exception-based instead of error unions
4. **Type System**: Dynamic typing with type hints instead of compile-time types
5. **String Handling**: Unicode by default instead of UTF-8 bytes

## License

Same as the parent project.

## Version

2.0 - Matches the Zig implementation version.
