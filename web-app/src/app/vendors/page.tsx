"use client";

import { useState } from "react";
import Link from "next/link";
import { Search, Star, Shield, ExternalLink } from "lucide-react";
import { getTierForScore } from "@/lib/constants";

interface Vendor {
  address: string;
  displayName: string;
  fairScore: number;
  completedJobs: number;
  totalVolume: number;
  specialties: string[];
}

// Placeholder vendors for UI demonstration
const PLACEHOLDER_VENDORS: Vendor[] = [
  {
    address: "5Gh7...xK3a",
    displayName: "SolDev Pro",
    fairScore: 4.6,
    completedJobs: 47,
    totalVolume: 215.5,
    specialties: ["Smart Contracts", "DeFi", "Anchor"],
  },
  {
    address: "9Bm2...yP7c",
    displayName: "NFT Artist",
    fairScore: 4.2,
    completedJobs: 32,
    totalVolume: 89.3,
    specialties: ["NFT Art", "Generative", "PFP"],
  },
  {
    address: "3Kw8...zR1d",
    displayName: "Web3 Designer",
    fairScore: 3.8,
    completedJobs: 18,
    totalVolume: 42.1,
    specialties: ["UI/UX", "Landing Pages", "Branding"],
  },
];

export default function VendorsPage() {
  const [search, setSearch] = useState("");

  const filtered = PLACEHOLDER_VENDORS.filter(
    (v) =>
      v.displayName.toLowerCase().includes(search.toLowerCase()) ||
      v.specialties.some((s) =>
        s.toLowerCase().includes(search.toLowerCase())
      )
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Vendors</h1>
          <p className="text-gray-400 text-sm mt-1">
            Find trusted Web3 service providers by FairScore
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-8">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
        <input
          type="text"
          placeholder="Search vendors by name or skill..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-3 bg-gray-900 border border-gray-800 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sol-green/50"
        />
      </div>

      {/* Vendor Grid */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((vendor) => (
          <VendorCard key={vendor.address} vendor={vendor} />
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-20 text-gray-500">
          <Shield className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p>No vendors found matching your search.</p>
        </div>
      )}
    </div>
  );
}

function VendorCard({ vendor }: { vendor: Vendor }) {
  const tier = getTierForScore(vendor.fairScore);

  return (
    <Link
      href={`/vendors/${vendor.address}`}
      className="block p-6 rounded-xl bg-gray-900/50 border border-gray-800 hover:border-gray-700 transition-colors"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">
            {vendor.displayName}
          </h3>
          <p className="text-gray-500 text-sm font-mono">{vendor.address}</p>
        </div>
        <div
          className="flex items-center gap-1 px-2 py-1 rounded-full text-sm font-medium"
          style={{
            backgroundColor: tier.color + "20",
            color: tier.color,
          }}
        >
          <Star className="w-3.5 h-3.5" />
          {vendor.fairScore.toFixed(1)}
        </div>
      </div>

      <div className="flex gap-2 mb-4 flex-wrap">
        {vendor.specialties.map((s) => (
          <span
            key={s}
            className="px-2 py-0.5 bg-gray-800 text-gray-300 text-xs rounded-full"
          >
            {s}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between text-sm text-gray-400">
        <span>{vendor.completedJobs} jobs completed</span>
        <span>{vendor.totalVolume.toFixed(1)} SOL volume</span>
      </div>

      <div className="mt-3 pt-3 border-t border-gray-800 flex items-center justify-between text-sm">
        <span className="text-gray-500">Fee: {tier.fee}</span>
        <span className="text-sol-green flex items-center gap-1">
          View Profile <ExternalLink className="w-3.5 h-3.5" />
        </span>
      </div>
    </Link>
  );
}
