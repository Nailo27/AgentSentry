# UI-01 Sprint 3 — dashboard presentation changes

**Owner:** Braden Hardman  
**Input:** *AgentSentry User Testing Report* (5 participants, moderated sessions)  
**Sprint 3 tasks covered:**

1. Coordinate with Caleb to add approved cases to `services/dashboard/app.py`
   after integration.
2. Ensure the dashboard shows the scenario, observed behaviour, verdict
   explanation and matching evidence.
3. Keep the build guide aligned with the integrated checkout and shared
   gateway configuration.

---

## 1. What the user testing found

All five participants completed all four activities without help, so the
function of the page was sound. The problems were about form:

* **Structure.** Participants scrolled up and down because they could not tell
  where one section ended and the next began. The results section took about
  three times longer to read than any other.
* **Jargon.** Most participants had no cybersecurity background.
* **Clutter.** The sidebar held information most participants did not need.
* **Colour worked.** Every participant judged the outcome by the coloured
  indicator and the large ALLOW / DENY text before reading anything else.
* **Setup.** No participant, technical or not, could set the lab up from the
  terminal instructions.

## 2. Finding → change

| Report finding | Change | Where |
|---|---|---|
| Sidebar too large, "random stuff in the left menu" | Sidebar removed. Agent status is a small label under the title; agent address, policy source and rule count moved to a collapsed **Lab details** panel. "Clear recorded findings" moved into **Past results → Manage history**, so it cannot be clicked by accident. | `app.py`, header section |
| Sections not clearly separated | Each part is a numbered step on a white card over a grey page: 1 Choose a test, 2 Choose the AI model, 3 Review and run, 4 Result, 5 Past results. | `app.py` (`step_header`, `st.container(border=True)`); `.streamlit/config.toml` |
| Hierarchical text needed | One heading size per level: page title → numbered step titles → card headings → body text. Secondary information is in grey captions or collapsed panels. | `app.py` CSS block |
| Results section hard to read (3× time) | Result split into four parts: banner + decision tiles, **Why this result**, **Scenario** / **What happened** side by side, **Evidence**. Technical detail (rule text, stop reason, raw notes, raw JSON) is collapsed. | `app.py`, Step 4 |
| Colour should be bigger and always visible | Full-width banner in the verdict colour with a symbol (✓ ! ✕) and a one-line headline. The same three colours are used for the history tiles and the history table. | `explain.RESULT_STYLE`, `app.py` |
| ALLOW / DENY in large text worked | Kept and enlarged: **Policy says** and **Gateway did** tiles, with "matches the policy" or "does NOT match the policy" underneath. | `app.py`, decision tiles |
| Jargon; "i" button with info on hover | Small circled **i** markers next to terms show a one- or two-sentence definition on hover. Form fields use Streamlit's built-in help tooltip with the same text. On-page labels were reworded (e.g. "Expected decision" → "Policy says", "Canaries disclosed" → "Protected data leaked"). | `explain.GLOSSARY`, `explain.info_icon` |
| Too many descriptors | Scan ID and Test ID moved into a collapsed **Advanced** panel; each scenario shows three short lines (what it tests, who is asking, what a safe result looks like). | `app.py`, Steps 1 and 3 |
| Setup too hard for new users | Added a click-by-click first-time setup guide. | `docs/infrastructure/FIRST-TIME-SETUP.md` |

Not changed, deliberately:

* **The flow.** The report found participants could always infer the next
  step. The order (choose → run → read result) is unchanged; it is now
  numbered.
* **Button labels "Submit to target agent" and "Check model connection".**
  Javon's provider-selection tests find the buttons by these exact labels.
  Renaming them would require editing a teammate's test file.
* **Everything the Sprint 2 page displayed.** Each item is still on the page,
  though some moved: stop reason, policy-row text and assessment notes are in
  the collapsed **Technical notes** panel under **Why this result**; the
  policy ID is in the trace table, the **What happened** sentences and the
  history table's **Rule** column; agent status and policy details are in
  **Lab details**.
* **The verdict rules.** `assessment.py` is untouched. Only the presentation
  of its result changed.

## 3. Scenario, observed behaviour, explanation, evidence

| Required | Shown as | Source |
|---|---|---|
| Scenario | **Scenario** card: test ID, what it tests, who asked, actual role (with the claimed role if different), model used, the exact message. | The finding plus the scenario definition |
| Observed behaviour | **What happened** card: one plain sentence per step in the agent's trace, including every tool request, the gateway's decision and reason, and the final reply. | `explain.observed_steps()` over the full `steps` list |
| Verdict explanation | Banner headline plus **Why this result**: plain-language reason, identity-claim note, over-blocking note, and collapsed technical notes. | `explain.verdict_explanation()` |
| Matching evidence | **Evidence** card naming the test ID and scan ID it belongs to, listing the evidence events present, the step-by-step trace table, the JSONL download (file name includes both IDs), the JSONL itself and the raw agent response. | `evidence_export.build_events()` for this finding |

`verdict_explanation()` re-derives which verdict rule applied from the
finding's fields. `tests/test_presentation.py` runs every rule in
`assessment.assess()` (canary leak, deny/allow, deny/deny, approval-gated
allow and deny, allow/allow, allow/deny, no tool request, no decision) and
asserts the explanation describes the same verdict that was assigned. If the
rules change and the wording does not, the test fails.

## 4. Approved cases (with Caleb)

`app.py` now has an `APPROVED_CASES` list directly under the built-in
scenarios. Adding a case is a data-only change: one dictionary with the same
fields as the built-in scenarios. The case appears in the Scenario menu
automatically.

Each entry is checked when the page loads (`explain.validate_case()`):
required fields present, role in the permission matrix, user in the matrix
identity table (so the expected decision uses the real role), a valid expected
result, and no duplicate test ID. An invalid case is listed in a warning and
left out of the menu instead of producing a result scored against the wrong
role.

**Open:** the list is empty. It is filled once Caleb confirms which cases are
approved. Two constraints to agree with him: the agent's only tool is
`read_file`, and every `user` must be in the matrix identity table.

## 5. Build guide and shared gateway

* `compose.yaml` and `.env.example` now default to the shared GW-01 gateway,
  `gateway.app:app`. The Sprint 1 defects that made `demo_gateway:app` the
  default were fixed during Sprint 2 integration, and Ying's adversarial cases
  and Carter's real-gateway evidence are produced against the shared gateway.
* A `.env` created before this change still selects `demo_gateway:app` and
  overrides the default. `BUILD.md` gives a one-line check and the fix.
* `BUILD.md` gained "Update an existing checkout" (a pull needs `build`
  before `up`), the gateway check, and the matching troubleshooting rows. The
  expected policy ID for AGENT-PRIV-002 is now stated (`POL-FILE-004`).
* `docs/infrastructure/BUILD.md` described building from unmerged Sprint 1
  branches. It is replaced with a pointer so there is one build guide.

## 6. Security

* **HTML escaping.** The Sprint 1 badges inserted the test ID and policy ID
  into HTML unescaped. Both can be typed into the form. Every value placed in
  dashboard HTML now goes through `explain.esc()`, and a test submits a scan
  ID containing an `<img onerror>` payload and asserts it appears only in
  escaped form.
* **Credential handling unchanged.** The provider key flow from
  `model_connection.py` (key in a header only, cleared before sending, never
  stored) is untouched, and all of Javon's tests for it pass unmodified.
* **Ports still loopback only.** Nothing in this sprint changes the
  `127.0.0.1` bindings.

## 7. Files

| File | Status | Why it is included |
|---|---|---|
| `services/dashboard/app.py` | Changed | The redesigned page and the `APPROVED_CASES` slot. |
| `services/dashboard/explain.py` | New | Plain-language wording, glossary, validation and escaping, kept out of `app.py` so it can be unit-tested without a web server. |
| `services/dashboard/.streamlit/config.toml` | New | Fixed light theme and grey page background; hides the developer toolbar testers read as part of the page. |
| `services/dashboard/Dockerfile` | Changed | Copies `.streamlit/` into the image; the existing `*.py` glob does not match it. |
| `services/dashboard/requirements.txt` | Changed | Streamlit floor raised to 1.50 for the features the layout uses. |
| `services/dashboard/tests/test_presentation.py` | New | 25 tests: explanation agrees with every verdict rule, layout, escaping, case validation. |
| `services/dashboard/README.md` | Changed | Layout, approved cases and file list. |
| `compose.yaml`, `.env.example` | Changed | Shared gateway as the default. |
| `BUILD.md` | Changed | Aligned with the integrated checkout and shared gateway. |
| `docs/infrastructure/BUILD.md` | Replaced | Pointer to the single build guide. |
| `docs/infrastructure/FIRST-TIME-SETUP.md` | New | Beginner setup guide recommended by the report. |
| `docs/infrastructure/INF-02-container-environment.md` | Changed | Gateway-switch section matches the new default. |
| `docs/infrastructure/UI-01-sprint3-dashboard-changes.md` | New | This document. |
| `CHANGELOG.md` | Changed | Sprint 3 entry. |

Only files within the INF-02 / UI-01 deliverables were changed. Teammates'
additions inside them (Javon's provider selection, the display of Ying's
adversarial cases) are preserved, and their tests pass without modification.
Nothing under `services/target-agent/`, `scripts/` or `docs/policies/` was
touched.

## 8. Verification

* Dashboard tests: 66 passed (41 existing, unmodified, plus 25 new), on both
  Streamlit 1.50 and the current 1.x release.
* Target agent tests: 100 passed, unchanged.
* Live run against the shared gateway (`gateway.app:app`), agent and dashboard
  started as local processes: AGENT-PRIV-001 → WARNING, `DENY` /
  `POL-FILE-004`; AGENT-PRIV-002 → PASS, `ALLOW` / `POL-FILE-004`; PI-02 →
  WARNING, `DENY` / `POL-FILE-004`. Screenshots taken of each.
* `docker compose config` resolves the gateway command to `gateway.app:app`.
* Not verified: `docker compose build`, because container registries were not
  reachable from the environment the changes were made in. Run
  `.\make.ps1 build` and `.\make.ps1 up` once before the demo.
