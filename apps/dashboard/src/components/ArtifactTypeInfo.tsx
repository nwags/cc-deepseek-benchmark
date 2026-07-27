import { artifactTypeDefinitions, artifactTypeTitle } from "../lib/artifact-types";

export function ArtifactTypeLabel({
  artifactType
}: {
  artifactType: string | null | undefined;
}) {
  const label = artifactType || "unknown";
  return (
    <span className="term-label mono" title={artifactTypeTitle(artifactType)}>
      {label}
    </span>
  );
}

export function ArtifactTypesReference() {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>Artifact types</h2>
          <p>How to read the common evidence files attached to a benchmark trial.</p>
        </div>
      </div>
      <div className="concept-grid">
        {artifactTypeDefinitions.map((item) => (
          <article key={item.artifactType}>
            <h3><span className="mono">{item.artifactType}</span></h3>
            <p><strong>{item.shortDefinition}</strong> {item.definition}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
