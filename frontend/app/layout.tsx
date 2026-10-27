import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "ProgramPulse AI | Delivery Assurance",
  description: "Independent delivery intelligence. Compare reported project health with what the evidence supports.",
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
