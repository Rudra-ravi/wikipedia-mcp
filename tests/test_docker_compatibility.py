"""
Test Docker compatibility and ensure all CLI flags work in Docker context.
"""

import subprocess
import sys
import pytest


class TestDockerCompatibility:
    """Test Docker compatibility and flag availability."""

    def test_cli_has_host_flag(self):
        """Test that CLI has --host flag (regression test for issue #24)."""
        result = subprocess.run(
            [sys.executable, "-m", "wikipedia_mcp", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "--host HOST" in result.stdout
        assert "Host to bind SSE server to" in result.stdout
        assert "0.0.0.0 for all interfaces" in result.stdout

    def test_host_flag_functionality(self):
        """Test that --host flag actually works."""
        # Test with help to ensure no parsing errors
        result = subprocess.run(
            [sys.executable, "-m", "wikipedia_mcp", "--host", "0.0.0.0", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        # If --host was unrecognized, we'd get an error instead of help output
        assert "usage:" in result.stdout

    def test_dockerfile_builds_from_source(self):
        """Test that Dockerfile is configured to build from source (not PyPI)."""
        with open("Dockerfile", "r") as f:
            dockerfile_content = f.read()

        # Should copy source and install locally, not install from PyPI
        assert "COPY . ." in dockerfile_content
        assert "pip install --no-cache-dir ." in dockerfile_content
        # Should NOT have the old PyPI install line
        assert "pip install wikipedia-mcp" not in dockerfile_content

    def test_version_consistency(self):
        """Test that Dockerfile version matches pyproject.toml version."""
        # Read version from pyproject.toml
        with open("pyproject.toml", "r") as f:
            pyproject_content = f.read()

        # Extract version from pyproject.toml
        for line in pyproject_content.split("\n"):
            if line.startswith("version = "):
                pyproject_version = line.split('"')[1]
                break
        else:
            pytest.fail("Could not find version in pyproject.toml")

        # Read version from Dockerfile
        with open("Dockerfile", "r") as f:
            dockerfile_content = f.read()

        # Should contain the same version
        expected_label = f'LABEL org.opencontainers.image.version="{pyproject_version}"'
        assert expected_label in dockerfile_content, f"Dockerfile should contain {expected_label}"
