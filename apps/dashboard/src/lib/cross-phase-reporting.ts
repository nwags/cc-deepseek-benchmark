import type {
  CurrentReviewedPhase3Arm,
  CurrentReviewedPhase3Scope,
} from "./phase3-current-reviewed-comparison";

type HistoricalCrossPhaseRow = {
  phase: string;
  arm_id: string;
  backend_model: string;
  provider: string;
  routing_path: string;
  success_count: number;
  clean_success_count: number;
  trial_count: number;
  pass_rate: number;
  recorded_cost_usd: number;
  adjusted_cost_usd: number | null;
  known_accounting_gap_usd: number;
  cost_per_clean_success_usd: number | null;
  failure_incomplete_spend_share: number | null;
  unclean_spend_share: number | null;
  median_wall_clock_seconds: number | null;
  cost_confidence: string;
  reviewed_cost_basis?:
    | "adjusted_known_cost"
    | "qualified_retained_rate_estimate";
  reviewed_cost_label?: string;
  pricing_provenance_status?: string;
  arm_run_allocation_confidence?: string;
  trial_allocation_status?: string;
  billing_reconciliation_status?: string;
};

export type CrossPhaseRow = HistoricalCrossPhaseRow & {
  comparison_cost_usd: number | null;
  comparison_cost_per_attempt_usd: number | null;
  comparison_cost_per_clean_success_usd: number | null;
  comparison_cost_basis: string;
  comparison_cost_label: string;
  comparison_cost_confidence: string;
  comparison_cost_layer:
    | "frozen_historical_baseline"
    | "current_selected_phase3";

  historical_reviewed_cost_usd: number | null;
  historical_reviewed_cost_basis: string | null;
  historical_reviewed_cost_label: string | null;
  historical_unclean_spend_share: number | null;

  selected_trial_allocation_status: string | null;
  selected_outcome_allocation_status: string | null;

  provider_billed_cost_usd: number | null;
  provider_billing_reconciliation_status: string | null;
  provider_selected_run_label: string | null;
};

export type RouterComparisonRow = {
  model_family: string;
  direct_phase: string;
  direct_arm_id: string;
  router_arm_id: string;
  delta_success_count: number;
  delta_pass_rate_pct_points: number;
  router_vs_direct_cost_ratio: number | null;
  router_vs_direct_cost_per_clean_success_ratio: number | null;
  router_vs_direct_wall_clock_ratio: number | null;
  interpretation: string;
};

export type BehaviorRow = {
  arm_id: string;
  provider: string;
  backend_model: string;
  pass_rate: number;
  adjusted_cost_usd: number;
  cost_per_clean_success_usd: number;
  unclean_spend_share: number;
  exception_count: number;
  normal_failure_count: number;
  suspect_noop_count: number;
  behavior_tags: string;
};

export type PhaseSummary = {
  phase: string;
  arm_count: number;
  trial_count: number;
  success_count: number;
  clean_success_count: number;
  pass_rate: number;

  comparison_cost_usd: number | null;
  comparison_cost_basis: string;
  comparison_cost_label: string;
  comparison_cost_per_clean_success_usd: number | null;

  historical_reviewed_cost_usd: number | null;
  historical_unclean_spend_share: number | null;
};

const crossPhaseRows: HistoricalCrossPhaseRow[] = [
  {
    "phase": "phase1",
    "arm_id": "arm-a-anthropic",
    "backend_model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "routing_path": "phase1_direct",
    "success_count": 39.0,
    "clean_success_count": 38.0,
    "trial_count": 60.0,
    "pass_rate": 0.65,
    "recorded_cost_usd": 37.29553755,
    "adjusted_cost_usd": 37.29553755,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 0.9814615144736841,
    "failure_incomplete_spend_share": 0.45192304916918946,
    "unclean_spend_share": 0.48617579853062076,
    "median_wall_clock_seconds": 255.66746899999998,
    "cost_confidence": "high"
  },
  {
    "phase": "phase1",
    "arm_id": "arm-b-deepseek-pro",
    "backend_model": "deepseek-v4-pro",
    "provider": "deepseek",
    "routing_path": "phase1_direct",
    "success_count": 42.0,
    "clean_success_count": 41.0,
    "trial_count": 60.0,
    "pass_rate": 0.7,
    "recorded_cost_usd": 2.01041485,
    "adjusted_cost_usd": 2.01041485,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 0.04903450853658537,
    "failure_incomplete_spend_share": 0.28270258847321983,
    "unclean_spend_share": 0.2978273240470741,
    "median_wall_clock_seconds": 617.469616,
    "cost_confidence": "high"
  },
  {
    "phase": "phase1",
    "arm_id": "arm-c-deepseek-flash",
    "backend_model": "deepseek-v4-flash",
    "provider": "deepseek",
    "routing_path": "phase1_direct",
    "success_count": 37.0,
    "clean_success_count": 36.0,
    "trial_count": 60.0,
    "pass_rate": 0.6166666666666667,
    "recorded_cost_usd": 1.1029806424000002,
    "adjusted_cost_usd": 1.1029806424000002,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 0.030638351177777783,
    "failure_incomplete_spend_share": 0.5512594638805058,
    "unclean_spend_share": 0.558508417935223,
    "median_wall_clock_seconds": 262.6607965,
    "cost_confidence": "high"
  },
  {
    "phase": "phase2",
    "arm_id": "arm-anthropic-haiku",
    "backend_model": "claude-haiku-4-5-20251001",
    "provider": "anthropic",
    "routing_path": "phase2_direct",
    "success_count": 26.0,
    "clean_success_count": 25.0,
    "trial_count": 60.0,
    "pass_rate": 0.43333333333333335,
    "recorded_cost_usd": 14.310609750000001,
    "adjusted_cost_usd": 14.310609750000001,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 0.57242439,
    "failure_incomplete_spend_share": 0.7588925866698307,
    "unclean_spend_share": 0.810709686916031,
    "median_wall_clock_seconds": 154.678966,
    "cost_confidence": "high"
  },
  {
    "phase": "phase2",
    "arm_id": "arm-anthropic-opus",
    "backend_model": "claude-opus-4-7",
    "provider": "anthropic",
    "routing_path": "phase2_direct",
    "success_count": 45.0,
    "clean_success_count": 43.0,
    "trial_count": 60.0,
    "pass_rate": 0.75,
    "recorded_cost_usd": 50.92816825,
    "adjusted_cost_usd": 68.47110252299031,
    "known_accounting_gap_usd": 17.542934272990305,
    "cost_per_clean_success_usd": 1.592351221464891,
    "failure_incomplete_spend_share": 0.14972002771371065,
    "unclean_spend_share": 0.3837332838940071,
    "median_wall_clock_seconds": 246.828462,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase2",
    "arm_id": "arm-anthropic-sonnet",
    "backend_model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "routing_path": "phase2_direct",
    "success_count": 40.0,
    "clean_success_count": 39.0,
    "trial_count": 60.0,
    "pass_rate": 0.6666666666666666,
    "recorded_cost_usd": 28.362903499999998,
    "adjusted_cost_usd": 29.817549660881724,
    "known_accounting_gap_usd": 1.454646160881724,
    "cost_per_clean_success_usd": 0.7645525554072237,
    "failure_incomplete_spend_share": 0.36195877559184586,
    "unclean_spend_share": 0.3892331325973392,
    "median_wall_clock_seconds": 259.290067,
    "cost_confidence": "medium"
  },
  {
    "phase": "phase2",
    "arm_id": "arm-deepseek-flash",
    "backend_model": "deepseek-v4-flash",
    "provider": "deepseek",
    "routing_path": "phase2_direct",
    "success_count": 35.0,
    "clean_success_count": 35.0,
    "trial_count": 60.0,
    "pass_rate": 0.5833333333333334,
    "recorded_cost_usd": 0.7161240352000001,
    "adjusted_cost_usd": 0.7161240352000001,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 0.020460686720000003,
    "failure_incomplete_spend_share": 0.41936417664871023,
    "unclean_spend_share": 0.41936417664871023,
    "median_wall_clock_seconds": 283.3964105,
    "cost_confidence": "high"
  },
  {
    "phase": "phase2",
    "arm_id": "arm-deepseek-pro",
    "backend_model": "deepseek-v4-pro[1m]",
    "provider": "deepseek",
    "routing_path": "phase2_direct",
    "success_count": 39.0,
    "clean_success_count": 38.0,
    "trial_count": 60.0,
    "pass_rate": 0.65,
    "recorded_cost_usd": 1.712667703,
    "adjusted_cost_usd": 1.712667703,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 0.045070202710526315,
    "failure_incomplete_spend_share": 0.3404627120477673,
    "unclean_spend_share": 0.35907257311081553,
    "median_wall_clock_seconds": 566.5992484999999,
    "cost_confidence": "high"
  },
  {
    "phase": "phase3",
    "arm_id": "router-gpt-5.5",
    "backend_model": "gpt-5.5",
    "provider": "openai",
    "routing_path": "litellm_router",
    "success_count": 44.0,
    "clean_success_count": 42.0,
    "trial_count": 60.0,
    "pass_rate": 0.7333333333333333,
    "recorded_cost_usd": 168.708375,
    "adjusted_cost_usd": 183.958832348525,
    "known_accounting_gap_usd": 15.250457348525003,
    "cost_per_clean_success_usd": 4.379972198774,
    "failure_incomplete_spend_share": 0.2263435277281203,
    "unclean_spend_share": 0.2605678223577251,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase3",
    "arm_id": "router-deepseek-flash",
    "backend_model": "deepseek-v4-flash",
    "provider": "deepseek",
    "routing_path": "litellm_router",
    "success_count": 40.0,
    "clean_success_count": 40.0,
    "trial_count": 60.0,
    "pass_rate": 0.6666666666666666,
    "recorded_cost_usd": 56.35246,
    "adjusted_cost_usd": 56.7953838632,
    "known_accounting_gap_usd": 0.44292386320000077,
    "cost_per_clean_success_usd": 1.41988459658,
    "failure_incomplete_spend_share": 0.24446597449966964,
    "unclean_spend_share": 0.24446597449966964,
    "median_wall_clock_seconds": null,
    "cost_confidence": "medium"
  },
  {
    "phase": "phase3",
    "arm_id": "router-anthropic-fable-5",
    "backend_model": "claude-fable-5",
    "provider": "anthropic",
    "routing_path": "litellm_router",
    "success_count": 39.0,
    "clean_success_count": 37.0,
    "trial_count": 60.0,
    "pass_rate": 0.65,
    "recorded_cost_usd": 25.64316325,
    "adjusted_cost_usd": 37.68696425,
    "known_accounting_gap_usd": 12.043801000000002,
    "cost_per_clean_success_usd": 1.018566601351,
    "failure_incomplete_spend_share": 0.19438014299599626,
    "unclean_spend_share": 0.4611728709350741,
    "median_wall_clock_seconds": null,
    "cost_confidence": "medium"
  },
  {
    "phase": "phase3",
    "arm_id": "router-anthropic-opus",
    "backend_model": "claude-opus-4-7",
    "provider": "anthropic",
    "routing_path": "litellm_router",
    "success_count": 39.0,
    "clean_success_count": 39.0,
    "trial_count": 60.0,
    "pass_rate": 0.65,
    "recorded_cost_usd": 40.33090325,
    "adjusted_cost_usd": 64.49228375,
    "known_accounting_gap_usd": 24.1613805,
    "cost_per_clean_success_usd": 1.653648301282,
    "failure_incomplete_spend_share": 0.47658815850198516,
    "unclean_spend_share": 0.4765881585019851,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase3",
    "arm_id": "router-gpt-5.4",
    "backend_model": "gpt-5.4",
    "provider": "openai",
    "routing_path": "litellm_router",
    "success_count": 39.0,
    "clean_success_count": 38.0,
    "trial_count": 60.0,
    "pass_rate": 0.65,
    "recorded_cost_usd": 173.09483,
    "adjusted_cost_usd": 183.646689146806,
    "known_accounting_gap_usd": 10.55185914680601,
    "cost_per_clean_success_usd": 4.832807609126,
    "failure_incomplete_spend_share": 0.1877813084287655,
    "unclean_spend_share": 0.21565043906207979,
    "median_wall_clock_seconds": null,
    "cost_confidence": "low"
  },
  {
    "phase": "phase3",
    "arm_id": "router-glm-5.2",
    "backend_model": "glm-5.2",
    "provider": "zai-glm",
    "routing_path": "litellm_router",
    "success_count": 38.0,
    "clean_success_count": 35.0,
    "trial_count": 60.0,
    "pass_rate": 0.6333333333333333,
    "recorded_cost_usd": 20.549075,
    "adjusted_cost_usd": 25.3166398,
    "known_accounting_gap_usd": 4.767564800000002,
    "cost_per_clean_success_usd": 0.723332565714,
    "failure_incomplete_spend_share": 0.2714436297347802,
    "unclean_spend_share": 0.3250099485951528,
    "median_wall_clock_seconds": null,
    "cost_confidence": "medium"
  },
  {
    "phase": "phase3",
    "arm_id": "router-gemini-3.1-pro",
    "backend_model": "gemini-3.1-pro-preview",
    "provider": "google-gemini",
    "routing_path": "litellm_router",
    "success_count": 38.0,
    "clean_success_count": 36.0,
    "trial_count": 60.0,
    "pass_rate": 0.6333333333333333,
    "recorded_cost_usd": 38.1007875,
    "adjusted_cost_usd": 46.469402372843,
    "known_accounting_gap_usd": 8.368614872842997,
    "cost_per_clean_success_usd": 1.290816732579,
    "failure_incomplete_spend_share": 0.2974662903531183,
    "unclean_spend_share": 0.3112025684516729,
    "median_wall_clock_seconds": null,
    "cost_confidence": "low"
  },
  {
    "phase": "phase3",
    "arm_id": "router-deepseek-pro",
    "backend_model": "deepseek-v4-pro",
    "provider": "deepseek",
    "routing_path": "litellm_router",
    "success_count": 37.0,
    "clean_success_count": 37.0,
    "trial_count": 60.0,
    "pass_rate": 0.6166666666666667,
    "recorded_cost_usd": 50.203188,
    "adjusted_cost_usd": 50.439011911,
    "known_accounting_gap_usd": 0.23582391100000422,
    "cost_per_clean_success_usd": 1.363216538135,
    "failure_incomplete_spend_share": 0.24364218182315214,
    "unclean_spend_share": 0.24364218182315223,
    "median_wall_clock_seconds": null,
    "cost_confidence": "medium"
  },
  {
    "phase": "phase3",
    "arm_id": "router-glm-5.1",
    "backend_model": "glm-5.1",
    "provider": "zai-glm",
    "routing_path": "litellm_router",
    "success_count": 36.0,
    "clean_success_count": 35.0,
    "trial_count": 60.0,
    "pass_rate": 0.6,
    "recorded_cost_usd": 18.65261,
    "adjusted_cost_usd": 20.297031,
    "known_accounting_gap_usd": 1.6444210000000012,
    "cost_per_clean_success_usd": 0.579915171429,
    "failure_incomplete_spend_share": 0.19404437033179878,
    "unclean_spend_share": 0.20176354857023174,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase3",
    "arm_id": "router-grok-build-0.1",
    "backend_model": "grok-build-0.1",
    "provider": "xai",
    "routing_path": "litellm_router",
    "success_count": 36.0,
    "clean_success_count": 36.0,
    "trial_count": 60.0,
    "pass_rate": 0.6,
    "recorded_cost_usd": 38.149845,
    "adjusted_cost_usd": 53.153814003353,
    "known_accounting_gap_usd": 15.003969003353,
    "cost_per_clean_success_usd": 1.476494833426,
    "failure_incomplete_spend_share": 0.5612899951350809,
    "unclean_spend_share": 0.5612899951350809,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase3",
    "arm_id": "router-qwen-3.7-plus",
    "backend_model": "qwen3.7-plus",
    "provider": "dashscope-qwen",
    "routing_path": "litellm_router",
    "success_count": 33.0,
    "clean_success_count": 32.0,
    "trial_count": 60.0,
    "pass_rate": 0.55,
    "recorded_cost_usd": 20.43072,
    "adjusted_cost_usd": 34.944370078779,
    "known_accounting_gap_usd": 14.513650078779001,
    "cost_per_clean_success_usd": 1.092011564962,
    "failure_incomplete_spend_share": 0.47129850196657075,
    "unclean_spend_share": 0.548345127858391,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase3",
    "arm_id": "router-kimi-k2.6",
    "backend_model": "kimi-k2.6",
    "provider": "moonshot-kimi",
    "routing_path": "litellm_router",
    "success_count": 30.0,
    "clean_success_count": 30.0,
    "trial_count": 60.0,
    "pass_rate": 0.5,
    "recorded_cost_usd": 25.98573,
    "adjusted_cost_usd": 35.131541559739,
    "known_accounting_gap_usd": 9.145811559738998,
    "cost_per_clean_success_usd": 1.171051385325,
    "failure_incomplete_spend_share": 0.6282090275546384,
    "unclean_spend_share": 0.6282090275546383,
    "median_wall_clock_seconds": null,
    "cost_confidence": "low"
  },
  {
    "phase": "phase3",
    "arm_id": "router-anthropic-sonnet",
    "backend_model": "claude-sonnet-4-6",
    "provider": "anthropic",
    "routing_path": "litellm_router",
    "success_count": 28.0,
    "clean_success_count": 28.0,
    "trial_count": 60.0,
    "pass_rate": 0.4666666666666667,
    "recorded_cost_usd": 37.394878,
    "adjusted_cost_usd": 52.7917033,
    "known_accounting_gap_usd": 15.396825300000003,
    "cost_per_clean_success_usd": 1.885417975,
    "failure_incomplete_spend_share": 0.4416456818509207,
    "unclean_spend_share": 0.44164568185092073,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  },
  {
    "phase": "phase3",
    "arm_id": "router-anthropic-haiku-sanitized",
    "backend_model": "claude-haiku-4-5-20251001",
    "provider": "anthropic",
    "routing_path": "litellm_router",
    "success_count": 25.0,
    "clean_success_count": 25.0,
    "trial_count": 60.0,
    "pass_rate": 0.4166666666666667,
    "recorded_cost_usd": 83.51122425,
    "adjusted_cost_usd": 83.51122425,
    "known_accounting_gap_usd": 0.0,
    "cost_per_clean_success_usd": 3.34044897,
    "failure_incomplete_spend_share": 0.6564517433714906,
    "unclean_spend_share": 0.6564517433714906,
    "median_wall_clock_seconds": null,
    "cost_confidence": "high"
  },
  {
    "phase": "phase3",
    "arm_id": "router-gemini-flash",
    "backend_model": "gemini-3.5-flash",
    "provider": "google-gemini",
    "routing_path": "litellm_router",
    "success_count": 13.0,
    "clean_success_count": 9.0,
    "trial_count": 60.0,
    "pass_rate": 0.21666666666666667,
    "recorded_cost_usd": 23.6669395,
    "adjusted_cost_usd": 43.534953854953,
    "known_accounting_gap_usd": 19.868014354953,
    "cost_per_clean_success_usd": 4.837217094995,
    "failure_incomplete_spend_share": 0.5572406600157447,
    "unclean_spend_share": 0.6080827705285639,
    "median_wall_clock_seconds": null,
    "cost_confidence": "mixed"
  }
];

const routerComparisonRows: RouterComparisonRow[] = [
  {
    "model_family": "Anthropic Sonnet",
    "direct_phase": "phase1",
    "direct_arm_id": "arm-a-anthropic",
    "router_arm_id": "router-anthropic-sonnet",
    "delta_success_count": -11.0,
    "delta_pass_rate_pct_points": -18.333333333333336,
    "router_vs_direct_cost_ratio": 1.415496511592712,
    "router_vs_direct_cost_per_clean_success_ratio": 1.9210309800186807,
    "router_vs_direct_wall_clock_ratio": 0.6420459147268361,
    "interpretation": "router-associated pass rate lower; adjusted cost broadly similar"
  },
  {
    "model_family": "Anthropic Sonnet",
    "direct_phase": "phase2",
    "direct_arm_id": "arm-anthropic-sonnet",
    "router_arm_id": "router-anthropic-sonnet",
    "delta_success_count": -12.0,
    "delta_pass_rate_pct_points": -19.999999999999996,
    "router_vs_direct_cost_ratio": 1.7704909994418006,
    "router_vs_direct_cost_per_clean_success_ratio": 2.4660410349367936,
    "router_vs_direct_wall_clock_ratio": 0.6330757514131847,
    "interpretation": "router-associated pass rate lower; router run materially more expensive"
  },
  {
    "model_family": "DeepSeek Pro",
    "direct_phase": "phase1",
    "direct_arm_id": "arm-b-deepseek-pro",
    "router_arm_id": "router-deepseek-pro",
    "delta_success_count": -5.0,
    "delta_pass_rate_pct_points": -8.333333333333325,
    "router_vs_direct_cost_ratio": 25.088857611154236,
    "router_vs_direct_cost_per_clean_success_ratio": 27.80116654208707,
    "router_vs_direct_wall_clock_ratio": 0.527519172700475,
    "interpretation": "router-associated pass rate lower; router run materially more expensive"
  },
  {
    "model_family": "DeepSeek Pro",
    "direct_phase": "phase2",
    "direct_arm_id": "arm-deepseek-pro",
    "router_arm_id": "router-deepseek-pro",
    "delta_success_count": -2.0,
    "delta_pass_rate_pct_points": -3.3333333333333326,
    "router_vs_direct_cost_ratio": 29.45055355609751,
    "router_vs_direct_cost_per_clean_success_ratio": 30.246514463016066,
    "router_vs_direct_wall_clock_ratio": 0.5748808560235851,
    "interpretation": "pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share"
  },
  {
    "model_family": "DeepSeek Flash",
    "direct_phase": "phase1",
    "direct_arm_id": "arm-c-deepseek-flash",
    "router_arm_id": "router-deepseek-flash",
    "delta_success_count": 3.0,
    "delta_pass_rate_pct_points": 4.999999999999993,
    "router_vs_direct_cost_ratio": 51.49263883690439,
    "router_vs_direct_cost_per_clean_success_ratio": 46.343374953213946,
    "router_vs_direct_wall_clock_ratio": 1.13737418937584,
    "interpretation": "pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share"
  },
  {
    "model_family": "DeepSeek Flash",
    "direct_phase": "phase2",
    "direct_arm_id": "arm-deepseek-flash",
    "router_arm_id": "router-deepseek-flash",
    "delta_success_count": 5.0,
    "delta_pass_rate_pct_points": 8.333333333333325,
    "router_vs_direct_cost_ratio": 79.30942276967161,
    "router_vs_direct_cost_per_clean_success_ratio": 69.39574492346266,
    "router_vs_direct_wall_clock_ratio": 1.054154532066665,
    "interpretation": "router-associated pass rate higher; router run materially more expensive; router run had lower unclean spend share"
  },
  {
    "model_family": "Anthropic Opus",
    "direct_phase": "phase2",
    "direct_arm_id": "arm-anthropic-opus",
    "router_arm_id": "router-anthropic-opus",
    "delta_success_count": -6.0,
    "delta_pass_rate_pct_points": -9.999999999999998,
    "router_vs_direct_cost_ratio": 0.9418905402953844,
    "router_vs_direct_cost_per_clean_success_ratio": 1.038494698274366,
    "router_vs_direct_wall_clock_ratio": 1.1863172854028479,
    "interpretation": "router-associated pass rate lower; adjusted cost broadly similar"
  },
  {
    "model_family": "Anthropic Haiku",
    "direct_phase": "phase2",
    "direct_arm_id": "arm-anthropic-haiku",
    "router_arm_id": "router-anthropic-haiku-sanitized",
    "delta_success_count": -1.0,
    "delta_pass_rate_pct_points": -1.6666666666666663,
    "router_vs_direct_cost_ratio": 5.835616071495486,
    "router_vs_direct_cost_per_clean_success_ratio": 5.835616071495487,
    "router_vs_direct_wall_clock_ratio": 0.9676816465142392,
    "interpretation": "pass rate broadly similar; router run materially more expensive; router run had lower unclean spend share"
  }
];

const behaviorRows: BehaviorRow[] = [
  {
    "arm_id": "router-anthropic-fable-5",
    "provider": "anthropic",
    "backend_model": "claude-fable-5",
    "pass_rate": 0.65,
    "adjusted_cost_usd": 37.68696425,
    "cost_per_clean_success_usd": 1.018566601351,
    "unclean_spend_share": 0.4611728709350741,
    "exception_count": 12.0,
    "normal_failure_count": 11.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;exception-heavy;middle-token-success-pattern"
  },
  {
    "arm_id": "router-anthropic-haiku-sanitized",
    "provider": "anthropic",
    "backend_model": "claude-haiku-4-5-20251001",
    "pass_rate": 0.4166666666666667,
    "adjusted_cost_usd": 83.51122425,
    "cost_per_clean_success_usd": 3.34044897,
    "unclean_spend_share": 0.6564517433714906,
    "exception_count": 0.0,
    "normal_failure_count": 35.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "lower-pass-rate;high-unclean-spend;higher-token-success-pattern"
  },
  {
    "arm_id": "router-anthropic-opus",
    "provider": "anthropic",
    "backend_model": "claude-opus-4-7",
    "pass_rate": 0.65,
    "adjusted_cost_usd": 64.49228375,
    "cost_per_clean_success_usd": 1.653648301282,
    "unclean_spend_share": 0.4765881585019851,
    "exception_count": 7.0,
    "normal_failure_count": 14.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;higher-token-success-pattern"
  },
  {
    "arm_id": "router-anthropic-sonnet",
    "provider": "anthropic",
    "backend_model": "claude-sonnet-4-6",
    "pass_rate": 0.4666666666666667,
    "adjusted_cost_usd": 52.7917033,
    "cost_per_clean_success_usd": 1.885417975,
    "unclean_spend_share": 0.44164568185092073,
    "exception_count": 23.0,
    "normal_failure_count": 9.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "lower-pass-rate;exception-heavy;higher-token-success-pattern"
  },
  {
    "arm_id": "router-deepseek-flash",
    "provider": "deepseek",
    "backend_model": "deepseek-v4-flash",
    "pass_rate": 0.6666666666666666,
    "adjusted_cost_usd": 56.7953838632,
    "cost_per_clean_success_usd": 1.41988459658,
    "unclean_spend_share": 0.24446597449966964,
    "exception_count": 8.0,
    "normal_failure_count": 12.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;higher-token-success-pattern"
  },
  {
    "arm_id": "router-deepseek-pro",
    "provider": "deepseek",
    "backend_model": "deepseek-v4-pro",
    "pass_rate": 0.6166666666666667,
    "adjusted_cost_usd": 50.439011911,
    "cost_per_clean_success_usd": 1.363216538135,
    "unclean_spend_share": 0.24364218182315223,
    "exception_count": 7.0,
    "normal_failure_count": 16.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;higher-token-success-pattern"
  },
  {
    "arm_id": "router-gemini-3.1-pro",
    "provider": "google-gemini",
    "backend_model": "gemini-3.1-pro-preview",
    "pass_rate": 0.6333333333333333,
    "adjusted_cost_usd": 46.469402372843,
    "cost_per_clean_success_usd": 1.290816732579,
    "unclean_spend_share": 0.3112025684516729,
    "exception_count": 16.0,
    "normal_failure_count": 8.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;exception-heavy;middle-token-success-pattern"
  },
  {
    "arm_id": "router-gemini-flash",
    "provider": "google-gemini",
    "backend_model": "gemini-3.5-flash",
    "pass_rate": 0.21666666666666667,
    "adjusted_cost_usd": 43.534953854953,
    "cost_per_clean_success_usd": 4.837217094995,
    "unclean_spend_share": 0.6080827705285639,
    "exception_count": 41.0,
    "normal_failure_count": 8.0,
    "suspect_noop_count": 2.0,
    "behavior_tags": "lower-pass-rate;expensive-clean-success;exception-heavy;high-unclean-spend;suspect-noop-present;middle-token-success-pattern"
  },
  {
    "arm_id": "router-glm-5.1",
    "provider": "zai-glm",
    "backend_model": "glm-5.1",
    "pass_rate": 0.6,
    "adjusted_cost_usd": 20.297031,
    "cost_per_clean_success_usd": 0.579915171429,
    "unclean_spend_share": 0.20176354857023174,
    "exception_count": 16.0,
    "normal_failure_count": 9.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;exception-heavy;lower-token-success-pattern"
  },
  {
    "arm_id": "router-glm-5.2",
    "provider": "zai-glm",
    "backend_model": "glm-5.2",
    "pass_rate": 0.6333333333333333,
    "adjusted_cost_usd": 25.3166398,
    "cost_per_clean_success_usd": 0.723332565714,
    "unclean_spend_share": 0.3250099485951528,
    "exception_count": 19.0,
    "normal_failure_count": 6.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;exception-heavy;lower-token-success-pattern"
  },
  {
    "arm_id": "router-gpt-5.4",
    "provider": "openai",
    "backend_model": "gpt-5.4",
    "pass_rate": 0.65,
    "adjusted_cost_usd": 183.646689146806,
    "cost_per_clean_success_usd": 4.832807609126,
    "unclean_spend_share": 0.21565043906207979,
    "exception_count": 7.0,
    "normal_failure_count": 15.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;expensive-clean-success;high-total-cost;middle-token-success-pattern"
  },
  {
    "arm_id": "router-gpt-5.5",
    "provider": "openai",
    "backend_model": "gpt-5.5",
    "pass_rate": 0.7333333333333333,
    "adjusted_cost_usd": 183.958832348525,
    "cost_per_clean_success_usd": 4.379972198774,
    "unclean_spend_share": 0.2605678223577251,
    "exception_count": 4.0,
    "normal_failure_count": 12.0,
    "suspect_noop_count": 2.0,
    "behavior_tags": "high-pass-rate;expensive-clean-success;high-total-cost;suspect-noop-present;middle-token-success-pattern"
  },
  {
    "arm_id": "router-grok-build-0.1",
    "provider": "xai",
    "backend_model": "grok-build-0.1",
    "pass_rate": 0.6,
    "adjusted_cost_usd": 53.153814003353,
    "cost_per_clean_success_usd": 1.476494833426,
    "unclean_spend_share": 0.5612899951350809,
    "exception_count": 13.0,
    "normal_failure_count": 11.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "mid-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern"
  },
  {
    "arm_id": "router-kimi-k2.6",
    "provider": "moonshot-kimi",
    "backend_model": "kimi-k2.6",
    "pass_rate": 0.5,
    "adjusted_cost_usd": 35.131541559739,
    "cost_per_clean_success_usd": 1.171051385325,
    "unclean_spend_share": 0.6282090275546383,
    "exception_count": 14.0,
    "normal_failure_count": 16.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "lower-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern"
  },
  {
    "arm_id": "router-qwen-3.7-plus",
    "provider": "dashscope-qwen",
    "backend_model": "qwen3.7-plus",
    "pass_rate": 0.55,
    "adjusted_cost_usd": 34.944370078779,
    "cost_per_clean_success_usd": 1.092011564962,
    "unclean_spend_share": 0.548345127858391,
    "exception_count": 19.0,
    "normal_failure_count": 9.0,
    "suspect_noop_count": 0.0,
    "behavior_tags": "lower-pass-rate;cost-efficient-clean-success;exception-heavy;high-unclean-spend;lower-token-success-pattern"
  }
];

function reviewedDecimal(
  value: string | null,
): number | null {
  if (value === null) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new Error(
      "reviewed Phase 3 cost is not finite",
    );
  }
  return parsed;
}

function historicalReviewedCostLabel(
  arm: CurrentReviewedPhase3Arm,
): string {
  return arm.historicalReviewedCostBasis
    === "qualified_retained_rate_estimate"
    ? "Qualified retained-rate reconstruction"
    : "Adjusted known cost";
}

function selectedCostLabel(
  arm: CurrentReviewedPhase3Arm,
): string {
  if (arm.selectedCostBasis === "provider_billed") {
    return "Provider-billed arm total";
  }
  if (
    arm.selectedCostBasis
      === "qualified_retained_rate_estimate"
  ) {
    return "Qualified retained-rate estimate";
  }
  return "Adjusted known cost";
}

export function getCurrentReviewedPhase3Rows(
  scope: CurrentReviewedPhase3Scope,
): CrossPhaseRow[] {
  return scope.arms.map((arm) => ({
    phase: "phase3",
    arm_id: arm.armId,
    backend_model: arm.backendModel,
    provider: arm.provider,
    routing_path: arm.routingPath,
    success_count: arm.successCount,
    clean_success_count: arm.cleanSuccessCount,
    trial_count: arm.trialCount,
    pass_rate: arm.passRate,

    // Historical compatibility fields remain benchmark-side
    // evidence. They are never overwritten with provider totals.
    recorded_cost_usd: reviewedDecimal(
      arm.historicalHarnessRecordedCostUsd,
    ) as number,
    adjusted_cost_usd: reviewedDecimal(
      arm.historicalReviewedCostUsd,
    ),
    known_accounting_gap_usd: reviewedDecimal(
      arm.accountingGapUsd,
    ) as number,
    cost_per_clean_success_usd: reviewedDecimal(
      arm.adjustedCostPerCleanSuccessUsd,
    ),
    failure_incomplete_spend_share:
      arm.failureOrIncompleteSpendShare,
    unclean_spend_share:
      arm.nonproductiveOrUncleanSpendShare,
    median_wall_clock_seconds:
      arm.medianWallClockSeconds,
    cost_confidence: arm.costConfidence,
    reviewed_cost_basis:
      arm.historicalReviewedCostBasis,
    reviewed_cost_label:
      historicalReviewedCostLabel(arm),
    pricing_provenance_status:
      arm.pricingProvenanceStatus,
    arm_run_allocation_confidence:
      arm.armRunAllocationConfidence,
    trial_allocation_status:
      arm.trialAllocationStatus,
    billing_reconciliation_status:
      arm.billingReconciliationStatus,

    // Decision-facing comparison fields use the current v2
    // selected-cost contract.
    comparison_cost_usd: reviewedDecimal(
      arm.selectedCostUsd,
    ),
    comparison_cost_per_attempt_usd:
      reviewedDecimal(
        arm.selectedCostPerAttemptUsd,
      ),
    comparison_cost_per_clean_success_usd:
      reviewedDecimal(
        arm.selectedCostPerCleanSuccessUsd,
      ),
    comparison_cost_basis: arm.selectedCostBasis,
    comparison_cost_label: selectedCostLabel(arm),
    comparison_cost_confidence:
      arm.selectedCostConfidence,
    comparison_cost_layer:
      "current_selected_phase3",

    // Historical outcome/cost facts stay explicitly historical.
    historical_reviewed_cost_usd:
      reviewedDecimal(
        arm.historicalReviewedCostUsd,
      ),
    historical_reviewed_cost_basis:
      arm.historicalReviewedCostBasis,
    historical_reviewed_cost_label:
      historicalReviewedCostLabel(arm),
    historical_unclean_spend_share:
      arm.nonproductiveOrUncleanSpendShare,

    selected_trial_allocation_status:
      arm.selectedTrialCostAllocationStatus,
    selected_outcome_allocation_status:
      arm.selectedOutcomeCostAllocationStatus,

    provider_billed_cost_usd:
      reviewedDecimal(arm.providerBilledCostUsd),
    provider_billing_reconciliation_status:
      arm.providerBillingReconciliationStatus,
    provider_selected_run_label:
      arm.providerSelectedRunLabel,
  }));
}

function historicalBaselineRow(
  row: HistoricalCrossPhaseRow,
): CrossPhaseRow {
  const comparisonCost = row.adjusted_cost_usd;

  return {
    ...row,
    reviewed_cost_basis: "adjusted_known_cost",
    reviewed_cost_label: "Adjusted known cost",

    comparison_cost_usd: comparisonCost,
    comparison_cost_per_attempt_usd:
      comparisonCost === null
        ? null
        : comparisonCost / row.trial_count,
    comparison_cost_per_clean_success_usd:
      row.cost_per_clean_success_usd,
    comparison_cost_basis: "adjusted_known_cost",
    comparison_cost_label: "Adjusted known cost",
    comparison_cost_confidence:
      row.cost_confidence,
    comparison_cost_layer:
      "frozen_historical_baseline",

    // Phase 1/2 comparison costs are already the frozen
    // historical baselines. The separate historical Phase 3
    // bridge is therefore not applicable to these rows.
    historical_reviewed_cost_usd: null,
    historical_reviewed_cost_basis: null,
    historical_reviewed_cost_label: null,
    historical_unclean_spend_share:
      row.unclean_spend_share,

    selected_trial_allocation_status: null,
    selected_outcome_allocation_status: null,

    provider_billed_cost_usd: null,
    provider_billing_reconciliation_status: null,
    provider_selected_run_label: null,
  };
}

export function getCrossPhaseRows(
  phase3Scope: CurrentReviewedPhase3Scope,
): CrossPhaseRow[] {
  const historicalBaselines = crossPhaseRows
    .filter((row) => row.phase !== "phase3")
    .map(historicalBaselineRow);

  return [
    ...historicalBaselines,
    ...getCurrentReviewedPhase3Rows(phase3Scope),
  ];
}

export function getRouterComparisonRows():
  RouterComparisonRow[] {
  return routerComparisonRows;
}

export function getBehaviorRows(): BehaviorRow[] {
  return behaviorRows;
}

export function getPhaseSummaries(
  rows: CrossPhaseRow[],
  phase3Scope?: CurrentReviewedPhase3Scope,
): PhaseSummary[] {
  const byPhase =
    new Map<string, CrossPhaseRow[]>();

  for (const row of rows) {
    const phaseRows = byPhase.get(row.phase) ?? [];
    phaseRows.push(row);
    byPhase.set(row.phase, phaseRows);
  }

  return Array.from(byPhase.entries())
    .map(([phase, phaseRows]) => {
      const trialCount = phaseRows.reduce(
        (sum, row) => sum + row.trial_count,
        0,
      );
      const successCount = phaseRows.reduce(
        (sum, row) => sum + row.success_count,
        0,
      );
      const cleanSuccessCount = phaseRows.reduce(
        (sum, row) =>
          sum + row.clean_success_count,
        0,
      );

      const completeComparisonCosts =
        phaseRows.every(
          (row) =>
            row.comparison_cost_usd !== null,
        );
      const rowComparisonCost =
        completeComparisonCosts
          ? phaseRows.reduce(
              (sum, row) =>
                sum
                + row.comparison_cost_usd!,
              0,
            )
          : null;

      const isSelectedPhase3 =
        phase === "phase3"
        && phase3Scope !== undefined;

      const comparisonCost =
        isSelectedPhase3
          ? reviewedDecimal(
              phase3Scope.selectedCostEvidence
                .selectedCostUsd,
            )
          : rowComparisonCost;

      const comparisonCostPerCleanSuccess =
        comparisonCost !== null
        && cleanSuccessCount > 0
          ? comparisonCost / cleanSuccessCount
          : null;

      const historicalReviewedCost =
        isSelectedPhase3
          ? reviewedDecimal(
              phase3Scope.selectedCostEvidence
                .historicalReviewedArmSumCostUsd,
            )
          : null;

      let historicalUncleanSpendShare:
        number | null;

      if (isSelectedPhase3) {
        // This remains the frozen historical outcome-cost
        // share. It is never multiplied by current selected
        // provider-billed totals.
        historicalUncleanSpendShare =
          phase3Scope.historicalCostEvidence
            .nonproductiveOrUncleanSpendShare;
      } else {
        const completeHistoricalAllocation =
          phaseRows.every(
            (row) =>
              row.adjusted_cost_usd !== null
              && row.unclean_spend_share
                !== null,
          );

        if (
          !completeHistoricalAllocation
          || comparisonCost === null
          || comparisonCost <= 0
        ) {
          historicalUncleanSpendShare = null;
        } else {
          const historicalUncleanSpend =
            phaseRows.reduce(
              (sum, row) =>
                sum
                + row.adjusted_cost_usd!
                * row.unclean_spend_share!,
              0,
            );

          historicalUncleanSpendShare =
            historicalUncleanSpend
            / comparisonCost;
        }
      }

      return {
        phase,
        arm_count: phaseRows.length,
        trial_count: trialCount,
        success_count: successCount,
        clean_success_count: cleanSuccessCount,
        pass_rate:
          trialCount > 0
            ? successCount / trialCount
            : 0,

        comparison_cost_usd: comparisonCost,
        comparison_cost_basis:
          isSelectedPhase3
            ? phase3Scope.selectedCostEvidence
                .selectedCostBasis
            : "adjusted_known_cost",
        comparison_cost_label:
          isSelectedPhase3
            ? "Current selected cost"
            : "Adjusted known cost",
        comparison_cost_per_clean_success_usd:
          comparisonCostPerCleanSuccess,

        historical_reviewed_cost_usd:
          historicalReviewedCost,
        historical_unclean_spend_share:
          historicalUncleanSpendShare,
      };
    })
    .sort(
      (left, right) =>
        left.phase.localeCompare(right.phase),
    );
}
