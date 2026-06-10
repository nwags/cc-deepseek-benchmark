export function PlaceholderPanel({
  title,
  children
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{title}</h2>
        <p>Read-only scaffold placeholder.</p>
      </div>
      <div className="placeholder-body">{children}</div>
    </section>
  );
}
