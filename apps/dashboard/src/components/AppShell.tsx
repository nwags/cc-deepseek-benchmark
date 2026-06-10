import Link from "next/link";

const navItems = [
  { href: "/", label: "Overview" },
  { href: "/runs", label: "Runs" },
  { href: "/arms", label: "Arms" },
  { href: "/tasks", label: "Tasks" },
  { href: "/artifacts", label: "Artifacts" },
  { href: "/runners", label: "Runners" },
  { href: "/scaffold", label: "Arm Scaffold" }
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
          <div className="brand-mark">P3</div>
          <div>
            <div className="brand-title">Router Bench</div>
            <div className="brand-subtitle">Phase 3</div>
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
