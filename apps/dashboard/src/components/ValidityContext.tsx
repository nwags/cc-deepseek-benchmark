import type { InvalidArmRunRow } from "../lib/dashboard-data";
import { sanitizeEvidenceText } from "../lib/safe-display";

function metadataString(row: InvalidArmRunRow | null | undefined, key: string): string | null {
  const value = row?.raw_metadata?.[key];
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  return text || null;
}

export function invalidCategory(row: InvalidArmRunRow | null | undefined): string | null {
  return metadataString(row, "category");
}

export function validityLabel(row: InvalidArmRunRow | null | undefined): string {
  if (!row) return "valid";

  const metadataLabel =
    metadataString(row, "validity") ?? metadataString(row, "status") ?? metadataString(row, "label");

  if (metadataLabel === "quarantined" || metadataLabel === "quarantine") {
    return "quarantined";
  }

  return "invalid";
}

export function ValidityBadge({ row }: { row: InvalidArmRunRow | null | undefined }) {
  const label = validityLabel(row);
  const category = invalidCategory(row);

  return (
    <span className={row ? "quality-badge quality-badge-warn" : "quality-badge"}>
      {sanitizeEvidenceText(row && category ? `${label}: ${category}` : label)}
    </span>
  );
}

export function InvalidReason({
  row,
  includeProvider = true
}: {
  row: InvalidArmRunRow | null | undefined;
  includeProvider?: boolean;
}) {
  if (!row) return null;

  return (
    <span>
      {sanitizeEvidenceText(row.reason)}
      {includeProvider && row.provider_run_id ? (
        <>
          {" "}
          <span className="muted">provider/workflow id </span>
          <span className="mono">{sanitizeEvidenceText(row.provider_run_id)}</span>
        </>
      ) : null}
    </span>
  );
}
