"""Unit tests for taxonomy core functionality."""

import unittest
import tempfile
import os
import json
from src.taxonomy import Taxonomy, InvalidEcosystem


class TestTaxonomy(unittest.TestCase):
    """Test taxonomy core functionality."""

    def get_tests_path(self, test_dir: str) -> str:
        """Get the path to a test directory."""
        # Get the path relative to this file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(current_dir)
        return os.path.join(tests_dir, test_dir)

    def test_load_single_ecosystem(self):
        """Test loading a single ecosystem."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("simple_ecosystems")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(1, stats.migration_count)
        self.assertEqual(1, stats.eco_count)
        self.assertEqual(3, stats.repo_count)
        self.assertEqual(1, stats.tag_count)

        # Verify Bitcoin ecosystem exists and has repos
        self.assertIn("Bitcoin", tax.eco_ids)
        btc_id = tax.eco_ids["Bitcoin"]
        self.assertIn(btc_id, tax.eco_to_repos)
        self.assertEqual(3, len(tax.eco_to_repos[btc_id]))

    def test_time_ordering(self):
        """Test that migrations are processed in time order."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("time_ordering")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(3, stats.migration_count)
        self.assertEqual(1, stats.eco_count)
        self.assertEqual(2, stats.repo_count)

        # Check that Ethereum has the right repos
        self.assertIn("Ethereum", tax.eco_ids)
        eth_id = tax.eco_ids["Ethereum"]
        repo_ids = tax.eco_to_repos[eth_id]
        repo_urls = [tax.repo_id_to_url[rid] for rid in repo_ids]
        repo_urls.sort()

        self.assertEqual(2, len(repo_urls))
        self.assertIn("https://github.com/ethereum/aleth", repo_urls)
        self.assertIn("https://github.com/openethereum/parity-ethereum", repo_urls)

    def test_ecosystem_disconnect(self):
        """Test ecosystem parent-child disconnection."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("ecosystem_disconnect")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(2, stats.migration_count)
        self.assertEqual(5, stats.eco_count)
        self.assertEqual(1, stats.repo_count)

        # Check Polygon's sub-ecosystems
        poly_id = tax.eco_ids["Polygon"]
        if poly_id in tax.parent_to_children:
            children = tax.parent_to_children[poly_id]
            child_names = [tax.eco_id_to_name[cid] for cid in children]
            self.assertEqual(1, len(child_names))
            self.assertIn("DeGods", child_names)

        # Check Solana has no sub-ecosystems
        solana_id = tax.eco_ids["Solana"]
        if solana_id in tax.parent_to_children:
            self.assertEqual(0, len(tax.parent_to_children[solana_id]))

    def test_ecosystem_rename(self):
        """Test ecosystem renaming."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("ecosystem_rename")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(1, stats.migration_count)
        self.assertEqual(2, stats.eco_count)
        self.assertEqual(2, stats.repo_count)

        # MultiversX should exist
        self.assertIn("MultiversX", tax.eco_ids)
        multi_id = tax.eco_ids["MultiversX"]

        # Check sub-ecosystems
        if multi_id in tax.parent_to_children:
            children = tax.parent_to_children[multi_id]
            self.assertEqual(1, len(children))

        # Elrond should not exist
        self.assertNotIn("Elrond", tax.eco_ids)

    def test_repo_removals(self):
        """Test repository removal from ecosystems."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("repo_removals")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(2, stats.migration_count)
        self.assertEqual(2, stats.eco_count)
        self.assertEqual(6, stats.repo_count)

        # Check Ethereum has only 1 repo
        eth_id = tax.eco_ids["Ethereum"]
        repos = tax.eco_to_repos[eth_id]
        self.assertEqual(1, len(repos))

    def test_repo_rename_with_existing_destination(self):
        """Test repository rename when destination exists."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("repo_renames_with_existing_destination")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(1, stats.migration_count)
        self.assertEqual(2, stats.eco_count)
        self.assertEqual(2, stats.repo_count)

        # Check Monero ecosystem
        monero_id = tax.eco_ids["Monero"]
        monero_repos = tax.eco_to_repos[monero_id]
        self.assertEqual(2, len(monero_repos))

        # Check Aeon ecosystem
        aeon_id = tax.eco_ids["Aeon"]
        aeon_repos = tax.eco_to_repos[aeon_id]
        self.assertEqual(1, len(aeon_repos))

        # Verify bitmonero is removed
        self.assertNotIn("https://github.com/monero-project/bitmonero", tax.repo_ids)

    def test_ecosystem_removal(self):
        """Test ecosystem removal."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("ecosystem_removal")
        tax.load(tests_path, None)

        stats = tax.stats()
        self.assertEqual(1, stats.migration_count)
        self.assertEqual(5, stats.eco_count)
        self.assertEqual(2, stats.repo_count)

        # Magic Eden should not exist
        self.assertNotIn("Magic Eden", tax.eco_ids)

        # Bitcoin should have no sub-ecosystems
        btc_id = tax.eco_ids["Bitcoin"]
        if btc_id in tax.parent_to_children:
            self.assertEqual(0, len(tax.parent_to_children[btc_id]))

        # Magic Eden Wallet should still exist
        self.assertIn("Magic Eden Wallet", tax.eco_ids)

    def test_date_filtering(self):
        """Test date filtering during load."""
        tests_path = self.get_tests_path("date_filtering")

        # Load with 2011 filter
        tax1 = Taxonomy()
        tax1.load(tests_path, "2011")
        stats1 = tax1.stats()
        self.assertEqual(1, stats1.migration_count)
        self.assertEqual(1, stats1.eco_count)

        # Load with 2013 filter
        tax2 = Taxonomy()
        tax2.load(tests_path, "2013")
        stats2 = tax2.stats()
        self.assertEqual(2, stats2.migration_count)
        self.assertEqual(2, stats2.eco_count)

        # Load with 2015-08-01 filter
        tax3 = Taxonomy()
        tax3.load(tests_path, "2015-08-01")
        stats3 = tax3.stats()
        self.assertEqual(3, stats3.migration_count)
        self.assertEqual(3, stats3.eco_count)

    def test_json_export(self):
        """Test JSON export functionality."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("tiered")
        tax.load(tests_path, None)

        # Bitcoin should have sub-ecosystems
        btc_id = tax.eco_ids["Bitcoin"]
        self.assertIn(btc_id, tax.parent_to_children)
        self.assertEqual(1, len(tax.parent_to_children[btc_id]))

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            tax.export_json(temp_file, None)

            # Read and verify content
            with open(temp_file, "r") as f:
                content = f.read()

            expected = (
                '{"eco_name":"Bitcoin","branch":[],"repo_url":"https://github.com/bitcoin/bitcoin","tags":["#protocol"]}\n'
                '{"eco_name":"Bitcoin","branch":["Lightning"],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}\n'
                '{"eco_name":"Bitcoin","branch":["Lightning","Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}\n'
                '{"eco_name":"Lightning","branch":[],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}\n'
                '{"eco_name":"Lightning","branch":["Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}\n'
                '{"eco_name":"Lightspark","branch":[],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}\n'
            )

            self.assertEqual(expected, content)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_json_export_single_ecosystem(self):
        """Test exporting a single ecosystem."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("tiered")
        tax.load(tests_path, None)

        # Export only Lightning ecosystem
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            tax.export_json(temp_file, "Lightning")

            # Read and verify content
            with open(temp_file, "r") as f:
                content = f.read()

            expected = (
                '{"eco_name":"Lightning","branch":[],"repo_url":"https://github.com/lightningnetwork/lnd","tags":["#protocol"]}\n'
                '{"eco_name":"Lightning","branch":["Lightspark"],"repo_url":"https://github.com/lightsparkdev/lightspark-rs","tags":["#sdk"]}\n'
            )

            self.assertEqual(expected, content)
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_export_invalid_ecosystem(self):
        """Test that exporting an invalid ecosystem raises an error."""
        tax = Taxonomy()
        tests_path = self.get_tests_path("simple_ecosystems")
        tax.load(tests_path, None)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            with self.assertRaises(InvalidEcosystem):
                tax.export_json(temp_file, "NonExistent")
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_tags_are_sorted_alphabetically(self):
        """Test that tags are sorted alphabetically (case-insensitive) in exports."""
        tax = Taxonomy()
        tax._add_eco("TestEco")
        # Add tags in non-alphabetical order with # prefix
        tax._add_repo(
            "TestEco",
            "https://github.com/test/repo",
            ["#zephyr", "#Apple", "#banana", "#MIDDLEWARE"],
        )

        # Export to temp file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            temp_file = f.name

        try:
            tax.export_json(temp_file, None)

            # Read and parse the JSON
            with open(temp_file, "r") as f:
                line = f.readline()
                data = json.loads(line)

            # Verify tags are sorted alphabetically (case-insensitive)
            expected_tags = ["#Apple", "#banana", "#MIDDLEWARE", "#zephyr"]
            self.assertEqual(expected_tags, data["tags"])

            # Verify the order is case-insensitive (Apple before banana before MIDDLEWARE before zephyr)
            self.assertEqual("#Apple", data["tags"][0])
            self.assertEqual("#banana", data["tags"][1])
            self.assertEqual("#MIDDLEWARE", data["tags"][2])
            self.assertEqual("#zephyr", data["tags"][3])
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


if __name__ == "__main__":
    unittest.main()
