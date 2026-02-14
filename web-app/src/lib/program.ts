import { Connection, PublicKey } from "@solana/web3.js";
import { AnchorProvider, Program, Idl } from "@coral-xyz/anchor";
import { PROGRAM_ID, RPC_ENDPOINT } from "./constants";

// Get the Solana connection
export function getConnection() {
  return new Connection(RPC_ENDPOINT, "confirmed");
}

// Derive PDA helpers
export function getUserProfilePda(wallet: PublicKey): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("user_profile"), wallet.toBuffer()],
    PROGRAM_ID
  );
}

export function getPlatformConfigPda(): [PublicKey, number] {
  return PublicKey.findProgramAddressSync(
    [Buffer.from("platform_config")],
    PROGRAM_ID
  );
}

export function getEscrowPda(
  buyer: PublicKey,
  vendor: PublicKey,
  escrowCount: number
): [PublicKey, number] {
  const buf = Buffer.alloc(8);
  buf.writeBigUInt64LE(BigInt(escrowCount));

  return PublicKey.findProgramAddressSync(
    [Buffer.from("escrow"), buyer.toBuffer(), vendor.toBuffer(), buf],
    PROGRAM_ID
  );
}

// Format FairScore from basis points (250 → "2.50")
export function formatFairScore(basisPoints: number): string {
  return (basisPoints / 100).toFixed(2);
}

// Format lamports to SOL
export function lamportsToSol(lamports: number): string {
  return (lamports / 1_000_000_000).toFixed(4);
}

// Format SOL to lamports
export function solToLamports(sol: number): number {
  return Math.floor(sol * 1_000_000_000);
}
