import { notFound, redirect } from "next/navigation";
import { getRunLabelForArmRunId } from "../../../lib/dashboard-data";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export default async function ArmRunDetailRedirectPage({
  params
}: {
  params: Promise<{ armRunId: string }>;
}) {
  const { armRunId } = await params;
  const decoded = decodeURIComponent(armRunId);

  if (!UUID_RE.test(decoded)) {
    if (decoded.includes("/")) {
      redirect(`/runs/${encodeURIComponent(decoded)}`);
    }
    notFound();
  }

  const runLabel = await getRunLabelForArmRunId(decoded);

  if (!runLabel) {
    notFound();
  }

  redirect(`/runs/${encodeURIComponent(runLabel)}`);
}
