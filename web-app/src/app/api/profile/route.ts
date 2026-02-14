import { NextRequest, NextResponse } from "next/server";
import { Connection, PublicKey } from "@solana/web3.js";
import { RPC_ENDPOINT, PROGRAM_ID } from "@/lib/constants";
import { getUserProfilePda, formatFairScore } from "@/lib/program";

export async function GET(request: NextRequest) {
  const wallet = request.nextUrl.searchParams.get("wallet");

  if (!wallet) {
    return NextResponse.json(
      { error: "wallet parameter required" },
      { status: 400 }
    );
  }

  try {
    const connection = new Connection(RPC_ENDPOINT, "confirmed");
    const walletPubkey = new PublicKey(wallet);
    const [profilePda] = getUserProfilePda(walletPubkey);

    const accountInfo = await connection.getAccountInfo(profilePda);

    if (!accountInfo) {
      return NextResponse.json(
        { error: "Profile not found. Create one first.", exists: false },
        { status: 404 }
      );
    }

    // TODO: Deserialize account data using Anchor IDL
    // For now, return a placeholder
    return NextResponse.json({
      exists: true,
      wallet,
      profilePda: profilePda.toBase58(),
      message: "Profile found. Full deserialization requires Anchor IDL.",
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch profile" },
      { status: 500 }
    );
  }
}
