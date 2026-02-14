use anchor_lang::prelude::*;

pub mod error;
pub mod instructions;
pub mod state;

use instructions::*;
use state::DisputeReason;

declare_id!("DQNBgzbhF8WCEcMtVZgG9gDbG2xa7jnNaVnY3vQrdaL9"); // Your actual ID

#[program]
pub mod repescrow {
    use super::*;

    /// Initialize the platform config (one-time admin setup)
    pub fn initialize_platform(
        ctx: Context<InitializePlatform>,
        min_escrow_amount: u64,
    ) -> Result<()> {
        instructions::initialize_platform::handler(ctx, min_escrow_amount)
    }

    /// Create a user profile (required before transacting)
    pub fn create_profile(ctx: Context<CreateProfile>) -> Result<()> {
        instructions::create_profile::handler(ctx)
    }

    /// Create a new escrow between buyer and vendor
    pub fn create_escrow(
        ctx: Context<CreateEscrow>,
        amount: u64,
        milestone_count: u8,
    ) -> Result<()> {
        instructions::create_escrow::handler(ctx, amount, milestone_count)
    }

    /// Fund an existing escrow (buyer deposits SOL)
    pub fn fund_escrow(ctx: Context<FundEscrow>) -> Result<()> {
        instructions::fund_escrow::handler(ctx)
    }

    /// Vendor submits work, starting the hold period
    pub fn submit_work(ctx: Context<SubmitWork>) -> Result<()> {
        instructions::submit_work::handler(ctx)
    }

    /// Release payment to vendor (after hold period)
    pub fn release_payment(ctx: Context<ReleasePayment>) -> Result<()> {
        instructions::release_payment::handler(ctx)
    }

    /// Vendor-initiated refund to buyer
    pub fn refund(ctx: Context<Refund>) -> Result<()> {
        instructions::refund::handler(ctx)
    }

    /// Open a dispute on an active escrow
    pub fn open_dispute(ctx: Context<OpenDispute>, reason: DisputeReason) -> Result<()> {
        instructions::open_dispute::handler(ctx, reason)
    }

    /// Admin resolves a dispute with a percentage split
    pub fn resolve_dispute(ctx: Context<ResolveDispute>, vendor_pct: u8) -> Result<()> {
        instructions::resolve_dispute::handler(ctx, vendor_pct)
    }

    /// Stake SOL for reputation boost
    pub fn stake(ctx: Context<Stake>, amount: u64) -> Result<()> {
        instructions::stake::handler(ctx, amount)
    }

    /// Unstake SOL
    pub fn unstake(ctx: Context<Unstake>, amount: u64) -> Result<()> {
        instructions::unstake::handler(ctx, amount)
    }
}
