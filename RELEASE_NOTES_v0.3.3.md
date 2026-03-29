CogStash v0.3.3

Changelog (selected fixes only):

- fix: Browse edit/save now persists edits and updates the in-memory view without full file reparse
- fix: Delete/mark-done update the in-memory notes list instead of forcing a full reparse
- fix: Copy action shows a brief non-blocking "Copied" notice
- fix: Stale/external-file edits now auto-reload and show a brief notice instead of failing silently
- feat: Settings now emit config-change callbacks; theme changes apply immediately to open windows
- refactor: Centralized config path usage (removed hardcoded duplicates)

Notes:
- This release includes only the fixes listed above (browse/settings live-refresh and UX improvements).
- All tests, lint, and type checks passed locally prior to tagging (170 passed, ruff/mypy clean).

How to get the release:
- Tag: v0.3.3
- After pushing the tag, create a GitHub release with this body and attach artifacts as needed.
