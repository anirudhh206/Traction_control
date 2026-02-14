import { PublicKey } from "@solana/web3.js";

// Program ID (update after deploying to devnet)
export const PROGRAM_ID = new PublicKey(
  "REPescrowXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
);

// RPC endpoints
export const RPC_ENDPOINT =
  process.env.NEXT_PUBLIC_RPC_ENDPOINT || "https://api.devnet.solana.com";

// Supabase
export const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
export const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

// FairScore tier configuration
export const FAIR_SCORE_TIERS = [
  { min: 4.5, max: 5.0, fee: "0.5%", hold: "Instant", label: "Elite", color: "#22c55e" },
  { min: 3.5, max: 4.49, fee: "1.0%", hold: "24hr", label: "Trusted", color: "#84cc16" },
  { min: 2.5, max: 3.49, fee: "1.5%", hold: "72hr", label: "Verified", color: "#eab308" },
  { min: 1.5, max: 2.49, fee: "2.0%", hold: "7 days", label: "Building", color: "#f97316" },
  { min: 0, max: 1.49, fee: "2.5%", hold: "14 days", label: "New", color: "#ef4444" },
] as const;

export function getTierForScore(score: number) {
  return FAIR_SCORE_TIERS.find((t) => score >= t.min) || FAIR_SCORE_TIERS[4];
}

// Minimum escrow amount in SOL
export const MIN_ESCROW_SOL = 0.01;
