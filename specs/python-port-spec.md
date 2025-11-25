# Python Port Specification: Taxonomy Validation and Export

## Overview

This specification describes how to port the Zig-based crypto-ecosystems taxonomy validation and export system to Python, using the Python standard library wherever possible.

## Architecture

The system consists of three main components:

1. **CLI Command Handler** - Parses and executes user commands
2. **Taxonomy Core** - Manages ecosystem/repository relationships and migration processing
3. **Utilities** - Helper functions for timestamp validation and shell-like lexing

## 1. CLI Command Handler (commands.py)

### Purpose
Parse command-line arguments and dispatch to appropriate handlers.

### Commands

#### validate
Validates all migrations in a directory and prints statistics.

**Options:**
- `-r, --root DIR`: Directory containing migration files (default: `./migrations`)
- `-h, --help`: Show help message

**Output:**
```
┃ N      Migrations
┃ N      Ecosystems
┃ N      Repos
┃ N      Tags
```

#### export
Exports the taxonomy to a JSON Lines file.

**Options:**
- `-r, --root DIR`: Directory containing migration files (default: `./migrations`)
- `-e, --ecosystem STR`: Export only a specific ecosystem
- `-m, --max-date STR`: Maximum date to run migrations until (YYYY-MM-DD format)
- `<output>`: Output file path (required, positional argument)

**Output Format:**
JSON Lines with each line containing:
```json
{
  "eco_name": "Bitcoin",
  "branch": ["Lightning", "Lightspark"],
  "repo_url": "https://github.com/...",
  "tags": ["#protocol", "#sdk"]
}
```

### Implementation Details

**Standard Library Modules:**
- `argparse`: Command-line argument parsing
- `sys`: Exit codes and stderr output
- `os.path`: Path operations

**Error Handling:**
- `MissingOutputPath`: When export command lacks output file
- `InvalidCommand`: Unknown command
- `InvalidOption`: Invalid option provided
- `DuplicateOption`: Option specified multiple times

**Argument Parsing:**
- Use `argparse.ArgumentParser` with subparsers for each command
- Validate that options aren't duplicated (track with seen flags)
- For export command, ensure output path is provided and is the last argument
- Validate that option values don't start with `-`

## 2. Taxonomy Core (taxonomy.py)

### Data Structures

Use dictionaries and sets to represent the taxonomy:

```python
class Taxonomy:
    def __init__(self):
        self.eco_auto_id: int = 0
        self.repo_auto_id: int = 0
        self.tag_auto_id: int = 0
        self.migration_count: int = 0

        # String to ID mappings
        self.eco_ids: dict[str, int] = {}
        self.repo_ids: dict[str, int] = {}
        self.tag_ids: dict[str, int] = {}

        # ID to string mappings
        self.tag_id_to_name: dict[int, str] = {}
        self.repo_id_to_url: dict[int, str] = {}
        self.eco_id_to_name: dict[int, str] = {}

        # Relationship mappings
        self.eco_to_repos: dict[int, set[int]] = {}
        self.repo_to_eco: dict[int, int] = {}
        self.parent_to_children: dict[int, set[int]] = {}
        self.child_to_parents: dict[int, set[int]] = {}
        self.eco_repo_to_tags: dict[tuple[int, int], set[int]] = {}

        # Error tracking
        self.errors: list[dict] = []
```

### Migration Commands

The system processes migration files with the following commands:

1. **ecoadd** `<ecosystem_name>`
   - Adds a new ecosystem to the taxonomy

2. **repadd** `<ecosystem_name>` `<repo_url>` `[<tag1>] [<tag2>] ...`
   - Adds a repository to an ecosystem with optional tags

3. **ecocon** `<parent_ecosystem>` `<child_ecosystem>`
   - Connects a child ecosystem to a parent (creates hierarchy)

4. **ecodis** `<parent_ecosystem>` `<child_ecosystem>`
   - Disconnects a child ecosystem from a parent

5. **ecorom** `<ecosystem_name>`
   - Removes an ecosystem (preserves child ecosystems as orphans)

6. **repmov** `<old_repo_url>` `<new_repo_url>`
   - Renames/moves a repository URL

7. **ecomov** `<old_ecosystem_name>` `<new_ecosystem_name>`
   - Renames an ecosystem

8. **reprem** `<ecosystem_name>` `<repo_url>`
   - Removes a repository from an ecosystem

### Load Process

```python
def load(self, root_dir: str, max_date: str | None = None) -> None:
    """
    Load and process migration files from root_dir.

    Steps:
    1. List all files in directory
    2. Filter files with valid timestamps (YYYY-MM-DDTHHMMSS format)
    3. If max_date provided, filter files before that date
    4. Sort files by timestamp (first 19 characters)
    5. Process each file line by line
    6. Track errors during processing
    7. If errors exist, print them and raise ValidationFailed
    """
```

**Standard Library Modules:**
- `os`: Directory listing with `os.listdir()`
- `os.path`: Path joining with `os.path.join()`
- `re`: Pattern matching for timestamp validation (optional, can use string slicing)

**File Processing:**
- Read entire file into memory
- Split by newlines
- Skip comment lines (lines starting with `#` after whitespace)
- Skip lines shorter than 6 characters
- Parse command (first 6 characters) and remainder
- Execute appropriate command handler
- Catch exceptions and append to errors list with line number and path

### Export Process

```python
def export_json(self, output_file: str, ecosystem: str | None = None) -> None:
    """
    Export taxonomy to JSON Lines format.

    Steps:
    1. Collect ecosystems to export (all or specific one)
    2. Sort ecosystems alphabetically (case-insensitive)
    3. For each ecosystem, emit repositories and recursively emit sub-ecosystems
    4. Write to file using buffered I/O
    """
```

**Standard Library Modules:**
- `json`: JSON serialization with `json.dumps()`
- `io`: Buffered file writing for performance

**Output Format:**
- One JSON object per line (JSON Lines format)
- Each object represents a repository in an ecosystem
- `branch` field shows the hierarchy path from top ecosystem to current level
- Repositories and sub-ecosystems sorted case-insensitively

**Recursive Emission:**
- Emit all repositories at current ecosystem level
- For each sub-ecosystem:
  - Append sub-ecosystem name to branch list
  - Recursively emit that sub-ecosystem
  - Pop from branch list

### Statistics

```python
def stats(self) -> dict:
    """
    Return statistics about the taxonomy.

    Returns:
        {
            'migration_count': int,
            'eco_count': int,
            'repo_count': int,
            'tag_count': int
        }
    """
```

## 3. Utilities

### Timestamp Validation (timestamp.py)

```python
def has_valid_timestamp(filename: str) -> bool:
    """
    Validate that filename starts with YYYY-MM-DDTHHMMSS format.

    Validation rules:
    - Minimum length of 17 characters
    - Pattern: YYYY-MM-DDTHHMMSS where Y/M/D/H/M/S are digits
    - Hyphens at positions 4 and 7
    - 'T' at position 10
    - Month: 1-12
    - Day: 1-31 (adjusted for month and leap years)
    - Hour: 0-23
    - Minute: 0-59
    - Second: 0-59

    Returns:
        True if filename has valid timestamp prefix, False otherwise
    """
```

**Standard Library Modules:**
- `datetime`: Use `datetime.date(year, month, day)` to validate date components
- String slicing for parsing components
- `str.isdigit()` for character validation

**Leap Year Handling:**
```python
def is_leap_year(year: int) -> bool:
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
```

### Shell-like Lexer (shlex_parser.py)

```python
def split(line: str) -> list[str]:
    """
    Split a line into tokens, handling quotes and escapes.

    Rules:
    - Whitespace separates tokens
    - Single quotes (') and double quotes (") group tokens
    - Backslash (\) escapes the next character
    - Quotes are removed from tokens
    - Escaped characters have backslash removed

    Raises:
        ValueError: If quotes are unterminated

    Returns:
        List of parsed tokens
    """
```

**Standard Library Modules:**
- `shlex`: Python's built-in shell lexer module
  - Use `shlex.split()` for basic functionality
  - Configure with `posix=True` for proper escaping

**Alternative Implementation:**
If `shlex.split()` doesn't match exact Zig behavior, implement manually:
- Iterate character by character
- Track state: in_quote, escape_next, current_token
- Build tokens character by character
- Handle quote pairs and escape sequences

## 4. Error Handling

### Error Structure

```python
@dataclass
class TaxonomyError:
    message: str
    line_num: int
    path: str
```

### Error Types

All errors should be implemented as custom exceptions:

```python
class TaxonomyException(Exception):
    pass

class ValidationFailed(TaxonomyException):
    pass

class InvalidEcosystem(TaxonomyException):
    pass

class InvalidParentEcosystem(TaxonomyException):
    pass

class InvalidChildEcosystem(TaxonomyException):
    pass

# ... etc for all error types
```

### Error Reporting

When errors are detected during validation:
1. Collect all errors during processing
2. Print errors to stderr in format: `{path}:{line_num}: error.{error_name}`
3. Raise `ValidationFailed` exception
4. Exit with non-zero exit code

## 5. Testing Strategy

### Unit Tests

Use `unittest` module from standard library:

```python
import unittest
import tempfile
import os

class TestTaxonomy(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        # Clean up temp directory
        pass

    def test_load_single_ecosystem(self):
        # Create test migration file
        # Load taxonomy
        # Assert stats

    def test_export_json(self):
        # Load test data
        # Export to temp file
        # Read and verify JSON content

    # ... more tests
```

**Test Coverage:**
- Timestamp validation (valid/invalid dates, leap years)
- Shell lexer (quotes, escapes, edge cases)
- Each migration command (ecoadd, repadd, etc.)
- Error handling (invalid commands, duplicate options)
- JSON export format (hierarchy, sorting, tags)
- Date filtering during load
- Ecosystem relationships (parent/child, disconnect)

## 6. Implementation Notes

### Performance Considerations

1. **File I/O**: Use buffered I/O for export (`io.BufferedWriter`)
2. **Memory**: Load migration files into memory (files are typically small)
3. **Sorting**: Use `sorted()` with case-insensitive key for ecosystem/repo ordering
4. **Sets**: Use `set` for repo/ecosystem relationships (O(1) lookups)

### Python Standard Library Equivalents

| Zig Feature | Python Equivalent |
|-------------|-------------------|
| `ArrayList` | `list` |
| `HashMap` | `dict` |
| `AutoHashMap` | `dict` |
| `std.mem.sort` | `sorted()` |
| `std.fs.cwd().openDir()` | `os.listdir()` |
| `std.json.stringify()` | `json.dumps()` |
| `std.mem.eql` | `==` operator |
| `std.mem.startsWith` | `str.startswith()` |
| `std.ascii.isWhitespace` | `str.isspace()` |
| `std.heap.page_allocator` | Automatic (GC) |

### Color Output

For colored terminal output (magenta `┃` character):
```python
MAGENTA = '\x1b[35m'
RESET = '\x1b[0m'
print(f"{MAGENTA}┃{RESET} {count:<6} Migrations")
```

### Case-Insensitive Sorting

```python
sorted(items, key=str.casefold)  # Proper Unicode case-folding
# OR
sorted(items, key=str.lower)     # Simple lowercase
```

## 7. Entry Point

```python
# main.py
import sys
from commands import main

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
```

## 8. Project Structure

```
crypto-ecosystems/
├── migrations/          # Migration files (input)
├── src/                 # Zig source (reference)
├── python/              # Python implementation
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── commands.py      # CLI handler
│   ├── taxonomy.py      # Core taxonomy logic
│   ├── timestamp.py     # Timestamp validation
│   └── shlex_parser.py  # Shell lexer (if needed)
└── tests/               # Test fixtures
    └── python/          # Python tests
        ├── __init__.py
        └── test_taxonomy.py
```

## 9. Dependencies

**Required:** None (Python 3.10+ standard library only)

**Optional:**
- `pytest`: For more advanced testing features (if preferred over `unittest`)
- `mypy`: For type checking

## 10. Compatibility Notes

### String Handling
- Python strings are Unicode by default (Zig uses UTF-8 bytes)
- Use UTF-8 encoding when reading/writing files: `open(file, 'r', encoding='utf-8')`

### Integer IDs
- Use `int` type (arbitrary precision in Python)
- No overflow concerns like in Zig's `u32`

### Dictionary Ordering
- Python 3.7+ dicts maintain insertion order
- Use this for predictable iteration when needed

## 11. Migration Commands Reference

### Command Format

Each line in a migration file follows the format:
```
<command> <arguments>
```

Commands are 6 characters followed by space-separated arguments. Arguments may be quoted if they contain spaces.

### Argument Quoting

- Use double quotes `"` or single quotes `'` for arguments with spaces
- Use backslash `\` to escape quotes within quotes
- Use backslash `\` to escape spaces without quotes

Examples:
```
ecoadd Bitcoin
ecoadd "Magic Eden Wallet"
repadd Bitcoin https://github.com/bitcoin/bitcoin
repadd Lightning https://github.com/example/repo "#protocol" "#layer2"
ecocon Bitcoin Lightning
```

## 12. Validation Rules

### Migration File Validation
- Files must start with valid timestamp: `YYYY-MM-DDTHHMMSS`
- Timestamps must be in chronological order (enforced by sorting)
- Commands must be exactly 6 characters
- All referenced ecosystems must exist before use
- Repository URLs must be unique within the taxonomy

### Command-Specific Validation
- `ecoadd`: Ecosystem name required
- `repadd`: Ecosystem must exist, repo URL required
- `ecocon`: Both parent and child ecosystems must exist
- `ecodis`: Parent must have child relationship
- `ecorom`: Ecosystem must exist
- `repmov`: Source repo must exist
- `ecomov`: Source ecosystem must exist, destination must not exist
- `reprem`: Ecosystem and repo must exist, repo must be in ecosystem

## 13. JSON Export Format Details

### Hierarchical Export

The export flattens the hierarchy by repeating repositories at each level with appropriate `branch` values:

Example:
```
Bitcoin (top-level)
├── bitcoin/bitcoin repo
└── Lightning (sub-ecosystem)
    ├── lightningnetwork/lnd repo
    └── Lightspark (sub-sub-ecosystem)
        └── lightsparkdev/lightspark-rs repo
```

Exports as:
```json
{"eco_name":"Bitcoin","branch":[],"repo_url":"https://github.com/bitcoin/bitcoin","tags":["#protocol"]}
{"eco_name":"Bitcoin","branch":["Lightning"],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}
{"eco_name":"Bitcoin","branch":["Lightning","Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
{"eco_name":"Lightning","branch":[],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}
{"eco_name":"Lightning","branch":["Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
{"eco_name":"Lightspark","branch":[],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}
```

Note: Each ecosystem appears with all its sub-ecosystems' content when exported at top level.

## 14. Implementation Priority

1. **Phase 1**: Core data structures and taxonomy class
2. **Phase 2**: Timestamp and shlex utilities
3. **Phase 3**: Migration command handlers
4. **Phase 4**: Load process and validation
5. **Phase 5**: Export functionality
6. **Phase 6**: CLI command handler
7. **Phase 7**: Testing and validation against Zig implementation

## 15. Success Criteria

The Python implementation should:
1. Parse the same command-line arguments as the Zig version
2. Load and validate migration files identically
3. Produce byte-for-byte identical JSON output
4. Report the same validation errors
5. Display the same statistics format
6. Use only Python standard library (no external dependencies)
7. Pass all unit tests equivalent to Zig test suite
