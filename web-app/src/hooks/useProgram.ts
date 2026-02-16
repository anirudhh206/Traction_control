import { useConnection, useWallet } from "@solana/wallet-adapter-react";
import { AnchorProvider, Program } from "@coral-xyz/anchor";
import { useMemo } from "react";
import { PROGRAM_ID } from "@/lib/constants";
import IDL from "@/idl/repescrow.json";
import type { Repescrow } from "@/idl/repescrow";

export function useProgram() {
  const { connection } = useConnection();
  const wallet = useWallet();

  const provider = useMemo(() => {
    if (!wallet.publicKey) return null;
    
    return new AnchorProvider(
      connection,
      wallet as any,
      { commitment: "confirmed" }
    );
  }, [connection, wallet]);

  const program = useMemo(() => {
    if (!provider) return null;
    
    return new Program<Repescrow>(
      IDL as Repescrow,
      PROGRAM_ID,
      provider
    );
  }, [provider]);

  return { program, provider, connected: !!wallet.publicKey };
}