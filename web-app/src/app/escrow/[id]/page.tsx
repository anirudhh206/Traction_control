"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Shield,
  Clock,
  CheckCircle,
  AlertTriangle,
  DollarSign,
} from "lucide-react";

type EscrowStatus =
  | "Created"
  | "Funded"
  | "Submitted"
  | "Released"
  | "Refunded"
  | "Disputed";

const STATUS_CONFIG: Record<
  EscrowStatus,
  { color: string; icon: React.ReactNode; label: string }
> = {
  Created: {
    color: "#6b7280",
    icon: <Clock className="w-4 h-4" />,
    label: "Awaiting Funding",
  },
  Funded: {
    color: "#3b82f6",
    icon: <DollarSign className="w-4 h-4" />,
    label: "Funded - In Progress",
  },
  Submitted: {
    color: "#eab308",
    icon: <Clock className="w-4 h-4" />,
    label: "Work Submitted - Hold Period",
  },
  Released: {
    color: "#22c55e",
    icon: <CheckCircle className="w-4 h-4" />,
    label: "Payment Released",
  },
  Refunded: {
    color: "#f97316",
    icon: <Shield className="w-4 h-4" />,
    label: "Refunded",
  },
  Disputed: {
    color: "#ef4444",
    icon: <AlertTriangle className="w-4 h-4" />,
    label: "Dispute Open",
  },
};

export default function EscrowDetailPage() {
  const params = useParams();
  const id = params.id as string;

  // TODO: Fetch escrow from on-chain
  const escrow = {
    id,
    buyer: "5Gh7...xK3a",
    vendor: "9Bm2...yP7c",
    amount: 2.5,
    releasedAmount: 0,
    feeBps: 150,
    status: "Funded" as EscrowStatus,
    milestoneCount: 0,
    holdPeriod: 259200, // 72hr
    createdAt: "2024-03-01T10:00:00Z",
    releaseAfter: null,
  };

  const statusConfig = STATUS_CONFIG[escrow.status];
  const feePercent = (escrow.feeBps / 100).toFixed(1);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1 text-gray-400 hover:text-white text-sm mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>

      {/* Escrow Header */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800 mb-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white mb-1">
              Escrow #{escrow.id.slice(0, 8)}
            </h1>
            <p className="text-gray-500 text-sm">
              Created {new Date(escrow.createdAt).toLocaleDateString()}
            </p>
          </div>
          <div
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium"
            style={{
              backgroundColor: statusConfig.color + "20",
              color: statusConfig.color,
            }}
          >
            {statusConfig.icon}
            {statusConfig.label}
          </div>
        </div>

        {/* Amount */}
        <div className="text-center py-8 border-y border-gray-800 mb-6">
          <div className="text-gray-400 text-sm mb-1">Escrow Amount</div>
          <div className="text-4xl font-bold text-white">
            {escrow.amount} SOL
          </div>
          <div className="text-gray-500 text-sm mt-1">
            {feePercent}% fee ({((escrow.amount * escrow.feeBps) / 10000).toFixed(4)}{" "}
            SOL)
          </div>
        </div>

        {/* Parties */}
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="p-4 rounded-lg bg-gray-800/50">
            <div className="text-gray-400 text-xs mb-1">Buyer</div>
            <div className="text-white font-mono text-sm">{escrow.buyer}</div>
          </div>
          <div className="p-4 rounded-lg bg-gray-800/50">
            <div className="text-gray-400 text-xs mb-1">Vendor</div>
            <div className="text-white font-mono text-sm">{escrow.vendor}</div>
          </div>
        </div>

        {/* Details */}
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-gray-400 text-xs mb-1">Fee Tier</div>
            <div className="text-white font-medium">{feePercent}%</div>
          </div>
          <div className="text-center">
            <div className="text-gray-400 text-xs mb-1">Hold Period</div>
            <div className="text-white font-medium">
              {Math.floor(escrow.holdPeriod / 3600)}hr
            </div>
          </div>
          <div className="text-center">
            <div className="text-gray-400 text-xs mb-1">Milestones</div>
            <div className="text-white font-medium">
              {escrow.milestoneCount || "Single Payment"}
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800">
        <h2 className="text-lg font-semibold text-white mb-4">Actions</h2>

        <div className="space-y-3">
          {escrow.status === "Created" && (
            <button className="w-full px-4 py-3 bg-sol-green text-gray-900 font-medium rounded-lg hover:bg-sol-green/90 transition-colors">
              Fund Escrow ({escrow.amount} SOL)
            </button>
          )}

          {escrow.status === "Funded" && (
            <>
              <button className="w-full px-4 py-3 bg-sol-purple text-white font-medium rounded-lg hover:bg-sol-purple/80 transition-colors">
                Submit Work (Vendor)
              </button>
              <button className="w-full px-4 py-3 border border-red-800 text-red-400 font-medium rounded-lg hover:bg-red-950/30 transition-colors">
                Open Dispute
              </button>
            </>
          )}

          {escrow.status === "Submitted" && (
            <button className="w-full px-4 py-3 bg-sol-green text-gray-900 font-medium rounded-lg hover:bg-sol-green/90 transition-colors">
              Release Payment (Buyer)
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
