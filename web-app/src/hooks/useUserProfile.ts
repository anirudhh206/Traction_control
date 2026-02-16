import { useEffect, useState } from "react";
import { PublicKey } from "@solana/web3.js";
import { useProgram } from "./useProgram";

export interface UserProfile {
  authority: PublicKey;
  fairScore: number;
  buyerTxCount: number;
  vendorTxCount: number;
  disputeCount: number;
  disputesWon: number;
  totalVolume: number;
  stakedAmount: number;
  createdAt: number;
  updatedAt: number;
}

export function useUserProfile(address?: PublicKey) {
  const { program, connected } = useProgram();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!program || !address) return;

    const fetchProfile = async () => {
      setLoading(true);
      setError(null);

      try {
        const [profilePda] = PublicKey.findProgramAddressSync(
          [Buffer.from("user_profile"), address.toBuffer()],
          program.programId
        );

        const profileAccount = await program.account.userProfile.fetch(profilePda);
        
        setProfile({
          authority: profileAccount.authority,
          fairScore: profileAccount.fairScore / 100, // Convert basis points to decimal
          buyerTxCount: profileAccount.buyerTxCount,
          vendorTxCount: profileAccount.vendorTxCount,
          disputeCount: profileAccount.disputeCount,
          disputesWon: profileAccount.disputesWon,
          totalVolume: profileAccount.totalVolume.toNumber(),
          stakedAmount: profileAccount.stakedAmount.toNumber(),
          createdAt: profileAccount.createdAt.toNumber(),
          updatedAt: profileAccount.updatedAt.toNumber(),
        });
      } catch (err: any) {
        if (err.message.includes("Account does not exist")) {
          setProfile(null); // Profile not created yet
        } else {
          setError(err.message);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [program, address]);

  return { profile, loading, error };
}