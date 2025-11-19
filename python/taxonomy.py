"""Core taxonomy data structures and operations."""

import os
import json
import sys
from dataclasses import dataclass
from typing import Optional

from . import shlex_parser
from . import timestamp


# Custom exceptions
class TaxonomyException(Exception):
    """Base exception for taxonomy errors."""

    pass


class ValidationFailed(TaxonomyException):
    """Raised when validation fails."""

    pass


class InvalidEcosystem(TaxonomyException):
    """Raised when ecosystem doesn't exist."""

    pass


class InvalidParentEcosystem(TaxonomyException):
    """Raised when parent ecosystem doesn't exist."""

    pass


class InvalidChildEcosystem(TaxonomyException):
    """Raised when child ecosystem doesn't exist."""

    pass


class InvalidSourceRepo(TaxonomyException):
    """Raised when source repo doesn't exist."""

    pass


class InvalidSourceEcosystem(TaxonomyException):
    """Raised when source ecosystem doesn't exist."""

    pass


class DestinationEcosystemAlreadyExists(TaxonomyException):
    """Raised when destination ecosystem already exists."""

    pass


class InvalidRepo(TaxonomyException):
    """Raised when repo doesn't exist."""

    pass


class EcosystemHasNoRepos(TaxonomyException):
    """Raised when ecosystem has no repos."""

    pass


class ParentEcosystemHasNoChildren(TaxonomyException):
    """Raised when parent has no children."""

    pass


class EcoAddRequiresOneParameter(TaxonomyException):
    """Raised when ecoadd doesn't have exactly one parameter."""

    pass


class EcoConRequiresExactlyTwoParameters(TaxonomyException):
    """Raised when ecocon doesn't have exactly two parameters."""

    pass


class EcoDisRequiresExactlyTwoParameters(TaxonomyException):
    """Raised when ecodis doesn't have exactly two parameters."""

    pass


class EcoRemRequiresExactlyTwoParameters(TaxonomyException):
    """Raised when ecorem doesn't have exactly one parameter."""

    pass


class RepAddRequiresAtLeastTwoParameters(TaxonomyException):
    """Raised when repadd doesn't have at least two parameters."""

    pass


class RepMovRequiresExactlyTwoParameters(TaxonomyException):
    """Raised when repmov doesn't have exactly two parameters."""

    pass


class EcoMovRequiresExactlyTwoParameters(TaxonomyException):
    """Raised when ecomov doesn't have exactly two parameters."""

    pass


class RepRemRequiresExactlyTwoParameters(TaxonomyException):
    """Raised when reprem doesn't have exactly two parameters."""

    pass


class UnterminatedQuote(TaxonomyException):
    """Raised when a quote is not terminated."""

    pass


@dataclass
class TaxonomyError:
    """Represents an error during taxonomy processing."""

    message: str
    line_num: int
    path: str


@dataclass
class TaxonomyStats:
    """Statistics about the taxonomy."""

    migration_count: int
    eco_count: int
    repo_count: int
    tag_count: int
    eco_connections_count: int = 0


class Taxonomy:
    """Main taxonomy class that manages ecosystems, repos, and their relationships."""

    def __init__(self):
        """Initialize an empty taxonomy."""
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
        self.errors: list[TaxonomyError] = []

    def stats(self) -> TaxonomyStats:
        """
        Return statistics about the taxonomy.

        Returns:
            TaxonomyStats with counts of migrations, ecosystems, repos, and tags
        """
        return TaxonomyStats(
            migration_count=self.migration_count,
            eco_count=len(self.eco_ids),
            repo_count=len(self.repo_ids),
            tag_count=len(self.tag_ids),
            eco_connections_count=0,
        )

    def _add_eco(self, name: str) -> None:
        """Add a new ecosystem."""
        if name not in self.eco_ids:
            self.eco_auto_id += 1
            self.eco_ids[name] = self.eco_auto_id
            self.eco_id_to_name[self.eco_auto_id] = name

    def _connect_eco(self, parent: str, child: str) -> None:
        """Connect a child ecosystem to a parent."""
        if parent not in self.eco_ids:
            raise InvalidParentEcosystem(f"Parent ecosystem '{parent}' does not exist")
        if child not in self.eco_ids:
            raise InvalidChildEcosystem(f"Child ecosystem '{child}' does not exist")

        parent_id = self.eco_ids[parent]
        child_id = self.eco_ids[child]

        # Add to parent -> children mapping
        if parent_id not in self.parent_to_children:
            self.parent_to_children[parent_id] = set()
        self.parent_to_children[parent_id].add(child_id)

        # Add to child -> parents mapping
        if child_id not in self.child_to_parents:
            self.child_to_parents[child_id] = set()
        self.child_to_parents[child_id].add(parent_id)

    def _disconnect_eco(self, parent: str, child: str) -> None:
        """Disconnect a child ecosystem from a parent."""
        if parent not in self.eco_ids:
            raise InvalidParentEcosystem(f"Parent ecosystem '{parent}' does not exist")
        if child not in self.eco_ids:
            raise InvalidChildEcosystem(f"Child ecosystem '{child}' does not exist")

        parent_id = self.eco_ids[parent]
        child_id = self.eco_ids[child]

        # Remove from parent -> children mapping
        if parent_id not in self.parent_to_children:
            raise ParentEcosystemHasNoChildren(f"Parent '{parent}' has no children")
        self.parent_to_children[parent_id].discard(child_id)

        # Remove from child -> parents mapping
        if child_id in self.child_to_parents:
            self.child_to_parents[child_id].discard(parent_id)

    def _remove_eco_by_id(self, eco_id: int) -> None:
        """Remove ecosystem relationships by ID."""
        # Remove from parent relationships
        if eco_id in self.child_to_parents:
            parent_set = self.child_to_parents[eco_id]
            for parent_id in parent_set:
                if parent_id in self.parent_to_children:
                    self.parent_to_children[parent_id].discard(eco_id)
            del self.child_to_parents[eco_id]

        # Remove from child relationships
        if eco_id in self.parent_to_children:
            del self.parent_to_children[eco_id]

    def _remove_eco(self, eco_name: str) -> None:
        """Remove an ecosystem."""
        if eco_name not in self.eco_ids:
            raise InvalidEcosystem(f"Ecosystem '{eco_name}' does not exist")

        eco_id = self.eco_ids[eco_name]
        self._remove_eco_by_id(eco_id)
        del self.eco_ids[eco_name]

    def _add_repo(
        self, eco_name: str, repo_url: str, tags: Optional[list[str]] = None
    ) -> None:
        """Add a repository to an ecosystem with optional tags."""
        if eco_name not in self.eco_ids:
            raise InvalidEcosystem(f"Ecosystem '{eco_name}' does not exist")

        eco_id = self.eco_ids[eco_name]

        # Add or get repo ID
        if repo_url not in self.repo_ids:
            self.repo_auto_id += 1
            self.repo_ids[repo_url] = self.repo_auto_id
            self.repo_id_to_url[self.repo_auto_id] = repo_url

        repo_id = self.repo_ids[repo_url]

        # Add repo to ecosystem
        if eco_id not in self.eco_to_repos:
            self.eco_to_repos[eco_id] = set()
        self.eco_to_repos[eco_id].add(repo_id)

        # Add tags if provided
        if tags:
            for tag in tags:
                if tag not in self.tag_ids:
                    self.tag_auto_id += 1
                    self.tag_ids[tag] = self.tag_auto_id
                    self.tag_id_to_name[self.tag_auto_id] = tag

                tag_id = self.tag_ids[tag]
                key = (eco_id, repo_id)

                if key not in self.eco_repo_to_tags:
                    self.eco_repo_to_tags[key] = set()
                self.eco_repo_to_tags[key].add(tag_id)

    def _move_repo(self, src: str, dst: str) -> None:
        """Move/rename a repository URL."""
        if src not in self.repo_ids:
            raise InvalidSourceRepo(f"Source repo '{src}' does not exist")

        src_id = self.repo_ids[src]

        if dst in self.repo_ids:
            # Destination exists, merge them
            dst_id = self.repo_ids[dst]

            # Update all ecosystems that have src to use dst
            for eco_id, repo_set in self.eco_to_repos.items():
                if src_id in repo_set:
                    repo_set.discard(src_id)
                    repo_set.add(dst_id)

            # Remove src from mappings
            del self.repo_ids[src]
            del self.repo_id_to_url[src_id]
        else:
            # Simple rename
            del self.repo_ids[src]
            self.repo_id_to_url[src_id] = dst
            self.repo_ids[dst] = src_id

    def _move_eco(self, src: str, dst: str) -> None:
        """Move/rename an ecosystem."""
        if src not in self.eco_ids:
            raise InvalidSourceEcosystem(f"Source ecosystem '{src}' does not exist")
        if dst in self.eco_ids:
            raise DestinationEcosystemAlreadyExists(
                f"Destination ecosystem '{dst}' already exists"
            )

        src_id = self.eco_ids[src]

        # Update mappings
        del self.eco_ids[src]
        self.eco_id_to_name[src_id] = dst
        self.eco_ids[dst] = src_id

    def _remove_repo_from_ecosystem(self, eco_name: str, repo_url: str) -> None:
        """Remove a repository from an ecosystem."""
        if eco_name not in self.eco_ids:
            raise InvalidEcosystem(f"Ecosystem '{eco_name}' does not exist")

        eco_id = self.eco_ids[eco_name]

        if eco_id not in self.eco_to_repos:
            raise EcosystemHasNoRepos(f"Ecosystem '{eco_name}' has no repos")

        if repo_url not in self.repo_ids:
            raise InvalidRepo(f"Repo '{repo_url}' does not exist")

        repo_id = self.repo_ids[repo_url]
        self.eco_to_repos[eco_id].discard(repo_id)

        # Remove tags for this eco-repo combination
        key = (eco_id, repo_id)
        if key in self.eco_repo_to_tags:
            del self.eco_repo_to_tags[key]

    # Command handlers
    def _cmd_ecoadd(self, tokens: list[str]) -> None:
        """Handle ecoadd command."""
        if len(tokens) != 1:
            raise EcoAddRequiresOneParameter("ecoadd requires exactly one parameter")
        self._add_eco(tokens[0])

    def _cmd_repadd(self, tokens: list[str]) -> None:
        """Handle repadd command."""
        if len(tokens) < 2:
            raise RepAddRequiresAtLeastTwoParameters(
                "repadd requires at least two parameters"
            )

        eco_name = tokens[0]
        repo_url = tokens[1]
        tags = tokens[2:] if len(tokens) > 2 else None
        self._add_repo(eco_name, repo_url, tags)

    def _cmd_ecocon(self, tokens: list[str]) -> None:
        """Handle ecocon command."""
        if len(tokens) != 2:
            raise EcoConRequiresExactlyTwoParameters(
                "ecocon requires exactly two parameters"
            )
        self._connect_eco(tokens[0], tokens[1])

    def _cmd_ecodis(self, tokens: list[str]) -> None:
        """Handle ecodis command."""
        if len(tokens) != 2:
            raise EcoDisRequiresExactlyTwoParameters(
                "ecodis requires exactly two parameters"
            )
        self._disconnect_eco(tokens[0], tokens[1])

    def _cmd_ecorem(self, tokens: list[str]) -> None:
        """Handle ecorem command."""
        if len(tokens) != 1:
            raise EcoRemRequiresExactlyTwoParameters(
                "ecorem requires exactly one parameter"
            )
        self._remove_eco(tokens[0])

    def _cmd_repmov(self, tokens: list[str]) -> None:
        """Handle repmov command."""
        if len(tokens) != 2:
            raise RepMovRequiresExactlyTwoParameters(
                "repmov requires exactly two parameters"
            )
        self._move_repo(tokens[0], tokens[1])

    def _cmd_ecomov(self, tokens: list[str]) -> None:
        """Handle ecomov command."""
        if len(tokens) != 2:
            raise EcoMovRequiresExactlyTwoParameters(
                "ecomov requires exactly two parameters"
            )
        self._move_eco(tokens[0], tokens[1])

    def _cmd_reprem(self, tokens: list[str]) -> None:
        """Handle reprem command."""
        if len(tokens) != 2:
            raise RepRemRequiresExactlyTwoParameters(
                "reprem requires exactly two parameters"
            )
        self._remove_repo_from_ecosystem(tokens[0], tokens[1])

    def _is_comment(self, line: str) -> bool:
        """Check if a line is a comment."""
        stripped = line.lstrip()
        return len(stripped) == 0 or stripped[0] == "#"

    def _load_file(self, path: str) -> None:
        """Load and process a single migration file."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.split("\n")
        for line_num, line in enumerate(lines, start=1):
            # Skip comments and blank lines
            if self._is_comment(line):
                continue

            # Skip lines too short to have a command
            if len(line) < 6:
                continue

            # Parse command
            keyword = line[0:6]
            remainder = line[6:]

            try:
                # Parse tokens from remainder
                tokens = shlex_parser.split(remainder)

                # Execute command
                if keyword == "ecoadd":
                    self._cmd_ecoadd(tokens)
                elif keyword == "repadd":
                    self._cmd_repadd(tokens)
                elif keyword == "ecocon":
                    self._cmd_ecocon(tokens)
                elif keyword == "ecodis":
                    self._cmd_ecodis(tokens)
                elif keyword == "ecorem":
                    self._cmd_ecorem(tokens)
                elif keyword == "repmov":
                    self._cmd_repmov(tokens)
                elif keyword == "ecomov":
                    self._cmd_ecomov(tokens)
                elif keyword == "reprem":
                    self._cmd_reprem(tokens)
                # Ignore unknown commands (might be comments or empty lines)

            except (TaxonomyException, ValueError) as e:
                error_name = type(e).__name__
                self.errors.append(
                    TaxonomyError(message=error_name, line_num=line_num, path=path)
                )

    def load(self, root_dir: str, max_date: Optional[str] = None) -> None:
        """
        Load and process migration files from root_dir.

        Args:
            root_dir: Directory containing migration files
            max_date: Optional maximum date to filter migrations (YYYY-MM-DD format)

        Raises:
            ValidationFailed: If errors were encountered during loading
        """
        # List all files in directory
        try:
            files = os.listdir(root_dir)
        except OSError as e:
            raise TaxonomyException(f"Cannot read directory '{root_dir}': {e}")

        # Filter files with valid timestamps
        migration_files = []
        for filename in files:
            file_path = os.path.join(root_dir, filename)
            if os.path.isfile(file_path) and timestamp.has_valid_timestamp(filename):
                # Apply date filter if provided
                if max_date is None or filename < max_date:
                    migration_files.append(filename)

        # Sort files by timestamp (first 19 characters)
        migration_files.sort(key=lambda x: x[0:19])

        # Process each file
        for filename in migration_files:
            file_path = os.path.join(root_dir, filename)
            self._load_file(file_path)
            self.migration_count += 1

        # Check for errors
        if self.errors:
            self._print_errors()
            raise ValidationFailed("Validation failed with errors")

    def _print_errors(self) -> None:
        """Print all errors to stderr."""
        for error in self.errors:
            print(
                f"{error.path}:{error.line_num}: error.{error.message}", file=sys.stderr
            )

    def _tag_strings_for_eco_repo(
        self, eco_id: int, repo_id: int
    ) -> Optional[list[str]]:
        """Get tag strings for a specific ecosystem-repo combination."""
        key = (eco_id, repo_id)
        if key in self.eco_repo_to_tags:
            tag_ids = self.eco_repo_to_tags[key]
            return [self.tag_id_to_name[tag_id] for tag_id in tag_ids]
        return None

    def _emit_ecosystem_json(self, f, top: str, branch: list[str], eco_id: int) -> None:
        """Recursively emit JSON for an ecosystem and its sub-ecosystems."""
        # Get repos for this ecosystem and sort them
        if eco_id in self.eco_to_repos:
            repo_ids = self.eco_to_repos[eco_id]
            # Create tuples of (repo_id, repo_url) and sort by URL (case-insensitive)
            repo_tuples = [
                (repo_id, self.repo_id_to_url[repo_id]) for repo_id in repo_ids
            ]
            repo_tuples.sort(key=lambda x: x[1].casefold())

            # Emit each repo
            for repo_id, repo_url in repo_tuples:
                tags = self._tag_strings_for_eco_repo(eco_id, repo_id)
                row = {
                    "eco_name": top,
                    "branch": branch.copy(),
                    "repo_url": repo_url,
                    "tags": tags if tags else [],
                }
                f.write(json.dumps(row, separators=(",", ":")) + "\n")

        # Get sub-ecosystems and sort them
        if eco_id in self.parent_to_children:
            child_ids = self.parent_to_children[eco_id]
            # Create tuples of (child_id, child_name) and sort by name (case-insensitive)
            child_tuples = [
                (child_id, self.eco_id_to_name[child_id]) for child_id in child_ids
            ]
            child_tuples.sort(key=lambda x: x[1].casefold())

            # Recursively emit each sub-ecosystem
            for child_id, child_name in child_tuples:
                branch.append(child_name)
                self._emit_ecosystem_json(f, top, branch, child_id)
                branch.pop()

    def export_json(self, output_file: str, ecosystem: Optional[str] = None) -> None:
        """
        Export taxonomy to JSON Lines format.

        Args:
            output_file: Path to output file
            ecosystem: Optional specific ecosystem to export (exports all if None)
        """
        # Collect ecosystems to export
        if ecosystem:
            if ecosystem not in self.eco_ids:
                raise InvalidEcosystem(f"Ecosystem '{ecosystem}' does not exist")
            keys_list = [(ecosystem, self.eco_ids[ecosystem])]
        else:
            # Get all ecosystems and sort by name (case-insensitive)
            keys_list = [(name, eco_id) for name, eco_id in self.eco_ids.items()]
            keys_list.sort(key=lambda x: x[0].casefold())

        # Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            for eco_name, eco_id in keys_list:
                branch = []
                self._emit_ecosystem_json(f, eco_name, branch, eco_id)
