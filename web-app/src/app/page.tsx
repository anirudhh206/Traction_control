"use client";

import Link from "next/link";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import {
  Shield,
  TrendingDown,
  Zap,
  Lock,
  ArrowRight,
  Star,
} from "lucide-react";
import { FAIR_SCORE_TIERS } from "@/lib/constants";

export default function LandingPage() {
  const { connected } = useWallet();

  return (
    <div className="relative">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-sol-purple/10 via-transparent to-transparent" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-32">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-sol-green/10 border border-sol-green/20 rounded-full text-sol-green text-sm mb-8">
              <Zap className="w-4 h-4" />
              Built on Solana &bull; Powered by FairScale
            </div>

            <h1 className="text-5xl sm:text-6xl font-bold text-white leading-tight mb-6">
              Your Reputation
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-sol-green to-sol-purple">
                Determines Your Fees
              </span>
            </h1>

            <p className="text-xl text-gray-400 mb-10 max-w-2xl mx-auto">
              RepEscrow is reputation-weighted escrow on Solana. Your FairScore
              drives your fees — from 0.5% for top vendors down from Upwork's
              20%.
            </p>

            <div className="flex items-center justify-center gap-4">
              {connected ? (
                <Link
                  href="/dashboard"
                  className="inline-flex items-center gap-2 px-8 py-3 bg-sol-green text-gray-900 font-semibold rounded-lg hover:bg-sol-green/90 transition-colors"
                >
                  Go to Dashboard
                  <ArrowRight className="w-5 h-5" />
                </Link>
              ) : (
                <WalletMultiButton className="!bg-sol-green !text-gray-900 !font-semibold !rounded-lg !h-12 !px-8 hover:!bg-sol-green/90" />
              )}
              <Link
                href="/vendors"
                className="inline-flex items-center gap-2 px-8 py-3 border border-gray-700 text-white font-medium rounded-lg hover:bg-gray-800 transition-colors"
              >
                Browse Vendors
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Fee Comparison */}
      <section className="py-20 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-white mb-4">
            Stop Overpaying for Trust
          </h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            Traditional platforms charge everyone the same high fee. RepEscrow
            rewards your reputation with lower costs.
          </p>

          <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
            <div className="p-6 rounded-xl bg-red-950/30 border border-red-900/30">
              <div className="text-red-400 text-sm font-medium mb-2">
                Upwork
              </div>
              <div className="text-4xl font-bold text-red-400 mb-1">20%</div>
              <div className="text-gray-500 text-sm">
                Same fee for everyone
              </div>
            </div>

            <div className="p-6 rounded-xl bg-yellow-950/30 border border-yellow-900/30">
              <div className="text-yellow-400 text-sm font-medium mb-2">
                Traditional Escrow
              </div>
              <div className="text-4xl font-bold text-yellow-400 mb-1">
                2-3%
              </div>
              <div className="text-gray-500 text-sm">
                Flat fee, no reputation benefit
              </div>
            </div>

            <div className="p-6 rounded-xl bg-green-950/30 border border-green-900/30">
              <div className="text-sol-green text-sm font-medium mb-2">
                RepEscrow
              </div>
              <div className="text-4xl font-bold text-sol-green mb-1">
                0.5%
              </div>
              <div className="text-gray-500 text-sm">
                Top FairScore tier
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FairScore Tiers */}
      <section className="py-20 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">
              FairScore Tier System
            </h2>
            <p className="text-gray-400 max-w-2xl mx-auto">
              Your on-chain reputation from FairScale determines your escrow
              fees and payment hold periods.
            </p>
          </div>

          <div className="max-w-3xl mx-auto space-y-3">
            {FAIR_SCORE_TIERS.map((tier) => (
              <div
                key={tier.label}
                className="flex items-center justify-between p-4 rounded-lg bg-gray-900/50 border border-gray-800"
              >
                <div className="flex items-center gap-4">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: tier.color }}
                  />
                  <div>
                    <span className="text-white font-medium">{tier.label}</span>
                    <span className="text-gray-500 text-sm ml-2">
                      {tier.min}-{tier.max}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-8">
                  <span className="text-white font-mono">{tier.fee} fee</span>
                  <span className="text-gray-400 text-sm w-20 text-right">
                    {tier.hold}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6">
              <TrendingDown className="w-10 h-10 text-sol-green mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Lower Fees
              </h3>
              <p className="text-gray-400">
                Build your reputation and watch your fees drop. Top vendors pay
                just 0.5% — 40x less than Upwork.
              </p>
            </div>

            <div className="p-6">
              <Lock className="w-10 h-10 text-sol-purple mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                Secure Escrow
              </h3>
              <p className="text-gray-400">
                Funds held in on-chain escrow with milestone payments and
                built-in dispute resolution.
              </p>
            </div>

            <div className="p-6">
              <Star className="w-10 h-10 text-yellow-400 mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">
                On-Chain Reputation
              </h3>
              <p className="text-gray-400">
                Your FairScore is portable across Web3. Good reputation
                follows you everywhere.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to earn lower fees?
          </h2>
          <p className="text-gray-400 mb-8 max-w-xl mx-auto">
            Connect your Solana wallet and start building your reputation today.
          </p>

          {!connected && (
            <WalletMultiButton className="!bg-sol-green !text-gray-900 !font-semibold !rounded-lg !h-12 !px-8" />
          )}
        </div>
      </section>
    </div>
  );
}
