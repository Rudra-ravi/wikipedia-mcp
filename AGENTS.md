# Project Prevention Notes

## CI Parity
- If releasing from floating dependency ranges, then run tests in a fresh env with latest resolved deps before tagging.
- If FastMCP internals are used in tests, then use helpers that support both 2.x (`get_tools`) and 3.x (`list_tools`) APIs.
- If release CI runs `black --check`, then run `black` on touched files before pushing the release tag.
