"use client";

import { useState } from "react";
import { useWallet } from "@solana/wallet-adapter-react";
import { WalletMultiButton } from "@solana/wallet-adapter-react-ui";
import {
  Shield,
  Coins,
  ArrowUpRight,
  ArrowDownRight,
  AlertCircle,
} from "lucide-react";

export default function SettingsPage() {
  const { publicKey, connected } = useWallet();
  const [stakeAmount, setStakeAmount] = useState("");
  const [isStaking, setIsStaking] = useState(false);

  if (!connected) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <Shield className="w-16 h-16 text-sol-green mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-white mb-4">
          Connect Your Wallet
        </h1>
        <p className="text-gray-400 mb-8">
          Connect your wallet to access settings.
        </p>
        <WalletMultiButton className="!bg-sol-green !text-gray-900 !font-semibold !rounded-lg !h-12 !px-8" />
      </div>
    );
  }

  const handleStake = async () => {
    if (!stakeAmount || parseFloat(stakeAmount) <= 0) return;
    setIsStaking(true);
    // TODO: Call on-chain stake instruction
    setTimeout(() => setIsStaking(false), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-2xl font-bold text-white mb-8">Settings</h1>

      {/* Wallet Info */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4">Wallet</h2>
        <div className="flex items-center justify-between">
          <div>
            <div className="text-gray-400 text-sm">Connected Wallet</div>
            <div className="text-white font-mono text-sm mt-1">
              {publicKey?.toBase58()}
            </div>
          </div>
          <WalletMultiButton className="!bg-gray-800 !rounded-lg !h-9 !text-sm" />
        </div>
      </div>

      {/* Staking */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800 mb-6">
        <h2 className="text-lg font-semibold text-white mb-2">
          Reputation Staking
        </h2>
        <p className="text-gray-400 text-sm mb-4">
          Stake SOL to boost your FairScore. Stakers earn +5 score bonus per
          successful transaction.
        </p>

        <div className="flex items-center gap-3 mb-4">
          <div className="relative flex-1">
            <input
              type="number"
              step="0.1"
              min="0"
              value={stakeAmount}
              onChange={(e) => setStakeAmount(e.target.value)}
              placeholder="Amount in SOL"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sol-green/50"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">
              SOL
            </span>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={handleStake}
            disabled={isStaking || !stakeAmount}
            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-sol-green text-gray-900 font-medium rounded-lg hover:bg-sol-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowUpRight className="w-4 h-4" />
            {isStaking ? "Staking..." : "Stake"}
          </button>
          <button
            disabled={isStaking}
            className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-700 text-white font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowDownRight className="w-4 h-4" />
            Unstake
          </button>
        </div>

        <div className="mt-4 p-3 bg-yellow-950/30 border border-yellow-900/30 rounded-lg flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" />
          <p className="text-yellow-200/70 text-xs">
            Staked SOL is locked in your profile PDA. You can unstake at any
            time, but your FairScore boost will be removed proportionally.
          </p>
        </div>
      </div>

      {/* Profile Actions */}
      <div className="p-6 rounded-xl bg-gray-900/50 border border-gray-800">
        <h2 className="text-lg font-semibold text-white mb-4">Profile</h2>
        <button className="w-full px-4 py-2.5 bg-sol-purple text-white font-medium rounded-lg hover:bg-sol-purple/80 transition-colors">
          Create Profile (one-time setup)
        </button>
        <p className="text-gray-500 text-xs mt-2 text-center">
          Creates your on-chain profile with a starting FairScore of 2.50
        </p>
      </div>
    </div>
  );
}
