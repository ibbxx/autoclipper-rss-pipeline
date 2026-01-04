import "./globals.css";
import type { Metadata } from "next";
import { QueryProvider } from "@/components/QueryProvider";

export const metadata: Metadata = {
  title: "Auto Clipper Dashboard",
  description: "Monitor YouTube -> Auto clips -> Approve -> Upload TikTok",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
