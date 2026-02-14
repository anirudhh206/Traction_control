use anchor_lang::prelude::*;
use crate::state::{Escrow, EscrowStatus, UserProfile, PlatformConfig};
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct ResolveDispute<'info> {
    /// Platform admin acting as arbitrator
    pub admin: Signer<'info>,

    /// CHECK: Buyer in the dispute
    #[account(mut)]
    pub buyer: UncheckedAccount<'info>,

    /// CHECK: Vendor in the dispute
    #[account(mut)]
    pub vendor: UncheckedAccount<'info>,

    #[account(
        mut,
        constraint = escrow.status == EscrowStatus::Disputed @ RepEscrowError::InvalidEscrowStatus,
        constraint = escrow.buyer == buyer.key() @ RepEscrowError::InvalidBuyer,
        constraint = escrow.vendor == vendor.key() @ RepEscrowError::InvalidVendor,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [b"user_profile", vendor.key().as_ref()],
        bump = vendor_profile.bump,
    )]
    pub vendor_profile: Account<'info, UserProfile>,

    #[account(
        mut,
        seeds = [b"user_profile", buyer.key().as_ref()],
        bump = buyer_profile.bump,
    )]
    pub buyer_profile: Account<'info, UserProfile>,

    /// CHECK: Treasury for fees
    #[account(
        mut,
        constraint = treasury.key() == platform_config.treasury @ RepEscrowError::InvalidTreasury,
    )]
    pub treasury: UncheckedAccount<'info>,

    #[account(
        mut,
        seeds = [b"platform_config"],
        bump = platform_config.bump,
        constraint = platform_config.admin == admin.key() @ RepEscrowError::Unauthorized,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    pub system_program: Program<'info, System>,
}

/// vendor_pct: 0-100, percentage of remaining funds that go to vendor
pub fn handler(ctx: Context<ResolveDispute>, vendor_pct: u8) -> Result<()> {
    require!(vendor_pct <= 100, RepEscrowError::InvalidPercentage);

    let escrow = &mut ctx.accounts.escrow;
    let clock = Clock::get()?;

    let remaining = escrow.amount - escrow.released_amount;
    require!(remaining > 0, RepEscrowError::NothingToRelease);

    // Calculate split
    let vendor_share = (remaining as u128)
        .checked_mul(vendor_pct as u128)
        .unwrap()
        .checked_div(100)
        .unwrap() as u64;
    let buyer_share = remaining - vendor_share;

    // Calculate fee on vendor's portion only
    let fee = (vendor_share as u128)
        .checked_mul(escrow.fee_bps as u128)
        .unwrap()
        .checked_div(10_000)
        .unwrap() as u64;
    let vendor_net = vendor_share - fee;

    // Transfer funds
    let escrow_info = escrow.to_account_info();
    **escrow_info.try_borrow_mut_lamports()? -= remaining;

    if vendor_net > 0 {
        let vendor_info = ctx.accounts.vendor.to_account_info();
        **vendor_info.try_borrow_mut_lamports()? += vendor_net;
    }

    if buyer_share > 0 {
        let buyer_info = ctx.accounts.buyer.to_account_info();
        **buyer_info.try_borrow_mut_lamports()? += buyer_share;
    }

    if fee > 0 {
        let treasury_info = ctx.accounts.treasury.to_account_info();
        **treasury_info.try_borrow_mut_lamports()? += fee;
    }

    // Update dispute resolution
    if let Some(ref mut dispute) = escrow.dispute {
        dispute.arbitrator = Some(ctx.accounts.admin.key());
        dispute.resolution_vendor_pct = Some(vendor_pct);
        dispute.resolved_at = Some(clock.unix_timestamp);
    }

    escrow.released_amount = escrow.amount;
    escrow.status = EscrowStatus::Released;

    // Update profiles — dispute impacts scores
    let vendor_profile = &mut ctx.accounts.vendor_profile;
    vendor_profile.dispute_count += 1;
    if vendor_pct >= 50 {
        vendor_profile.disputes_won += 1;
    }
    vendor_profile.fair_score = vendor_profile.calculate_new_score(vendor_pct >= 50, true);
    vendor_profile.updated_at = clock.unix_timestamp;

    let buyer_profile = &mut ctx.accounts.buyer_profile;
    buyer_profile.dispute_count += 1;
    if vendor_pct < 50 {
        buyer_profile.disputes_won += 1;
    }
    buyer_profile.fair_score = buyer_profile.calculate_new_score(vendor_pct < 50, true);
    buyer_profile.updated_at = clock.unix_timestamp;

    // Update platform volume
    let config = &mut ctx.accounts.platform_config;
    config.total_volume += remaining;

    msg!(
        "Dispute resolved: {}% to vendor ({}), {}% to buyer ({}). Fee: {}",
        vendor_pct,
        vendor_net,
        100 - vendor_pct,
        buyer_share,
        fee
    );

    Ok(())
}
