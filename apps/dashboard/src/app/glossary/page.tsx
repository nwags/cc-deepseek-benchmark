import Link from "next/link";

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
          <p>Use this page as the shared language layer for interpreting benchmark results.</p>
        </div>
        <div className="glossary-list">
          {glossaryEntries.map((entry) => (
            <article className="glossary-entry" id={entry.slug} key={entry.slug}>
              <h3>{entry.term}</h3>
              <p>{entry.definition}</p>
              {"links" in entry && entry.links.length > 0 ? (
                <nav className="glossary-related-links" aria-label={`Related pages for ${entry.term}`}>
                  {entry.links.map((link) => (
                    <Link href={link.href} key={link.href}>{link.label} →</Link>
                  ))}
                </nav>
              ) : null}
            </article>
          ))}
        </div>
      </section>
    </AppShell>
  );
}
