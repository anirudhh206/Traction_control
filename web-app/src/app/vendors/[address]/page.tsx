"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import {
  Star,
  Shield,
  Clock,
  DollarSign,
  ArrowLeft,
  CheckCircle,
} from "lucide-react";
import { getTierForScore, FAIR_SCORE_TIERS } from "@/lib/constants";

export default function VendorProfilePage() {
  const params = useParams();
  const address = params.address as string;

  // TODO: Fetch vendor profile from on-chain
  const vendor = {
    address,
    displayName: "Vendor Profile",
    fairScore: 3.5,
    completedJobs: 12,
    totalVolume: 45.2,
    disputeCount: 1,
    disputesWon: 1,
    stakedAmount: 5.0,
    specialties: ["Smart Contracts", "DeFi"],
    createdAt: "2024-01-15",
  };

  const tier = getTierForScore(vendor.fairScore);

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link
        href="/vendors"
        className="inline-flex items-center gap-1 text-gray-400 hover:text-white text-sm mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Vendors
      </Link>

      {/* Profile Header */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800 mb-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">
              {vendor.displayName}
            </h1>
            <p className="text-gray-500 font-mono text-sm">{vendor.address}</p>
            <p className="text-gray-600 text-xs mt-1">
              Member since {vendor.createdAt}
            </p>
          </div>
          <div className="text-right">
            <div
              className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-lg font-bold"
              style={{
                backgroundColor: tier.color + "20",
                color: tier.color,
              }}
            >
              <Star className="w-5 h-5" />
              {vendor.fairScore.toFixed(2)}
            </div>
            <div className="text-gray-500 text-xs mt-1">
              {tier.label} Tier &bull; {tier.fee} fee
            </div>
          </div>
        </div>

        <div className="flex gap-2 mb-6 flex-wrap">
          {vendor.specialties.map((s) => (
            <span
              key={s}
              className="px-3 py-1 bg-gray-800 text-gray-300 text-sm rounded-full"
            >
              {s}
            </span>
          ))}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-3 rounded-lg bg-gray-800/50">
            <div className="text-gray-400 text-xs mb-1 flex items-center gap-1">
              <CheckCircle className="w-3 h-3" /> Completed
            </div>
            <div className="text-white font-semibold">
              {vendor.completedJobs} jobs
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-800/50">
            <div className="text-gray-400 text-xs mb-1 flex items-center gap-1">
              <DollarSign className="w-3 h-3" /> Volume
            </div>
            <div className="text-white font-semibold">
              {vendor.totalVolume} SOL
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-800/50">
            <div className="text-gray-400 text-xs mb-1 flex items-center gap-1">
              <Shield className="w-3 h-3" /> Disputes
            </div>
            <div className="text-white font-semibold">
              {vendor.disputesWon}/{vendor.disputeCount} won
            </div>
          </div>
          <div className="p-3 rounded-lg bg-gray-800/50">
            <div className="text-gray-400 text-xs mb-1 flex items-center gap-1">
              <Clock className="w-3 h-3" /> Staked
            </div>
            <div className="text-white font-semibold">
              {vendor.stakedAmount} SOL
            </div>
          </div>
        </div>
      </div>

      {/* FairScore Breakdown */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">
          FairScore Breakdown
        </h2>
        <div className="space-y-3">
          {FAIR_SCORE_TIERS.map((t) => (
            <div key={t.label} className="flex items-center gap-3">
              <div
                className="w-2 h-2 rounded-full flex-shrink-0"
                style={{ backgroundColor: t.color }}
              />
              <div className="flex-1 h-2 bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{
                    width:
                      vendor.fairScore >= t.min
                        ? "100%"
                        : vendor.fairScore >= t.min - 1
                        ? `${((vendor.fairScore - (t.min - 1)) / 1) * 100}%`
                        : "0%",
                    backgroundColor: t.color,
                  }}
                />
              </div>
              <span className="text-gray-500 text-xs w-16 text-right">
                {t.label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Create Escrow CTA */}
      <div className="p-6 rounded-xl bg-gradient-to-r from-sol-purple/10 to-sol-green/10 border border-gray-800 text-center">
        <h3 className="text-lg font-semibold text-white mb-2">
          Want to work with this vendor?
        </h3>
        <p className="text-gray-400 text-sm mb-4">
          Create an escrow with {tier.fee} fee based on their {tier.label}{" "}
          FairScore.
        </p>
        <Link
          href={`/escrow/new?vendor=${vendor.address}`}
          className="inline-flex items-center gap-2 px-6 py-2.5 bg-sol-green text-gray-900 font-medium rounded-lg hover:bg-sol-green/90 transition-colors"
        >
          Create Escrow
        </Link>
      </div>
    </div>
  );
}
