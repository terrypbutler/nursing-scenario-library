# Nursing Scenario Library

This repository stores the fictional training scenarios used by Nurse
Simulation Studio. Scenario content is separate from the application so a new
patient can be written, reviewed and published without changing the app code.

All current scenarios are **development fixtures awaiting local clinical and
educational review**. Never add real patient information.

## Add a scenario

1. Copy `templates/scenario-template.yaml` into `scenarios/`.
2. Give it the next unused ID, for example `PAT-005.yaml`, and use the same ID
   in `case_id`.
3. Fill in the fictional patient, clinical state, actions, dialogue boundaries
   and debrief prompts.
4. Keep `publication_status: development` while it is being reviewed.
5. Run the validation and build commands below.
6. Commit and push the change with GitHub Desktop.

Every action must have matching entries under `dialogue.action_responses` and
`dialogue.action_phrases`. Portable scenarios also carry the Studio prebrief,
clinical workspace, non-verbal palette and educator rubric, so advanced
simulation features do not live inside the application code.
Dialogue facts may have `when` conditions, but the AI cannot apply effects or
change clinical state. State changes remain deterministic and must be authored
under `allowed_actions` or `time_events`.

## Validate and build locally

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python tools\build_library.py
```

Nurse Simulation Studio consumes `dist/library.json`. A build stops if a scenario is malformed,
contains direct-identity fields, has incomplete dialogue responses, permits
unsafe AI content or enables automatic competence decisions.

## Review status

- `development`: available for prototype testing but not clinically approved.
- `approved`: reviewed through the organisation's clinical, simulation,
  medicines, accessibility and information-governance processes.

Use `python tools\build_library.py --approved-only` when the deployed app should
receive only approved scenarios.

## Connect Nurse Simulation Studio

After this repository is published, set the following in the Streamlit app's
Secrets page:

```toml
SCENARIO_LIBRARY_URL = "https://YOUR-GITHUB-NAME.github.io/nursing-scenario-library/library.json"
```

The app validates the downloaded library and uses its bundled fictional cases
if the published library cannot be loaded safely.
