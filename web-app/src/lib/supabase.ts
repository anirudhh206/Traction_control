import { createClient } from "@supabase/supabase-js";
import { SUPABASE_URL, SUPABASE_ANON_KEY } from "./constants";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Track a signup (wallet connect)
export async function trackSignup(walletAddress: string) {
  const { error } = await supabase.from("signups").insert({
    wallet_address: walletAddress,
    signed_up_at: new Date().toISOString(),
  });

  if (error) {
    console.error("Failed to track signup:", error);
  }
}

// Track an escrow creation
export async function trackEscrowCreation(
  buyerWallet: string,
  vendorWallet: string,
  amountSol: number
) {
  const { error } = await supabase.from("escrow_events").insert({
    buyer_wallet: buyerWallet,
    vendor_wallet: vendorWallet,
    amount_sol: amountSol,
    event_type: "created",
    created_at: new Date().toISOString(),
  });

  if (error) {
    console.error("Failed to track escrow:", error);
  }
}
