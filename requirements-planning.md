# Garden Planner Lite – Requirements Document

## 1. Overview

Garden Planner Lite is a lightweight web application that allows users to:

- Select plants for their garden
- View recommended planting schedules
- Receive compatibility warnings between selected plants

The system emphasizes rule-based logic, date calculations, and state-driven UI updates.

---

## 2. Goals

### Primary Goals

- Provide a simple interface for managing a small garden plan
- Surface planting timelines based on plant data
- Detect and warn about incompatible plant combinations

### Secondary Goals (QA-focused)

- Enable deterministic rule evaluation for test automation
- Provide clear API boundaries for contract testing
- Surface edge cases (date boundaries, conflicting rules)

---

## 3. Scope

### In Scope

- Plant selection and removal
- Rule evaluation (compatibility)
- Planting schedule generation
- UI reflecting current garden state

### Out of Scope

- User authentication
- Persistent storage (optional; can use in-memory or local storage)
- Advanced gardening recommendations (fertilizer, soil, etc.)

---

## 4. Users

### Target User

Casual home gardener planning a small seasonal garden

### QA Persona (important)

Engineer validating:

- Business rules
- API correctness
- UI consistency with backend state

---

## 5. Functional Requirements

### 5.1 Plant Management

**Description**

Users can add and remove plants from their garden plan.

**Requirements**

- User can select a plant from a predefined list
- Selected plants are displayed in a "Garden List"
- User can remove a plant from the list

**Acceptance Criteria**

- Adding a plant updates the garden list immediately
- Removing a plant updates the list and recalculates rules
- Duplicate plants: **Allowed** (represents multiple plantings)

---

### 5.2 Plant Data Model

**Plant Object**

```
Plant {
  id: string
  name: string
  plantingStartMonth: number (1–12)
  plantingEndMonth: number (1–12)
  incompatibleWith: string[] (plant ids)
}
```

---

### 5.3 Compatibility Rules Engine

**Description**

System evaluates selected plants for incompatibilities.

**Rules**

- If Plant A is incompatible with Plant B → warning is generated
- Rules are bidirectional OR explicitly defined (choose one and document)

**Output**

```
Warning {
  type: "compatibility"
  message: string
  plantsInvolved: string[]
}
```

**Acceptance Criteria**

- Warnings appear immediately after plant selection
- Warnings update when plants are removed
- No duplicate warnings for same pair

---

### 5.4 Planting Schedule

**Description**

System generates a simple planting schedule per plant.

**Logic**

Based on current date (system date), uses:
- `plantingStartMonth`
- `plantingEndMonth`

Output per plant:
- `"Too early"`
- `"Plant now"`
- `"Too late"`

**Rules**

| Condition | Status |
|---|---|
| current month < start | "Too early" |
| between start and end (inclusive) | "Plant now" |
| current month > end | "Too late" |

---

### 5.5 Calendar View

**Description**

UI displays planting status for each plant.

**Requirements**

Each plant shows:
- Name
- Status (Too early / Plant now / Too late)

**Acceptance Criteria**

Updates immediately when:
- Plant is added
- Plant is removed
- *(Optional)* simulated date changes

---

## 6. Non-Functional Requirements

### Performance

- Rule evaluation must complete < 200ms for up to 20 plants

### Reliability

- System must not crash on invalid or missing data
- Graceful handling of unknown plant IDs

### Testability (critical)

- Rules engine must be isolated and callable via API
- Deterministic outputs for given inputs
- Date logic must allow mocking current date

---

## 7. API Design (for testing focus)

### 7.1 `GET /plants`

Returns list of available plants.

### 7.2 `POST /evaluate`

**Input:**

```json
{
  "plantIds": ["string"],
  "currentMonth": 1
}
```

**Output:**

```json
{
  "plants": [
    {
      "id": "string",
      "status": "too_early" | "plant_now" | "too_late"
    }
  ],
  "warnings": []
}
```

**Acceptance Criteria**

- Response reflects correct status per plant
- Warnings accurately reflect incompatibilities
- Handles empty input

---

## 8. UI Requirements

### Main Screen Components

- Plant selector dropdown
- Garden list (selected plants)
- Warnings panel
- Planting schedule display

### Behavior

- UI must reflect API response exactly
- No hidden logic in frontend (all rules via API)

---

## 9. Edge Cases (explicitly required)

These are intentional for demo/testing value.

### Data Edge Cases

- Empty plant list
- Duplicate plants
- Unknown plant ID

### Rule Edge Cases

- Circular incompatibility (A ↔ B)
- Self-incompatibility (invalid data)

### Date Edge Cases

- Boundary months (start = current, end = current)
- Invalid month (0, 13)

---

## 10. Test Scenarios (built-in for demo)

### Functional

- Add plant → appears in list
- Remove plant → disappears + recalculates

### Rules

- Add incompatible plants → warning appears
- Remove one → warning disappears

### Date Logic

Test all 3 states:
- Before season
- In season
- After season

### API

- Valid request → correct structure
- Invalid request → graceful error

### UI

- State matches API response exactly

---

## 11. Suggested Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript |
| Backend | Python + FastAPI |
| Unit tests | pytest |
| API tests | pytest + httpx |
| UI tests | Playwright (Python) |

---

## 12. Stretch Goals (optional)

- Simulated "current date" selector (great for demos)
- Persist garden in local storage
- Add "companion plants" (positive rules)
