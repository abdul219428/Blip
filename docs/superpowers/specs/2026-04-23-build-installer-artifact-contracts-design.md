# Build And Installer Artifact Contracts Design

## Context

Issue `#25` is the remaining architecture-boundary slice under umbrella issue `#12`.

Today, build and packaging behavior works, but artifact naming and path expectations are derived in multiple places:

- `scripts/build.py`
- `scripts/build_installer.py`
- `.github/workflows/release.yml`

Those components agree today by convention rather than by a single explicit contract. Versioned UI names, CLI names, onedir bundle paths, installer inputs, archive names, and release upload patterns are all related, but they are not owned in one place.

## Goals

- define one shared source of truth for artifact names and expected paths
- reduce duplicated naming and path logic across build, installer, and release flows
- make packaging behavior easier to evolve safely
- keep orchestration thin and contract logic explicit

## Non-Goals

- redesign the release pipeline
- change which artifact types are produced
- change user-facing product names unless required by the existing contract
- move packaging logic into a large configuration system

## Recommended Approach

Introduce one shared artifact-contract module that owns packaging identities and expected output paths.

Recommended location:

- `scripts/_artifacts.py`

This keeps the contract close to the packaging scripts and avoids pretending that build metadata is part of the runtime application layer.

The contract module should define:

- canonical executable names by target and bundle mode
- canonical onedir directory names
- canonical installer-facing staged names
- canonical release archive names by platform
- helper functions for locating expected outputs under `dist/`

The contract module should not run build tools itself. It should only answer questions like:

- what should this artifact be called
- where should it exist after build
- what archive name should the workflow publish
- what staged names should the installer consume

## Ownership Boundaries

### `scripts/_artifacts.py`

Owns:

- artifact naming rules
- artifact path conventions
- installer staging names
- release archive naming rules
- small helper APIs for locating expected outputs

Does not own:

- PyInstaller invocation
- file copying or staging execution
- Inno Setup execution
- GitHub Actions orchestration

### `scripts/build.py`

Owns:

- PyInstaller build plan
- platform-specific build invocation details
- icon conversion and build execution

Consumes:

- artifact names and output paths from the contract module

### `scripts/build_installer.py`

Owns:

- finding installer inputs using the shared contract
- staging the installer payload
- invoking Inno Setup

Consumes:

- versioned bundle and binary identities from the contract module
- stable staged-name rules from the contract module

### `.github/workflows/release.yml`

Owns:

- validation, build, archive, upload, and release orchestration

Consumes:

- small Python helpers or script entrypoints that apply the shared artifact contract

The workflow should stop re-deriving naming conventions inline where practical.

## Contract Shape

The shared module should expose a small set of explicit helpers rather than loose constants only.

Examples of the contract surface:

- executable name for UI onefile, UI onedir executable, and CLI onefile
- onedir directory name for a version
- installer staged executable names
- platform archive name for release packaging
- helper to locate built artifacts in `dist/`

The contract should be readable enough that a maintainer can understand the packaging outputs without reading multiple scripts and workflow steps together.

## Workflow Integration

The release workflow currently duplicates artifact rename and archive logic inline.

That should be tightened by moving naming-sensitive steps behind shared Python calls. The workflow can still orchestrate platform differences, but it should not be the place where canonical artifact identity is defined.

Preferred direction:

- keep YAML responsible for sequencing
- call Python helpers/scripts for naming-sensitive operations

This reduces brittle glob patterns and makes future changes easier to validate in tests.

## Testing Strategy

Add focused tests for the artifact contract itself.

Required coverage:

- expected names for UI onefile, UI onedir, and CLI artifacts
- expected staged installer names
- expected release archive names for each supported platform
- expected `dist/` lookup behavior

Update build and installer tests so they assert consumption of the shared contract rather than duplicated local naming logic.

The workflow should be tested indirectly through script/helper behavior where possible, not by over-investing in YAML-specific tests.

## Migration Plan

Implement this in one focused slice:

1. add the shared artifact-contract module
2. refactor `scripts/build.py` to consume it
3. refactor `scripts/build_installer.py` to consume it
4. reduce duplicated rename/archive naming logic in `release.yml`
5. add or update focused tests

## Risks And Mitigations

Risk: renaming logic changes accidentally and breaks release artifact compatibility.
Mitigation: preserve current public artifact names and add direct tests for the contract.

Risk: the shared module grows into an over-abstracted packaging framework.
Mitigation: keep the module small and limited to naming/path contracts only.

Risk: workflow changes become harder to read.
Mitigation: move only naming-sensitive logic out of YAML and keep orchestration in the workflow.

## Acceptance Criteria

- artifact naming and path conventions are defined in one shared module
- `build.py` and `build_installer.py` no longer duplicate core artifact naming rules
- release workflow logic relies less on inline artifact naming conventions
- tests directly cover the shared artifact contract
- current external artifact names remain stable unless explicitly changed
