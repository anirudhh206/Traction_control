import { NextRequest, NextResponse } from "next/server";
import { Connection, PublicKey } from "@solana/web3.js";
import { RPC_ENDPOINT, PROGRAM_ID } from "@/lib/constants";

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

    // Fetch all program accounts where buyer or vendor matches wallet
    // TODO: Add proper deserialization with Anchor IDL
    const accounts = await connection.getProgramAccounts(PROGRAM_ID, {
      filters: [
        { dataSize: 200 }, // Approximate escrow account size
      ],
    });

    return NextResponse.json({
      wallet,
      escrowCount: accounts.length,
      message: "Full escrow listing requires Anchor IDL deserialization.",
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch escrows" },
      { status: 500 }
    );
  }
}
