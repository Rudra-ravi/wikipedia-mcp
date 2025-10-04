"""
Tests for the command-line interface of Wikipedia MCP server.
"""

import subprocess
import sys

# Path to the wikipedia-mcp executable
WIKIPEDIA_MCP_CMD = [sys.executable, "-m", "wikipedia_mcp"]


def run_mcp_command(args, expect_timeout=False):
    """Helper function to run the wikipedia-mcp command and return its output."""
    try:
        process = subprocess.run(
            WIKIPEDIA_MCP_CMD + args,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,  # Increased timeout
            stdin=subprocess.PIPE,  # Explicitly pipe stdin
        )
        return process
    except subprocess.TimeoutExpired as e:
        if expect_timeout:
            return e
        else:
            raise


def _textify(value):
    """Return subprocess output as a decoded string."""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if value is None:
        return ""
    return str(value)


def test_cli_stdio_transport_starts():
    """Test that stdio transport starts without immediate errors."""
    args = ["--transport", "stdio", "--log-level", "INFO"]
    result = run_mcp_command(args, expect_timeout=True)

    # For stdio mode, we now expect the process to start, log, and exit cleanly.
    # It does not block indefinitely in the test environment with piped stdin.
    assert not isinstance(result, subprocess.TimeoutExpired), "Expected command to complete without timing out"

    stderr_output = _textify(getattr(result, "stderr", ""))
    assert result.returncode == 0, f"Expected return code 0, got {result.returncode}. " f"Stderr: {stderr_output}"

    # Check that some logging output was captured
    assert "Starting Wikipedia MCP server with stdio transport" in stderr_output, (
        "Expected startup message missing in stderr. " f"Observed: {stderr_output}"
    )
    assert "Using stdio transport - suppressing direct stdout messages" in stderr_output, (
        "Expected stdio mode message missing in stderr. " f"Observed: {stderr_output}"
    )

    # Verify stdout is empty (no prints interfering with stdio protocol)
    stdout_output = _textify(getattr(result, "stdout", ""))
    assert stdout_output.strip() == "", "stdout should be empty for stdio transport. " f"Observed: {stdout_output}"


def test_cli_sse_transport_starts():
    """Test that sse transport starts without immediate errors."""
    args = ["--transport", "sse", "--log-level", "INFO"]
    result = run_mcp_command(args, expect_timeout=True)

    # For sse mode, we expect the process to start the HTTP server and then timeout
    assert isinstance(result, subprocess.TimeoutExpired), "Expected timeout for sse mode"

    # Check that logging output was captured
    stderr_output = _textify(getattr(result, "stderr", ""))

    # Should see uvicorn startup messages for sse mode
    assert (
        "uvicorn" in stderr_output.lower() or "application startup" in stderr_output.lower()
    ), "Expected uvicorn startup messages for sse transport"


def test_cli_invalid_transport():
    """Test CLI behavior with an invalid transport option."""
    args = ["--transport", "invalid_transport_option"]
    result = run_mcp_command(args)
    assert result.returncode != 0, "Should exit with non-zero code for invalid transport"
    assert "invalid choice: 'invalid_transport_option'" in result.stderr, "Should show argparse error"


def test_cli_help_message():
    """Test that the help message can be displayed."""
    args = ["--help"]
    result = run_mcp_command(args)
    assert result.returncode == 0, "Help should exit with code 0"
    assert "usage:" in result.stdout.lower(), "Should show usage information"
    assert "--transport" in result.stdout, "Should show transport option"
    assert "--log-level" in result.stdout, "Should show log-level option"


def test_cli_log_levels():
    """Test different log levels work without errors."""
    for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
        args = ["--transport", "stdio", "--log-level", level]
        result = run_mcp_command(args, expect_timeout=True)

        # For stdio mode, we now expect the process to start, log, and exit cleanly.
        assert not isinstance(
            result, subprocess.TimeoutExpired
        ), f"Expected command to complete for log level {level} without timing out"

        stderr_output = _textify(getattr(result, "stderr", ""))
        assert result.returncode == 0, (
            f"Expected return code 0 for log level {level}, got {result.returncode}. " f"Stderr: {stderr_output}"
        )

        startup_message = "Starting Wikipedia MCP server with stdio transport"
        if level in ["DEBUG", "INFO"]:
            assert startup_message in stderr_output, (
                f"Startup message missing for log level {level}. " f"Stderr: {stderr_output}"
            )
        elif level in ["WARNING", "ERROR"]:
            assert startup_message not in stderr_output, (
                f"Startup message unexpectedly present for log level {level}. " f"Stderr: {stderr_output}"
            )
            # We can also check if *any* output is present for WARNING/ERROR,
            # or if specific higher-level messages appear, but for now, ensuring the INFO message
            # is correctly excluded is the main goal for this part of the test.
            # The primary check is that it started and timed out. The earlier timeout assertion covers this
            # behaviour. We mainly care that the INFO-level message is absent at higher log levels while the
            # logger still emits output.
            if level == "WARNING":
                # Example: Check for a line that looks like a log entry if specific messages are hard to predict
                # For now, the absence of the INFO message and the timeout is the core check.
                pass  # Add more specific checks if needed
            if level == "ERROR":
                pass  # Add more specific checks if needed
