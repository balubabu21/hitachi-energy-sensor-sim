import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Grid Sensor Simulator",
  description: "Mock sensor data for Hitachi Energy product families (unofficial simulation).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
