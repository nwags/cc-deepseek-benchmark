import { redirect } from "next/navigation";

export default function TasksPage() {
  redirect("/evals?scope=all-imported");
}
