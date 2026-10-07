import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Coders Alley · Atelier",
  description: "Live 3D view of the agent team at work.",
};

export default function OfficeLayout({ children }: { children: React.ReactNode }) {
  return children;
}
