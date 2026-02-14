"use client";

import { useEffect, useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import Link from "next/link";
import {
  Shield,
  TrendingUp,
  Clock,
  DollarSign,
  ArrowUpRight,
  Plus,
} from "lucide-react";
import { getTierForScore, FAIR_SCORE_TIERS } from "@/lib/constants";
import { formatFairScore, lamportsToSol } from "@/lib/program";

interface ProfileData {
  fairScore: number;
  buyerTxCount: number;
  vendorTxCount: number;
  totalVolume: number;
  stakedAmount: number;
  disputeCount: number;
  disputesWon: number;
}

export default function DashboardPage() {
  const { publicKey, connected } = useWallet();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!connected || !publicKey) {
      setLoading(false);
      return;
    }

    // TODO: Fetch profile from on-chain program
    // For now, show placeholder data
    setProfile({
      fairScore: 250, // 2.50 - starting score
      buyerTxCount: 0,
      vendorTxCount: 0,
      totalVolume: 0,
      stakedAmount: 0,
      disputeCount: 0,
      disputesWon: 0,
    });
    setLoading(false);
  }, [connected, publicKey]);

  if (!connected) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <Shield className="w-16 h-16 text-sol-green mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-white mb-4">
          Connect Your Wallet
        </h1>
        <p className="text-gray-400 mb-8 max-w-md mx-auto">
          Connect your Solana wallet to view your dashboard, FairScore, and
          manage your escrows.
        </p>
        <WalletMultiButton className="!bg-sol-green !text-gray-900 !font-semibold !rounded-lg !h-12 !px-8" />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <div className="animate-pulse text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  const tier = profile ? getTierForScore(profile.fairScore / 100) : FAIR_SCORE_TIERS[4];
  const scoreDisplay = profile ? formatFairScore(profile.fairScore) : "0.00";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-gray-400 text-sm mt-1">
            {publicKey?.toBase58().slice(0, 4)}...
            {publicKey?.toBase58().slice(-4)}
          </p>
        </div>
        <Link
          href="/escrow/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-sol-green text-gray-900 font-medium rounded-lg hover:bg-sol-green/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Escrow
        </Link>
      </div>

      {/* FairScore Card */}
      <div className="mb-8 p-6 rounded-xl bg-gradient-to-r from-gray-900 to-gray-800 border border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-gray-400 text-sm mb-1">Your FairScore</div>
            <div className="flex items-baseline gap-3">
              <span className="text-5xl font-bold text-white">
                {scoreDisplay}
              </span>
              <span
                className="text-sm font-medium px-2 py-0.5 rounded-full"
                style={{
                  backgroundColor: tier.color + "20",
                  color: tier.color,
                }}
              >
                {tier.label}
              </span>
            </div>
            <div className="text-gray-500 text-sm mt-2">
              {tier.fee} escrow fee &bull; {tier.hold} hold
            </div>
          </div>
          <div className="text-right">
            <div className="text-gray-400 text-sm mb-1">Next Tier</div>
            <div className="text-white font-medium">
              {tier.label === "Elite" ? "Max tier reached" : `${(tier.min).toFixed(1)}+`}
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={<DollarSign className="w-5 h-5" />}
          label="Total Volume"
          value={`${lamportsToSol(profile?.totalVolume || 0)} SOL`}
        />
        <StatCard
          icon={<ArrowUpRight className="w-5 h-5" />}
          label="Transactions"
          value={String((profile?.buyerTxCount || 0) + (profile?.vendorTxCount || 0))}
        />
        <StatCard
          icon={<TrendingUp className="w-5 h-5" />}
          label="Staked"
          value={`${lamportsToSol(profile?.stakedAmount || 0)} SOL`}
        />
        <StatCard
          icon={<Clock className="w-5 h-5" />}
          label="Disputes"
          value={`${profile?.disputesWon || 0}/${profile?.disputeCount || 0}`}
        />
      </div>

      {/* Active Escrows */}
      <div className="rounded-xl bg-gray-900/50 border border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          Active Escrows
        </h2>
        <div className="text-center py-12 text-gray-500">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No active escrows yet.</p>
          <Link
            href="/escrow/new"
            className="text-sol-green hover:underline text-sm mt-2 inline-block"
          >
            Create your first escrow
          </Link>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="p-4 rounded-lg bg-gray-900/50 border border-gray-800">
      <div className="flex items-center gap-2 text-gray-400 text-sm mb-2">
        {icon}
        {label}
      </div>
      <div className="text-xl font-semibold text-white">{value}</div>
    </div>
  );
}
