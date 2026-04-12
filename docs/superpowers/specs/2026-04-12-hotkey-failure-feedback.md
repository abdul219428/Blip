# Hotkey Registration Failure Feedback Spec

## Parent issue
- Child issue: `#15` — Show clear in-app feedback when hotkey registration fails
- Umbrella: `#11` — Post-v0.4.1 UX and workflow follow-up

## Problem

When `pynput.keyboard.GlobalHotKeys` fails to register the configured hotkey, CogStash currently logs the error and prints a console message, but the GUI provides no durable, user-facing indication that the main capture workflow is broken.

This creates a bad UX: the app appears to start normally, but pressing the hotkey does nothing.

## Goal

Make hotkey registration failure visible and understandable in the GUI for the current session, using:

1. a startup modal dialog with next steps
2. a persistent warning in Settings so the failure remains discoverable after startup

## Non-goals

- changing how users edit the hotkey in-app (tracked separately in `#14`)
- adding retry/rebind UI for the hotkey in this slice
- persisting hotkey failure state across app restarts
- redesigning broader startup/onboarding flows

## User experience

### Startup behavior

If hotkey registration fails during `main()`:

- CogStash still starts
- tray/UI behavior still initializes as today
- a modal warning is shown once during startup

The modal must clearly say:

- the configured hotkey could not be registered
- capture by hotkey is unavailable for this session
- likely next steps:
  - another app may already be using the shortcut
  - platform permissions/accessibility hooks may be blocking registration
  - the user can review the log file for technical detail
  - the user can change the hotkey in config for now, then restart CogStash

### Persistent warning behavior

When the user opens Settings during the same failed session, the General tab must show a visible warning block near the hotkey section.

That warning must:

- mention that the current hotkey failed to register
- state that global capture is unavailable until the problem is fixed and the app restarts
- point the user to the log file
- remain accurate with current product behavior (do **not** claim hotkey can already be changed inside Settings)

### Session lifetime

- the warning is runtime/session state only
- if the next app launch registers the hotkey successfully, no warning is shown

## Technical design constraints

- keep the implementation narrow to `ui.app` and `ui.settings`
- do not add config persistence for this runtime-only failure state
- prefer a small runtime flag/message passed from `CogStash` app state into Settings rather than a new cross-cutting persistence mechanism
- keep console/log output in place; GUI feedback is additive, not a replacement

## Acceptance criteria

1. If hotkey registration raises during startup, `main()` shows a warning dialog once.
2. The app still reaches the normal running state instead of crashing.
3. Settings General tab shows a persistent warning for the same failed session.
4. The Settings warning does not falsely imply in-app hotkey editing already exists.
5. Existing successful-startup behavior remains unchanged when hotkey registration succeeds.
6. Tests cover:
   - startup warning shown on hotkey registration failure
   - startup still completes after failure
   - Settings warning appears when failure state is present
   - no warning appears when there is no failure state

## Likely files

- `src/cogstash/ui/app.py`
- `src/cogstash/ui/settings.py`
- `tests/ui/test_app.py`
- `tests/ui/test_settings.py`
