# Artifact Evidence and Trial Diagnosis v1.3 browser acceptance

Date: 2026-08-01

Build under test: optimized Next.js production build served read-only at `http://127.0.0.1:3001`. The user's existing development server on port 3000 was left running and unmodified.

## Corpus review

- `/comprehensive-review` returned 200 and defaulted to the high-priority queue: rows 1–25 of 66; disagreement rows 1–25 of 1,223.
- `priority=high&queue_page=2` returned rows 26–50 and page 2 of 3.
- `priority=medium&arm=router-kimi-k3&reason=timeout` returned all 8 matching queue rows.
- `disagreement_page=2` returned rows 26–50 and page 2 of 49.
- Kimi K3 + timeout-reliability + raw-failure filtering returned 110 matching disagreement rows.
- Kimi K3 + `not_recorded` outcome filtering returned 10 rows. Displayed arm summaries distinguish `success`, `failure`, and `not_recorded` rather than inferring failure from a success count.

## Representative trials

- Substantive success `20c82fa9-1a3b-450f-9535-b59b32e4120c`: raw success, substantive execution/activity, validated snapshot.
- Substantive failure `84bed545-ad08-4e84-b596-faa88791b46b`: raw failure, substantive execution, test-assertion failure detail.
- Empty completion `7eceb1c8-4a7b-4899-9650-b54f7d432d24`: long API-path empty completion.
- Policy refusal `f286e656-db4c-4d69-a773-c72f380b4c4c`: policy blocked, provider-policy refusal, 9/9 canonical evidence.
- Incomplete evidence `c8e2ab43-fa99-48e1-a5dd-9d49b2006cf5`: 7/9 canonical evidence, missing CTRF and reward artifacts; meaningful-activity timeout remains separately visible.
- Optional live reanalysis of the empty-completion trial matched the validated snapshot, displayed the live-analysis controls, and correctly showed no false snapshot/live warning. The positive mismatch selector is covered by the deterministic `changedAnalysisAxes` regression test.

## Safety and layout

- Rendered acceptance pages contained no unredacted bearer token, URL userinfo, or supported secret assignment pattern.
- Configuration/endpoint and exception-summary display paths retained safe context while using the common redactor.
- A 390 × 844 Chrome capture showed a narrow-screen two-column navigation and single-column content with no observed horizontal overflow.
- A 1,440 × 1,000 Chrome capture confirmed readable task-local numbering, derived/snapshot badges, and the policy-refusal quick diagnosis.

Screenshots are operational acceptance artifacts outside Git:

- `/tmp/comprehensive-review-narrow-20260801.png`
- `/tmp/trial-policy-refusal-wide-20260801.png`

## v1.3.1 development-server React-key recheck

Date: 2026-08-02 UTC

The prior development server was not running when checked. Only `apps/dashboard/.next` was removed, then `npm run dev -- --hostname 127.0.0.1 --port 3000` was started from a clean development cache. Headless Chrome rendered these representative run pages:

- Gemini Flash: HTTP 200; 60 trial rows, 20 distinct tasks, attempts 1/2/3 each present 20 times, run ordinals 1–60 unique.
- Anthropic Haiku sanitized: HTTP 200; same 60/20/20×3/1–60 structure.
- GPT-5.5: HTTP 200; same 60/20/20×3/1–60 structure.
- Fable 5: HTTP 200; same 60/20/20×3/1–60 structure.

The Next.js server console contained only successful GET lines for these pages—no duplicate-key, hydration, module-resolution, or runtime warnings. `/artifacts` also returned HTTP 200 after the clean restart and rendered the lifecycle guide plus artifact-type reference, confirming `artifact-types.ts` resolved normally. No trial attempt was duplicated or omitted in the rendered DOM. Acceptance logging contains counts and route labels only; no credential values or artifact excerpts were recorded.
