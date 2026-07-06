export type ArtifactHrefFilters = {
  suite_id?: string | null;
  arm_id?: string | null;
  run_label?: string | null;
  task_id?: string | null;
  quality_flag?: string | null;
  exception_type?: string | null;
  artifact_type?: string | null;
  artifact_kind?: string | null;
  q?: string | null;
};

export function buildArtifactHref(filters: ArtifactHrefFilters = {}) {
  const params = new URLSearchParams();
  const normalizedFilters = {
    ...filters,
    artifact_type: filters.artifact_type ?? filters.artifact_kind
  };

  for (const key of [
    "suite_id",
    "arm_id",
    "run_label",
    "task_id",
    "quality_flag",
    "exception_type",
    "artifact_type",
    "q"
  ] as const) {
    const value = normalizedFilters[key];
    if (value) {
      params.set(key, value);
    }
  }

  const query = params.toString();
  return query ? `/artifacts?${query}` : "/artifacts";
}
