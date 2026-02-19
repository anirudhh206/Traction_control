import type { Metadata } from "next";
// import { Inter } from "next/font/google";
import "./globals.css";
import WalletProvider from "@/components/layout/WalletProvider";
import Navbar from "@/components/layout/Navbar";

// const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RepEscrow - Reputation-Weighted Escrow on Solana",
  description:
    "Your FairScore determines your fees. Higher reputation = lower costs. Built on Solana.",
  openGraph: {
    title: "RepEscrow - Reputation-Weighted Escrow on Solana",
    description:
      "Your FairScore determines your fees. Higher reputation = lower costs. Built on Solana.",
    url: "https://repescrow.xyz",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body> {/* ← Remove {inter.className} */}
        <WalletProvider>
          <Navbar />
          <main className="min-h-screen">{children}</main>
        </WalletProvider>
      </body>
    </html>
  );

}
