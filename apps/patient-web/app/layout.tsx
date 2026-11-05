import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CareConnect | Care that fits your life",
  description: "Find clinicians, explore virtual appointments, and manage care through CareConnect.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
