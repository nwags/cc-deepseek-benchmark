import assert from "node:assert/strict";
import test from "node:test";
import ts from "typescript";
import { Buffer } from "node:buffer";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const sourcePath = join(here, "run-plan-validation.ts");
const source = await readFile(sourcePath, "utf8");

const transpiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.ES2022,
    target: ts.ScriptTarget.ES2022,
  },
}).outputText;

const moduleUrl = `data:text/javascript;base64,${Buffer.from(transpiled).toString("base64")}`;
const {
  hasFinding,
  promotionReviewEvidenceKey,
  validateRunPlan,
} = await import(moduleUrl);

const gpt = {
  arm_id: "router-gpt-5.5",
  provider: "openai",
  backend_model: "gpt-5.5",
};

const geminiPro = {
  arm_id: "router-gemini-3.1-pro",
  provider: "google-gemini",
  backend_model: "gemini-3.1-pro-preview",
};

const geminiFlash = {
  arm_id: "router-gemini-flash",
  provider: "google-gemini",
  backend_model: "gemini-3.5-flash",
};

const anthropic = {
  arm_id: "router-anthropic-opus",
  provider: "anthropic",
  backend_model: "claude-opus-4-7",
};

const qwen = {
  arm_id: "router-qwen-3.7-plus",
  provider: "dashscope",
  backend_model: "qwen3.7-plus",
};

const fable = {
  arm_id: "router-anthropic-fable-5",
  provider: "anthropic",
  backend_model: "claude-fable-5",
};

function plan(overrides) {
  return validateRunPlan({
    selectedArms: [],
    runMode: "smoke",
    dryRun: true,
    confirmPaidRun: false,
    nConcurrent: "1",
    runnerSlots: 3,
    ...overrides,
  });
}

test("3 arms with n_concurrent=1 gives effective concurrency 3", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, anthropic], nConcurrent: "1" });
  assert.equal(result.effectiveTaskParallelism, 3);
  assert.equal(result.harborConcurrency, 1);
  assert.equal(result.status, "clear");
});

test("3 arms with n_concurrent=2 warns and gives effective concurrency 6", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, anthropic], nConcurrent: "2" });
  assert.equal(result.effectiveTaskParallelism, 6);
  assert.equal(result.harborConcurrency, 2);
  assert.equal(result.status, "review");
  assert.equal(hasFinding(result, "Harbor concurrency above checked-in assumption", "warning"), true);
});

test("2 Gemini arms is blocked", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, geminiFlash] });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Gemini provider-family concurrency exceeded", "blocker"), true);
});

test("Qwen full mode is blocked", () => {
  const result = plan({ selectedArms: [qwen], runMode: "full" });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Qwen full sweep blocked", "blocker"), true);
});

test("Fable selected is blocked", () => {
  const result = plan({ selectedArms: [fable] });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Fable planner gate", "blocker"), true);
});

test("4 selected arms exceeds 3-slot runner capacity", () => {
  const result = plan({ selectedArms: [gpt, geminiPro, anthropic, qwen] });
  assert.equal(result.status, "blocked");
  assert.equal(hasFinding(result, "Runner-slot capacity exceeded", "blocker"), true);
});


function promotionGate(overrides = {}) {
  return {
    gate_id: "gate-1",
    arm_id: "router-gpt-5.5",
    source_arm_run_id: "run-1",
    usage_reconciliation_id: "usage-1",
    cost_reconciliation_id: "cost-1",
    source_mode: "canary",
    target_mode: "smoke",
    decision: "pass",
    blocker_codes: [],
    derived_blocker_codes: [],
    waiver_reason: null,
    effective_can_advance: true,
    reviewed_by: "reviewer",
    reviewed_at: "2026-08-30T12:00:00Z",
    usage_validation_status: "validated_exact",
    cost_validation_status: "validated_exact",
    selected_usage_authority: "provider_request_usage",
    selected_cost_basis: "provider_billed",
    selected_cost_relation: "exact",
    selected_cost_usd: "1.25",
    usage_limitation_codes: [],
    cost_limitation_codes: [],
    ...overrides,
  };
}

test("Canary planning does not require predecessor promotion evidence", () => {
  const result = plan({
    selectedArms: [gpt],
    runMode: "canary",
    promotionGateLoadStatus: "unavailable",
    promotionGates: [],
    promotionReviewConfirmed: false,
  });

  assert.equal(result.status, "clear");
  assert.equal(
    hasFinding(result, "Canary is the entry evidence stage", "ok"),
    true,
  );
  assert.equal(
    hasFinding(result, "Promotion evidence unavailable", "blocker"),
    false,
  );
});

test("Smoke planning fails closed when its current Canary gate is missing", () => {
  const result = plan({
    selectedArms: [gpt],
    runMode: "smoke",
    promotionGateLoadStatus: "available",
    promotionGates: [],
    promotionReviewConfirmed: true,
  });

  assert.equal(result.status, "blocked");
  assert.equal(
    hasFinding(
      result,
      "Promotion gate missing: router-gpt-5.5",
      "blocker",
    ),
    true,
  );
});

test("Evidence-qualified Smoke still requires explicit human review", () => {
  const unconfirmed = plan({
    selectedArms: [gpt],
    runMode: "smoke",
    promotionGateLoadStatus: "available",
    promotionGates: [promotionGate()],
    promotionReviewConfirmed: false,
  });

  assert.equal(unconfirmed.status, "blocked");
  assert.equal(
    hasFinding(
      unconfirmed,
      "Promotion evidence qualified: router-gpt-5.5",
      "ok",
    ),
    true,
  );
  assert.equal(
    hasFinding(
      unconfirmed,
      "Human promotion review not confirmed",
      "blocker",
    ),
    true,
  );

  const confirmed = plan({
    selectedArms: [gpt],
    runMode: "smoke",
    promotionGateLoadStatus: "available",
    promotionGates: [promotionGate()],
    promotionReviewConfirmed: true,
  });

  assert.equal(confirmed.status, "clear");
  assert.equal(
    hasFinding(
      confirmed,
      "Human promotion review confirmed",
      "ok",
    ),
    true,
  );
});

test("Recorded waiver never becomes Planner authorization", () => {
  const result = plan({
    selectedArms: [gpt],
    runMode: "smoke",
    promotionGateLoadStatus: "available",
    promotionGates: [
      promotionGate({
        decision: "waived",
        waiver_reason: "manual exception retained for audit",
        effective_can_advance: false,
        derived_blocker_codes: ["gate_decision_not_pass"],
      }),
    ],
    promotionReviewConfirmed: true,
  });

  assert.equal(result.status, "blocked");
  assert.equal(
    hasFinding(
      result,
      "Promotion waiver is not authorization: router-gpt-5.5",
      "blocker",
    ),
    true,
  );
});

test("Full planning blocks a pass record that is not effectively current", () => {
  const result = plan({
    selectedArms: [gpt],
    runMode: "full",
    promotionGateLoadStatus: "available",
    promotionGates: [
      promotionGate({
        gate_id: "gate-full",
        source_mode: "smoke",
        target_mode: "full",
        effective_can_advance: false,
        derived_blocker_codes: ["cost_reconciliation_not_current"],
      }),
    ],
    promotionReviewConfirmed: true,
  });

  assert.equal(result.status, "blocked");
  assert.equal(
    hasFinding(
      result,
      "Promotion evidence is stale or inconsistent: router-gpt-5.5",
      "blocker",
    ),
    true,
  );
});

test("Smoke and Full fail closed when promotion evidence cannot be loaded", () => {
  for (const runMode of ["smoke", "full"]) {
    const result = plan({
      selectedArms: [gpt],
      runMode,
      promotionGateLoadStatus: "unavailable",
      promotionGates: [],
      promotionReviewConfirmed: true,
    });

    assert.equal(result.status, "blocked");
    assert.equal(
      hasFinding(result, "Promotion evidence unavailable", "blocker"),
      true,
    );
  }
});


test("promotion review acknowledgement key binds the exact evidence packet", () => {
  const base = {
    selectedArmIds: ["router-gpt-5.5"],
    runMode: "smoke",
    promotionGateLoadStatus: "available",
    promotionGates: [promotionGate()],
  };

  const original = promotionReviewEvidenceKey(base);

  const mutations = [
    { source_arm_run_id: "run-2" },
    { usage_reconciliation_id: "usage-2" },
    { cost_reconciliation_id: "cost-2" },
    { decision: "blocked", blocker_codes: ["review_blocker"] },
    { effective_can_advance: false },
    { waiver_reason: "changed waiver context" },
    { reviewed_by: "other-reviewer" },
    { reviewed_at: "2026-08-30T13:00:00Z" },
    { usage_validation_status: "validated_qualified" },
    { cost_validation_status: "validated_qualified" },
    { selected_usage_authority: "harness_usage_validated" },
    {
      selected_cost_basis:
        "provider_rate_reconstructed_harness_usage_validated",
    },
    { selected_cost_relation: "estimate" },
    { selected_cost_usd: "1.2500001" },
    { usage_limitation_codes: ["usage_limit"] },
    { cost_limitation_codes: ["cost_limit"] },
    { derived_blocker_codes: ["cost_reconciliation_not_current"] },
  ];

  for (const mutation of mutations) {
    const changed = promotionReviewEvidenceKey({
      ...base,
      promotionGates: [promotionGate(mutation)],
    });
    assert.notEqual(
      changed,
      original,
      `review key must change for ${Object.keys(mutation).join(",")}`,
    );
  }

  const reorderedCodes = promotionReviewEvidenceKey({
    ...base,
    promotionGates: [
      promotionGate({
        blocker_codes: ["b", "a"],
        usage_limitation_codes: ["u2", "u1"],
      }),
    ],
  });

  const reorderedCodesAgain = promotionReviewEvidenceKey({
    ...base,
    promotionGates: [
      promotionGate({
        blocker_codes: ["a", "b"],
        usage_limitation_codes: ["u1", "u2"],
      }),
    ],
  });

  assert.equal(
    reorderedCodes,
    reorderedCodesAgain,
    "set-like code ordering must not invalidate an otherwise identical packet",
  );
});
