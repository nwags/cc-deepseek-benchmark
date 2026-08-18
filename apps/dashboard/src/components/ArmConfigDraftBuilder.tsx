"use client";

import { useMemo, useState } from "react";

import {
  ARM_DRAFT_OMITTED_PROVIDER_FIELDS,
  buildArmConfigDraft,
  type ArmDraftRouteKind,
} from "../lib/arm-config-draft";

export function ArmConfigDraftBuilder({ existingArmIds }: { existingArmIds: readonly string[] }) {
  const [routeKind, setRouteKind] = useState<ArmDraftRouteKind>("direct");
  const [armId, setArmId] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [backendModel, setBackendModel] = useState("");
  const [expectedObservedModel, setExpectedObservedModel] = useState("");
  const [jobDirName, setJobDirName] = useState("");
  const [notes, setNotes] = useState("");

  const draft = useMemo(() => buildArmConfigDraft({
    routeKind,
    armId,
    displayName,
    provider,
    model,
    backendModel,
    expectedObservedModel,
    jobDirName,
    notes,
  }, existingArmIds), [
    armId,
    backendModel,
    displayName,
    existingArmIds,
    expectedObservedModel,
    jobDirName,
    model,
    notes,
    provider,
    routeKind,
  ]);

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Draft new arm configuration</h2>
          <p>Build a reviewable YAML scaffold for a future checked-in arm configuration.</p>
        </div>
      </div>

      <div className="quality-context-panel">
        <p><strong>Draft only — no repository file is created.</strong></p>
        <p>
          Provider/router-specific environment, secret mapping, safety fields, and validation may still be required.
          Compare this draft with an audited existing arm, then submit the resulting configuration through normal Git review.
          This helper does not request or generate API keys or tokens, and the draft is not ready to run.
        </p>
      </div>

      <div className="planner-grid">
        <label className="form-field">
          <span>Route kind</span>
          <select value={routeKind} onChange={(event) => setRouteKind(event.target.value as ArmDraftRouteKind)}>
            <option value="direct">direct</option>
            <option value="litellm-routed">LiteLLM-routed</option>
          </select>
        </label>
        <label className="form-field">
          <span>arm_id</span>
          <input value={armId} onChange={(event) => setArmId(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>display_name</span>
          <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>provider</span>
          <input value={provider} onChange={(event) => setProvider(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>model / route model alias</span>
          <input value={model} onChange={(event) => setModel(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>backend_model{routeKind === "litellm-routed" ? " — required for routed draft" : " — optional"}</span>
          <input value={backendModel} onChange={(event) => setBackendModel(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>expected_observed_model</span>
          <input value={expectedObservedModel} onChange={(event) => setExpectedObservedModel(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>job_dir_name</span>
          <input value={jobDirName} onChange={(event) => setJobDirName(event.target.value)} autoComplete="off" />
        </label>
        <label className="form-field">
          <span>notes</span>
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
        </label>
      </div>

      <div aria-live="polite">
        {draft.existingArmCollision ? (
          <p className="warning-text" role="alert">
            This arm_id exactly matches an existing checked-in arm. The suggested destination would collide; no file will be overwritten or renamed automatically.
          </p>
        ) : null}
        {!draft.destinationArmIdIsValid && armId !== "" ? (
          <p className="warning-text" role="alert">
            arm_id must start with a lowercase letter or number and contain only lowercase letters, numbers, dots, underscores, or hyphens before a destination can be suggested.
          </p>
        ) : null}
        {draft.missingFields.length ? (
          <p className="muted">Draft fields still needed: {draft.missingFields.join(", ")}.</p>
        ) : null}
      </div>

      <div className="generated-command">
        <div className="panel-heading flush-heading">
          <div>
            <h3>Generated YAML draft</h3>
            <p>Suggested future destination: <span className="mono">{draft.suggestedDestination}</span></p>
          </div>
        </div>
        <pre>{draft.yaml}</pre>
      </div>

      <div className="quality-context-panel">
        <p><strong>Provider-specific fields are intentionally not generated.</strong></p>
        <p className="mono">{ARM_DRAFT_OMITTED_PROVIDER_FIELDS.join(", ")}</p>
        <p>Use an audited existing arm as a structural reference without copying secret values.</p>
      </div>
    </section>
  );
}
