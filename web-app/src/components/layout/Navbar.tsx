"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import { useWallet } from "@solana/wallet-adapter-react";
import { Shield } from "lucide-react";

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/dashboard", label: "Dashboard" },
  { href: "/vendors", label: "Vendors" },
];

export default function Navbar() {
  const pathname = usePathname();
  const { connected } = useWallet();

  return (
    <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <Shield className="w-8 h-8 text-sol-green" />
            <span className="text-xl font-bold text-white">
              Rep<span className="text-sol-green">Escrow</span>
            </span>
          </Link>

          {/* Nav Links */}
          <div className="hidden md:flex items-center gap-6">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm font-medium transition-colors ${
                  pathname === link.href
                    ? "text-sol-green"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {link.label}
              </Link>
            ))}

            {connected && (
              <Link
                href="/settings"
                className={`text-sm font-medium transition-colors ${
                  pathname === "/settings"
                    ? "text-sol-green"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                Settings
              </Link>
            )}
          </div>

          {/* Wallet Button */}
          <WalletMultiButton className="!bg-sol-purple hover:!bg-sol-purple/80 !rounded-lg !h-10 !text-sm" />
        </div>
      </div>
    </nav>
  );
}
