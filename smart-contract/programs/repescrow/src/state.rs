use anchor_lang::prelude::*;

// ---------------------------------------------------------------------------
// Escrow Account
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct Escrow {
    /// Buyer (depositor) public key
    pub buyer: Pubkey,
    /// Vendor (service provider) public key
    pub vendor: Pubkey,
    /// Total escrow amount in lamports (or token smallest unit)
    pub amount: u64,
    /// Amount already released to vendor
    pub released_amount: u64,
    /// Fee percentage in basis points (50 = 0.5%, 250 = 2.5%)
    pub fee_bps: u16,
    /// Escrow status
    pub status: EscrowStatus,
    /// Number of milestones (0 = single payment)
    pub milestone_count: u8,
    /// Current milestone index (0-based)
    pub current_milestone: u8,
    /// Hold period in seconds (based on vendor's tier)
    pub hold_period: i64,
    /// Timestamp when escrow was created
    pub created_at: i64,
    /// Timestamp when payment can be released (after hold period)
    pub release_after: i64,
    /// Dispute details (if any)
    pub dispute: Option<Dispute>,
    /// Bump seed for PDA
    pub bump: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum EscrowStatus {
    /// Escrow created, awaiting deposit
    Created,
    /// Funds deposited, work in progress
    Funded,
    /// Vendor submitted work, hold period started
    Submitted,
    /// Payment released to vendor
    Released,
    /// Refunded to buyer
    Refunded,
    /// Active dispute
    Disputed,
    /// Cancelled before funding
    Cancelled,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct Dispute {
    /// Who initiated the dispute
    pub initiated_by: Pubkey,
    /// Reason (short description hash or enum)
    pub reason: DisputeReason,
    /// Arbitrator assigned
    pub arbitrator: Option<Pubkey>,
    /// Resolution: percentage to vendor (0-100, rest goes to buyer)
    pub resolution_vendor_pct: Option<u8>,
    /// Timestamp of dispute creation
    pub created_at: i64,
    /// Timestamp of resolution
    pub resolved_at: Option<i64>,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug, PartialEq, Eq, InitSpace)]
pub enum DisputeReason {
    WorkNotDelivered,
    QualityIssue,
    ScopeDisagreement,
    PaymentDispute,
    Other,
}

// ---------------------------------------------------------------------------
// User Profile (on-chain reputation tracking)
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct UserProfile {
    /// User's wallet
    pub authority: Pubkey,
    /// FairScore (stored as basis points: 450 = 4.50)
    pub fair_score: u16,
    /// Total completed transactions as buyer
    pub buyer_tx_count: u32,
    /// Total completed transactions as vendor
    pub vendor_tx_count: u32,
    /// Total dispute count
    pub dispute_count: u16,
    /// Disputes won
    pub disputes_won: u16,
    /// Total volume transacted (in lamports)
    pub total_volume: u64,
    /// Staked amount for reputation boost
    pub staked_amount: u64,
    /// Timestamp of profile creation
    pub created_at: i64,
    /// Last updated timestamp
    pub updated_at: i64,
    /// Bump seed for PDA
    pub bump: u8,
}

impl UserProfile {
    /// Get the FairScore as a float-like value (e.g., 450 → 4.50)
    pub fn fair_score_display(&self) -> f64 {
        self.fair_score as f64 / 100.0
    }

    /// Get fee tier based on FairScore
    pub fn get_fee_bps(&self) -> u16 {
        match self.fair_score {
            450..=500 => 50,   // 0.5% - Top tier
            350..=449 => 100,  // 1.0% - Good
            250..=349 => 150,  // 1.5% - Average
            150..=249 => 200,  // 2.0% - Below average
            _ => 250,          // 2.5% - New/low reputation
        }
    }

    /// Get hold period in seconds based on FairScore
    pub fn get_hold_period(&self) -> i64 {
        match self.fair_score {
            450..=500 => 0,           // Instant release
            350..=449 => 86_400,      // 24 hours
            250..=349 => 259_200,     // 72 hours
            150..=249 => 604_800,     // 7 days
            _ => 1_209_600,           // 14 days
        }
    }

    /// Calculate updated FairScore after a completed transaction
    pub fn calculate_new_score(&self, successful: bool, dispute: bool) -> u16 {
        let current = self.fair_score as i32;
        let total_tx = (self.buyer_tx_count + self.vendor_tx_count) as i32;

        // Base adjustment
        let mut adjustment: i32 = if successful { 10 } else { -20 };

        // Dispute penalty
        if dispute {
            adjustment -= 15;
        }

        // Staking bonus (stakers get +5 per successful tx)
        if successful && self.staked_amount > 0 {
            adjustment += 5;
        }

        // Early transactions have more weight (bootstrapping)
        if total_tx < 10 {
            adjustment = adjustment * 2;
        }

        let new_score = (current + adjustment).clamp(0, 500);
        new_score as u16
    }
}

// ---------------------------------------------------------------------------
// Milestone
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct MilestoneList {
    /// Parent escrow
    pub escrow: Pubkey,
    /// Milestone details
    #[max_len(10)]
    pub milestones: Vec<Milestone>,
    /// Bump seed
    pub bump: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, InitSpace)]
pub struct Milestone {
    /// Amount for this milestone (in lamports)
    pub amount: u64,
    /// Description hash (store full description off-chain)
    #[max_len(64)]
    pub description_hash: String,
    /// Status of this milestone
    pub status: MilestoneStatus,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, PartialEq, Eq, InitSpace)]
pub enum MilestoneStatus {
    Pending,
    InProgress,
    Submitted,
    Approved,
    Disputed,
}

// ---------------------------------------------------------------------------
// Platform Config (admin-controlled)
// ---------------------------------------------------------------------------

#[account]
#[derive(InitSpace)]
pub struct PlatformConfig {
    /// Platform admin
    pub admin: Pubkey,
    /// Treasury wallet for fees
    pub treasury: Pubkey,
    /// Total escrows created
    pub total_escrows: u64,
    /// Total volume processed
    pub total_volume: u64,
    /// Whether new escrows are enabled
    pub active: bool,
    /// Minimum escrow amount (lamports)
    pub min_escrow_amount: u64,
    /// Bump seed
    pub bump: u8,
}
