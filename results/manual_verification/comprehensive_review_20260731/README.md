# Comprehensive evidence review

Generated: `2026-08-02T14:58:37.377646+00:00`

Analyzer: `artifact-evidence-v1.3.2`

Generator: `comprehensive-evidence-review-v1.3.2`

Suite: `phase3-full-20`

This directory is a local derived review layer. It reads Supabase and immutable R2 objects but does not write to either service. Raw rewards, stored quality flags, pass-rate denominators, historical results, and artifact bytes remain unchanged.

Coverage: 16 selected valid full-suite runs, 960 trials, and 7877 artifact metadata rows. The manual-review queue contains 565 trials. The control sample contains strict ordinary controls plus explicit timeout, telemetry-mismatch, exception-success, and incomplete-evidence strata.

`trial_review.csv` is the row-level validated snapshot. `trial_evidence.jsonl` contains transparent evidence facts and direct artifact identifiers, never hidden reasoning or raw configuration secrets. `targeted_evidence_packet.csv` indexes the sanitized `targeted_evidence_bundle.jsonl`; its independent packet manifest binds row counts and hashes. `review_manifest.json` binds source versions, scope, row counts, and output hashes. `run_review.csv` retains invalid and unselected candidates for provenance. See `docs/COMPREHENSIVE_EVIDENCE_REVIEW_METHOD.md` for bounds, precedence, sampling, and limitations.
