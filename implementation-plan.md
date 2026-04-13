# Garden Planner Lite – Technical Implementation Plan

## Overview

The app is built in five phases, back-to-front. Each phase produces a runnable, testable artifact before the next begins. The backend is fully tested before the frontend touches it.

```
Phase 1 → Project scaffold & environment
Phase 2 → Plant data layer
Phase 3 → Rules engine (pure logic)
Phase 4 → API layer (FastAPI)
Phase 5 → React frontend
```

---

## Project Structure (target)

```
gardening/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── models.py            # Pydantic data models
│   ├── data.py              # Plant seed data
│   ├── rules.py             # Compatibility + schedule logic
│   ├── conftest.py          # Shared pytest fixtures (TestClient)
│   └── tests/
│       ├── test_rules.py    # Unit tests for pure logic
│       └── test_api.py      # API contract tests
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── types.ts         # Shared TypeScript interfaces
│   │   ├── api.ts           # All fetch calls live here
│   │   └── components/
│   │       ├── PlantSelector.tsx
│   │       ├── GardenList.tsx
│   │       ├── WarningsPanel.tsx
│   │       └── ScheduleDisplay.tsx
│   └── tests/
│       └── e2e/             # Playwright tests
├── pytest.ini
├── requirements.txt
└── package.json
```

---

## Conventions (read before writing any code)

These decisions are fixed for the whole project. An AI agent must not deviate from them.

### Field naming

- **Backend (Python/Pydantic):** all field names use `snake_case` — `plant_ids`, `current_month`, `planting_start_month`, `plants_involved`
- **API wire format:** FastAPI serializes Pydantic models as `snake_case` by default — do not configure `alias` or `by_alias`
- **Frontend (TypeScript):** field names match the wire format exactly — `snake_case`. Do not camelCase them in `types.ts`

### Technology choices (no alternatives)

- **Frontend scaffold:** Vite with the React + TypeScript template (`npm create vite@latest frontend -- --template react-ts`). Dev server runs on port **5173**, not 3000.
- **Pydantic version:** v2 (`pydantic>=2.0`)
- **Python version:** 3.11+

### `data-testid` attributes (required on all interactive/observable elements)

Every component must emit these exact attributes so Playwright tests can find them without relying on CSS classes or text content:

| Element | `data-testid` value |
|---|---|
| Plant dropdown | `plant-selector` |
| Add plant button | `add-plant-btn` |
| Garden list container | `garden-list` |
| Each garden list item | `garden-item-{index}` (0-based) |
| Remove button per item | `remove-plant-{index}` |
| Warnings panel | `warnings-panel` |
| Each warning message | `warning-{index}` |
| Schedule display container | `schedule-display` |
| Status badge per plant | `status-badge-{plant_id}-{index}` |

### `current_month` in the frontend

The frontend derives current month as `new Date().getMonth() + 1` (JavaScript months are 0-indexed). This value is passed directly to `POST /evaluate`. There is no date picker in the base implementation (stretch goal only).

### Unknown plant IDs

When `POST /evaluate` receives a plant ID not found in the data store, it returns **HTTP 404** with body `{"detail": "Plant not found: {id}"}`. It does not return 422.

### Duplicate plant IDs and compatibility

When the same plant ID appears more than once in `plant_ids`, the compatibility engine must **not** generate a warning between those two entries. Two instances of the same plant (same ID) are not incompatible with each other. Warnings only fire between plants with *different* IDs where an incompatibility is declared.

---

## Configuration Files

These files must be created during Phase 1 and never modified thereafter.

### `pytest.ini`

```ini
[pytest]
testpaths = backend/tests
pythonpath = backend
```

`pythonpath = backend` makes `from rules import ...` and `from data import PLANTS` work without `sys.path` manipulation in test files.

### `requirements.txt`

```
fastapi>=0.111.0
uvicorn>=0.29.0
pydantic>=2.0
httpx>=0.27.0
pytest>=8.0
pytest-asyncio>=0.23.0
starlette>=0.37.0
playwright>=1.44.0
```

> Note: `starlette` provides `TestClient`. `pytest-asyncio` is included for future async test support but not required for the synchronous `TestClient` pattern used in this project.

### `backend/conftest.py`

This file must be created in Phase 1 alongside the health endpoint. All test files depend on the `client` fixture it provides.

```python
# backend/conftest.py
import pytest
from starlette.testclient import TestClient
from main import app

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
```

### TypeScript interfaces (`frontend/src/types.ts`)

All frontend files import types from here. These must match the API wire format exactly.

```typescript
export interface Plant {
  id: string;
  name: string;
  planting_start_month: number;
  planting_end_month: number;
  incompatible_with: string[];
}

export interface PlantStatus {
  id: string;
  status: "too_early" | "plant_now" | "too_late";
}

export interface Warning {
  type: "compatibility";
  message: string;
  plants_involved: string[];
}

export interface EvaluateResponse {
  plants: PlantStatus[];
  warnings: Warning[];
}
```

---

## Phase 1 — Project Scaffold & Environment

**Goal:** A runnable FastAPI server that returns `{"status": "ok"}` and a React app that loads in the browser. No real logic yet — just confirm the toolchain works end-to-end.

### Tasks

1. Create `pytest.ini` and `requirements.txt` with the exact contents shown in the Configuration section above
2. Create a Python virtual environment and run `pip install -r requirements.txt`
3. Create `backend/conftest.py` with the `client` fixture shown above
4. Create `backend/main.py` with:
   - A `GET /health` endpoint returning `{"status": "ok"}`
   - CORS middleware configured for the Vite dev server (see CORS config below)
5. Scaffold the frontend: `npm create vite@latest frontend -- --template react-ts`
6. Run `pip install playwright && playwright install chromium` for e2e tests

### CORS configuration for `main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
```

### Phase 1 Success Tests

| Test | Type | Passes When |
|---|---|---|
| `test_health_returns_ok` | pytest | `GET /health` returns `{"status": "ok"}` with HTTP 200 |
| Manual browser check | manual | React app loads at `localhost:5173` without errors |
| Manual CORS check | manual | Browser fetch from React to `/health` succeeds (no CORS error in console) |

**Run pytest from the project root:** `pytest`

```python
# backend/tests/test_api.py
def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

---

## Phase 2 — Plant Data Layer

**Goal:** Define the `Plant` model and load seed data. `GET /plants` returns a list of real plants. No rule logic yet.

### Tasks

1. Define `Plant` and `Warning` as Pydantic models in `models.py`:
   ```python
   from pydantic import BaseModel, Field

   class Plant(BaseModel):
       id: str
       name: str
       planting_start_month: int = Field(ge=1, le=12)
       planting_end_month: int = Field(ge=1, le=12)
       incompatible_with: list[str]

   class Warning(BaseModel):
       type: str
       message: str
       plants_involved: list[str]  # list of plant IDs, not names
   ```
2. Populate `data.py` with the seed data below, exposed as a module-level constant `PLANTS: list[Plant]`
3. Implement `GET /plants` in `main.py` — returns `PLANTS` serialized to JSON

### Seed Data

Use these exact IDs — tests in later phases reference them by ID.

| `id` | `name` | Start | End | `incompatible_with` |
|---|---|---|---|---|
| `tomato` | Tomato | 4 | 8 | `["fennel"]` |
| `fennel` | Fennel | 3 | 7 | `["tomato", "pepper"]` |
| `pepper` | Pepper | 4 | 8 | `["fennel"]` |
| `basil` | Basil | 5 | 9 | `[]` |
| `carrot` | Carrot | 3 | 6 | `["dill"]` |
| `dill` | Dill | 4 | 7 | `["carrot"]` |
| `lettuce` | Lettuce | 2 | 5 | `[]` |
| `garlic` | Garlic | 9 | 11 | `[]` |

> Garlic (start=9) covers the late-year gap. Lettuce (start=2) covers the early-year gap. This ensures all 12 months can be tested for "too early", "plant now", and "too late" without needing to construct synthetic plants.

### Phase 2 Success Tests

| Test | Type | Passes When |
|---|---|---|
| `test_get_plants_returns_list` | pytest | Response is a JSON array |
| `test_get_plants_not_empty` | pytest | List contains at least 1 plant |
| `test_plant_has_required_fields` | pytest | Every plant has all 5 required fields with correct types |
| `test_all_months_valid` | pytest | No plant has `start` or `end` outside `1–12` |
| `test_no_duplicate_ids` | pytest | All plant `id` values are unique |

```python
def test_plant_has_required_fields(client):
    plants = client.get("/plants").json()
    for plant in plants:
        assert "id" in plant
        assert "name" in plant
        assert 1 <= plant["planting_start_month"] <= 12
        assert 1 <= plant["planting_end_month"] <= 12
        assert isinstance(plant["incompatible_with"], list)
```

---

## Phase 3 — Rules Engine (Pure Logic)

**Goal:** Implement all business logic as pure functions in `rules.py` with zero dependency on FastAPI. This is the most important phase — logic is fully tested before it touches the API.

### Tasks

1. Implement `get_planting_status(plant: Plant, current_month: int) -> str`:
   - Returns `"too_early"`, `"plant_now"`, or `"too_late"`
   - `current_month` is passed in explicitly (never reads system date directly)

2. Implement `get_compatibility_warnings(selected_plants: list[Plant]) -> list[Warning]`:
   - Checks every unique *pair* of plants using `itertools.combinations`
   - A warning fires if either plant lists the other's ID in its `incompatible_with` list
   - Deduplicates by pair: `{A, B}` and `{B, A}` are the same pair and produce one warning
   - Two plants with the **same ID** never produce a warning (see Conventions)
   - `Warning.plants_involved` contains the two plant **IDs** (not names)
   - `Warning.message` should read: `"{name_a} and {name_b} are not compatible"`

3. Import both `Plant` and `Warning` from `models.py`

### Phase 3 Success Tests

These are pure unit tests — no HTTP client, no `client` fixture.

**Planting status:**

| Test | Input | Expected |
|---|---|---|
| `test_status_too_early` | start=5, end=8, month=3 | `"too_early"` |
| `test_status_plant_now_start_boundary` | start=5, end=8, month=5 | `"plant_now"` |
| `test_status_plant_now_mid` | start=5, end=8, month=6 | `"plant_now"` |
| `test_status_plant_now_end_boundary` | start=5, end=8, month=8 | `"plant_now"` |
| `test_status_too_late` | start=5, end=8, month=10 | `"too_late"` |
| `test_status_single_month_window_hit` | start=6, end=6, month=6 | `"plant_now"` |
| `test_status_single_month_window_miss` | start=6, end=6, month=7 | `"too_late"` |

**Compatibility warnings:**

| Test | Input | Expected |
|---|---|---|
| `test_no_warnings_for_compatible_plants` | [tomato, basil] | `[]` |
| `test_warning_fires_for_incompatible_pair` | [tomato, fennel] | 1 warning |
| `test_warning_is_bidirectional` | [fennel, tomato] (reversed order) | same 1 warning |
| `test_no_duplicate_warnings` | [tomato, fennel, fennel] | still 1 warning (tomato↔fennel only) |
| `test_multiple_warnings` | [tomato, fennel, carrot, dill] | 2 warnings |
| `test_empty_list_no_warnings` | [] | `[]` |
| `test_single_plant_no_warnings` | [tomato] | `[]` |
| `test_circular_incompatibility` | A→B and B→A in data | 1 warning (not 2) |

> `test_no_duplicate_warnings` uses two fennel instances. The tomato↔fennel pair appears once (from tomato+fennel[0]). fennel[0]↔fennel[1] share the same ID → no self-warning. Result: 1 warning total.

```python
# backend/tests/test_rules.py
from rules import get_planting_status, get_compatibility_warnings
from data import PLANTS

def _plant(id):
    return next(p for p in PLANTS if p.id == id)

def test_status_plant_now_start_boundary():
    assert get_planting_status(_plant("tomato"), current_month=4) == "plant_now"

def test_warning_is_bidirectional():
    warnings_ab = get_compatibility_warnings([_plant("tomato"), _plant("fennel")])
    warnings_ba = get_compatibility_warnings([_plant("fennel"), _plant("tomato")])
    assert len(warnings_ab) == 1
    assert len(warnings_ba) == 1
    assert set(warnings_ab[0].plants_involved) == set(warnings_ba[0].plants_involved)

def test_duplicate_ids_no_self_warning():
    tomato = _plant("tomato")
    warnings = get_compatibility_warnings([tomato, tomato])
    assert warnings == []
```

---

## Phase 4 — API Layer

**Goal:** Wire the rules engine into the `POST /evaluate` endpoint. API contract is fully tested with `httpx` before the frontend is built.

### Tasks

1. Define request/response Pydantic models in `models.py`:
   ```python
   class EvaluateRequest(BaseModel):
       plant_ids: list[str]
       current_month: int = Field(ge=1, le=12)

   class PlantStatus(BaseModel):
       id: str
       status: str

   class EvaluateResponse(BaseModel):
       plants: list[PlantStatus]
       warnings: list[Warning]
   ```

2. Implement `POST /evaluate` in `main.py`:
   - Parse request body as `EvaluateRequest`
   - For each ID in `plant_ids`, look it up in `PLANTS` (a dict keyed by ID is efficient)
   - If any ID is not found, raise `HTTPException(status_code=404, detail=f"Plant not found: {id}")`
   - Call `get_planting_status(plant, request.current_month)` for each plant
   - Call `get_compatibility_warnings(resolved_plants)` for the full list
   - Return `EvaluateResponse`

3. Build the plant lookup dict in `data.py`:
   ```python
   PLANTS_BY_ID: dict[str, Plant] = {p.id: p for p in PLANTS}
   ```

### Phase 4 Success Tests

**Happy path:**

| Test | Input | Expected |
|---|---|---|
| `test_evaluate_single_plant_too_early` | `["tomato"]`, month=1 | status `too_early`, 0 warnings |
| `test_evaluate_single_plant_now` | `["tomato"]`, month=5 | status `plant_now`, 0 warnings |
| `test_evaluate_single_plant_too_late` | `["tomato"]`, month=11 | status `too_late`, 0 warnings |
| `test_evaluate_incompatible_pair` | `["tomato","fennel"]`, month=5 | 2 plants, 1 warning |
| `test_evaluate_empty_plant_list` | `[]`, month=6 | `plants: []`, `warnings: []`, HTTP 200 |
| `test_evaluate_duplicate_plant_ids` | `["tomato","tomato"]`, month=5 | 2 plant entries, 0 warnings |

**Error handling:**

| Test | Input | Expected |
|---|---|---|
| `test_unknown_plant_id` | `["does_not_exist"]`, month=5 | HTTP 404, `detail` contains `"does_not_exist"` |
| `test_invalid_month_zero` | `[]`, month=0 | HTTP 422 |
| `test_invalid_month_thirteen` | `[]`, month=13 | HTTP 422 |

**Response shape:**

| Test | Passes When |
|---|---|
| `test_response_has_plants_key` | `"plants"` key present in response body |
| `test_response_has_warnings_key` | `"warnings"` key present in response body |
| `test_each_plant_has_id_and_status` | Every entry in `plants` has `id` and `status` |
| `test_status_values_are_valid_enum` | `status` is one of `too_early`, `plant_now`, `too_late` |

```python
# backend/tests/test_api.py
def test_evaluate_incompatible_pair(client):
    response = client.post("/evaluate", json={
        "plant_ids": ["tomato", "fennel"],
        "current_month": 5
    })
    assert response.status_code == 200
    body = response.json()
    assert len(body["plants"]) == 2
    assert len(body["warnings"]) == 1
    assert body["warnings"][0]["type"] == "compatibility"

def test_unknown_plant_id(client):
    response = client.post("/evaluate", json={
        "plant_ids": ["does_not_exist"],
        "current_month": 5
    })
    assert response.status_code == 404
    assert "does_not_exist" in response.json()["detail"]

def test_evaluate_duplicate_plant_ids(client):
    response = client.post("/evaluate", json={
        "plant_ids": ["tomato", "tomato"],
        "current_month": 5
    })
    assert response.status_code == 200
    body = response.json()
    assert len(body["plants"]) == 2
    assert body["warnings"] == []
```

---

## Phase 5 — React Frontend

**Goal:** Build the UI against the live API. All plant/rule logic remains in the backend — the frontend only renders what the API returns.

### Tasks

1. Create `frontend/src/types.ts` with the TypeScript interfaces shown in the Configuration section above

2. Implement `frontend/src/api.ts`:
   ```typescript
   const API_BASE = "http://localhost:8000";

   export async function fetchPlants(): Promise<Plant[]> {
     const res = await fetch(`${API_BASE}/plants`);
     return res.json();
   }

   export async function evaluate(
     plantIds: string[],
     currentMonth: number
   ): Promise<EvaluateResponse> {
     const res = await fetch(`${API_BASE}/evaluate`, {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({ plant_ids: plantIds, current_month: currentMonth }),
     });
     return res.json();
   }
   ```

3. Build components with required `data-testid` attributes (see Conventions):
   - `PlantSelector` — `<select data-testid="plant-selector">` + `<button data-testid="add-plant-btn">`
   - `GardenList` — `<ul data-testid="garden-list">`, each `<li data-testid="garden-item-{i}">` with `<button data-testid="remove-plant-{i}">`
   - `WarningsPanel` — `<div data-testid="warnings-panel">` — rendered only when `warnings.length > 0`
   - `ScheduleDisplay` — `<div data-testid="schedule-display">`, each badge `<span data-testid="status-badge-{plant_id}-{i}">`

4. Wire state in `App.tsx`:
   - `availablePlants: Plant[]` — loaded on mount via `fetchPlants()`
   - `selectedIds: string[]` — mutated by add/remove actions (duplicates allowed)
   - `evaluateResult: EvaluateResponse | null` — result of calling `evaluate(selectedIds, currentMonth)`
   - `currentMonth: number` — derived once as `new Date().getMonth() + 1`, stored in state
   - Any change to `selectedIds` triggers a new `evaluate` call

5. Configure Playwright:
   ```bash
   cd frontend
   npm install -D @playwright/test
   npx playwright install chromium
   ```
   Add `playwright.config.ts` with `baseURL: "http://localhost:5173"` and `webServer` pointing to `npm run dev`

### Phase 5 Success Tests

**Playwright (end-to-end):**

| Test | Steps | Passes When |
|---|---|---|
| `test_plant_appears_in_garden_list` | Select "tomato", click Add | `[data-testid="garden-list"]` contains "Tomato" |
| `test_remove_plant_updates_list` | Add then remove "tomato" | "Tomato" no longer in garden list |
| `test_incompatible_warning_appears` | Add "tomato" then "fennel" | `[data-testid="warnings-panel"]` visible, contains both names |
| `test_warning_clears_on_remove` | Add "tomato" + "fennel", remove "fennel" | `[data-testid="warnings-panel"]` not visible |
| `test_schedule_status_displayed` | Add "tomato" | `[data-testid^="status-badge-tomato"]` visible with non-empty text |
| `test_duplicate_plants_allowed` | Add "tomato" twice | Two `[data-testid^="garden-item"]` elements visible |
| `test_empty_state_no_warnings` | Load page without adding anything | `[data-testid="warnings-panel"]` not present in DOM |

> `test_schedule_status_displayed` does not assert a specific status value because the result depends on the current month at test runtime. It only asserts the badge is visible and non-empty.

```python
# frontend/tests/e2e/test_garden.py
from playwright.sync_api import Page, expect

def test_incompatible_warning_appears(page: Page):
    page.goto("http://localhost:5173")
    page.select_option("[data-testid='plant-selector']", "tomato")
    page.click("[data-testid='add-plant-btn']")
    page.select_option("[data-testid='plant-selector']", "fennel")
    page.click("[data-testid='add-plant-btn']")
    warnings = page.locator("[data-testid='warnings-panel']")
    expect(warnings).to_be_visible()
    expect(warnings).to_contain_text("Tomato")
    expect(warnings).to_contain_text("Fennel")

def test_empty_state_no_warnings(page: Page):
    page.goto("http://localhost:5173")
    expect(page.locator("[data-testid='warnings-panel']")).not_to_be_visible()
```

---

## Phase Completion Checklist

| Phase | Done When |
|---|---|
| Phase 1 | `pytest` finds and passes `test_health_returns_ok`; React loads at `localhost:5173` |
| Phase 2 | All 5 plant data tests pass; `/plants` returns valid seed data |
| Phase 3 | All 16 rules unit tests pass with zero API involvement |
| Phase 4 | All 13 API tests pass; unknown IDs return 404, invalid months return 422 |
| Phase 5 | All 7 Playwright tests pass against live backend |

---

## Key Constraints to Preserve

- **No business logic in the frontend.** The React app calls `/evaluate` and renders the result — it does not compute statuses or warnings itself.
- **`current_month` is always an explicit parameter** — rules functions never call `datetime.now()` or `date.today()` internally. This keeps logic deterministic and testable.
- **Warnings deduplicate by unordered pair.** The set `{A, B}` and `{B, A}` are the same pair. Use `itertools.combinations` to generate pairs — it guarantees each pair appears once.
- **Same-ID plants never warn each other.** Two instances of `tomato` in the garden list are not incompatible.
- **All field names are `snake_case`** across the Python models, JSON wire format, and TypeScript types.
