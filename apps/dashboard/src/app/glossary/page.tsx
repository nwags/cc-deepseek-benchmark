import { AppShell } from "../../components/AppShell";
import { glossaryEntries } from "../../lib/glossary";

export const dynamic = "force-dynamic";

export default function GlossaryPage() {
  return (
    <AppShell
      title="Glossary"
      description="Definitions for dashboard terms, benchmark concepts, ingestion fields, and cost/artifact caveats."
    >
      <section className="panel">
        <div className="panel-heading">
          <h2>Dashboard terms</h2>
          <p>Use this page as the shared language layer for interpreting Phase 3 results.</p>
        </div>
        <div className="glossary-list">
          {glossaryEntries.map((entry) => (
            <article className="glossary-entry" id={entry.slug} key={entry.slug}>
              <h3>{entry.term}</h3>
              <p>{entry.definition}</p>
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
