import Link from "next/link";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/architecture", label: "Architecture" },
  { href: "/data-model", label: "Data Model" },
  { href: "/glossary", label: "Glossary" },
  { href: "/trial-quality", label: "Trial Quality" },
  { href: "/cross-phase", label: "Cross-phase" },
  { href: "/eval-suites", label: "Eval Suites" },
  { href: "/evals", label: "Evals" },
  { href: "/runs", label: "Runs" },
  { href: "/runs/live", label: "Live Runs" },
  { href: "/arms", label: "Arms" },
  { href: "/artifacts", label: "Artifacts" },
  { href: "/provider-evidence", label: "Provider Evidence" },
  { href: "/comprehensive-review", label: "Evidence Review" },
  { href: "/planner", label: "Planner" },
  { href: "/cost-coverage", label: "Cost Coverage" }
];

export function AppShell({
  title,
  eyebrow = "Claude Code Backend Benchmark",
  description,
  children
}: {
  title: string;
  eyebrow?: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">CAB</div>
          <div>
            <div className="brand-title">Benchmark Dashboard</div>
            <div className="brand-subtitle">Coding agents</div>
          </div>
        </div>

        <nav className="nav-list" aria-label="Dashboard navigation">
          {navItems.map((item) => (
            <Link href={item.href} key={item.href} className="nav-link">
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>

      <section className="content-shell">
        <header className="hero compact-hero">
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
          {description ? <p className="hero-copy">{description}</p> : null}
        </header>

        {children}
      </section>
    </main>
  );
}
