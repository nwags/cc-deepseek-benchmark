import { fileURLToPath } from "node:url";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const failureTaxonomyRuntimeFiles = [
  "../../configs/dashboard/failure_taxonomy_v1.json",
  "../../results/manual_verification/failure_taxonomy_20260813/failure_taxonomy_manifest.json",
  "../../results/manual_verification/failure_taxonomy_20260813/trial_failure_taxonomy.jsonl",
  "../../results/manual_verification/failure_taxonomy_20260813/taxonomy_counts.json",
  "../../results/manual_verification/failure_taxonomy_20260813/review_queue.csv",
  "../../results/manual_verification/failure_taxonomy_20260813/README.md",
  "../../results/manual_verification/comprehensive_review_20260731/review_manifest.json",
  "../../results/manual_verification/comprehensive_review_20260731/trial_review.csv",
  "../../results/manual_verification/comprehensive_review_20260731/trial_evidence.jsonl",
  "../../scripts/lib/failure_taxonomy_classifier.py",
  "../../scripts/generate_failure_taxonomy_snapshot.py",
];

const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ["192.168.0.53"],
  // Permit Next's server tracer to include the exact repository-level runtime inputs below.
  outputFileTracingRoot: repositoryRoot,
  outputFileTracingIncludes: {
    "/trial-quality": failureTaxonomyRuntimeFiles,
    "/trials/**": failureTaxonomyRuntimeFiles,
  },
};

export default nextConfig;
