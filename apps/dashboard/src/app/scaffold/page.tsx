import { redirect } from "next/navigation";

export default function ScaffoldPage() {
  redirect("/planner?mode=arm");
}
