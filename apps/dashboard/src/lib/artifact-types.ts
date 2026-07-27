export type ArtifactTypeDefinition = {
  artifactType: string;
  shortDefinition: string;
  definition: string;
};

export const artifactTypeDefinitions = [
  {
    artifactType: "agent_transcript",
    shortDefinition: "Human-readable agent transcript.",
    definition: "Human-readable Claude Code / agent transcript for the trial. This is usually the best first stop for seeing what the agent appeared to do."
  },
  {
    artifactType: "config",
    shortDefinition: "Captured run or trial configuration.",
    definition: "Captured run or trial configuration. Use it to confirm arm, model route, task, timeout, and harness settings."
  },
  {
    artifactType: "log",
    shortDefinition: "Harbor or runner trial log.",
    definition: "Harbor/runner trial log. Use it for setup output, command execution, timing, infrastructure failures, and other harness-level context."
  },
  {
    artifactType: "result",
    shortDefinition: "Structured Harbor result JSON.",
    definition: "Structured Harbor result JSON. It usually contains reward, exception metadata, timing, token/cost fields, and nested agent/verifier results."
  },
  {
    artifactType: "trajectory",
    shortDefinition: "Structured agent behavior record.",
    definition: "Structured agent trajectory. Use it for deeper review of messages, actions, tool calls, and step-level behavior."
  },
  {
    artifactType: "verifier_ctrf",
    shortDefinition: "Structured verifier/test results.",
    definition: "Verifier output in CTRF JSON format. Use it for structured test-case pass/fail details."
  },
  {
    artifactType: "verifier_reward",
    shortDefinition: "Minimal scored reward output.",
    definition: "Minimal verifier reward file, usually 0 or 1. Use it to confirm the scored benchmark outcome."
  },
  {
    artifactType: "verifier_stdout",
    shortDefinition: "Raw verifier/test stdout.",
    definition: "Raw verifier/test stdout. This is usually the best first stop for understanding why a trial failed."
  },
  {
    artifactType: "exception",
    shortDefinition: "Harness/runtime exception evidence.",
    definition: "Exception traceback or harness/runtime error captured when Harbor or agent execution raised an exception."
  }
] as const satisfies readonly ArtifactTypeDefinition[];

export function getArtifactTypeDefinition(artifactType: string | null | undefined) {
  if (!artifactType) return undefined;
  return artifactTypeDefinitions.find((item) => item.artifactType === artifactType);
}

export function artifactTypeTitle(artifactType: string | null | undefined) {
  const label = artifactType || "unknown artifact";
  const definition = getArtifactTypeDefinition(artifactType);

  if (!definition) {
    return `${label}: artifact type metadata imported from the benchmark run. No dashboard glossary entry exists yet.`;
  }

  return `${definition.artifactType}: ${definition.definition}`;
}
