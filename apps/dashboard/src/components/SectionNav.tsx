export type SectionNavItem = Readonly<{
  href: `#${string}`;
  label: string;
}>;

export function SectionNav({
  items,
  ariaLabel = "On this page",
}: {
  items: readonly SectionNavItem[];
  ariaLabel?: string;
}) {
  if (items.length === 0) return null;

  return (
    <nav className="section-nav" aria-label={ariaLabel}>
      <strong className="section-nav-label">On this page</strong>
      <div className="section-nav-links">
        {items.map((item) => (
          <a key={item.href} href={item.href}>
            {item.label}
          </a>
        ))}
      </div>
    </nav>
  );
}
