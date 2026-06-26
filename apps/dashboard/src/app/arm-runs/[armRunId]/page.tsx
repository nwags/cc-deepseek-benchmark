import { notFound, redirect } from "next/navigation";
import { getRunLabelForArmRunId } from "../../../lib/dashboard-data";

export default async function ArmRunDetailRedirectPage({
  params
}: {
  params: Promise<{ armRunId: string }>;
}) {
  const { armRunId } = await params;
  const runLabel = await getRunLabelForArmRunId(armRunId);

  if (!runLabel) {
    notFound();
  }

  redirect(`/runs/${encodeURIComponent(runLabel)}`);
}
