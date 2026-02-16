import { useState } from "react";
import { PublicKey, SystemProgram, LAMPORTS_PER_SOL } from "@solana/web3.js";
import { useProgram } from "./useProgram";

export function useCreateEscrow() {
  const { program } = useProgram();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createEscrow = async (
    vendor: PublicKey,
    amountSol: number,
    milestones: number = 1
  ) => {
    if (!program) throw new Error("Program not initialized");

    setLoading(true);
    setError(null);

    try {
      const buyer = program.provider.publicKey!;
      const amountLamports = amountSol * LAMPORTS_PER_SOL;

      // Derive escrow PDA
      const escrowKeypair = new PublicKey(0); // You'll generate this
      const [escrowPda] = PublicKey.findProgramAddressSync(
        [
          Buffer.from("escrow"),
          buyer.toBuffer(),
          vendor.toBuffer(),
          escrowKeypair.toBuffer(),
        ],
        program.programId
      );

      const tx = await program.methods
        .createEscrow(
          new BN(amountLamports),
          milestones
        )
        .accounts({
          escrow: escrowPda,
          buyer: buyer,
          vendor: vendor,
          systemProgram: SystemProgram.programId,
        })
        .rpc();

      console.log("Escrow created:", tx);
      return { signature: tx, escrowPda };
    } catch (err: any) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createEscrow, loading, error };
}