use anchor_lang::prelude::*;
use crate::state::{Escrow, EscrowStatus, UserProfile, PlatformConfig};
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct ReleasePayment<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,

    /// CHECK: Vendor receiving payment
    #[account(mut)]
    pub vendor: UncheckedAccount<'info>,

    #[account(
        mut,
        constraint = escrow.buyer == buyer.key() @ RepEscrowError::Unauthorized,
        constraint = escrow.vendor == vendor.key() @ RepEscrowError::InvalidVendor,
        constraint = escrow.status == EscrowStatus::Submitted @ RepEscrowError::InvalidEscrowStatus,
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
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<ReleasePayment>) -> Result<()> {
    let escrow = &mut ctx.accounts.escrow;
    let clock = Clock::get()?;

    // Check hold period has passed
    require!(
        clock.unix_timestamp >= escrow.release_after,
        RepEscrowError::HoldPeriodActive
    );

    let amount = escrow.amount - escrow.released_amount;
    require!(amount > 0, RepEscrowError::NothingToRelease);

    // Calculate fee
    let fee = (amount as u128)
        .checked_mul(escrow.fee_bps as u128)
        .unwrap()
        .checked_div(10_000)
        .unwrap() as u64;

    let vendor_amount = amount - fee;

    // Transfer from escrow PDA to vendor
    let escrow_info = escrow.to_account_info();
    **escrow_info.try_borrow_mut_lamports()? -= amount;

    let vendor_info = ctx.accounts.vendor.to_account_info();
    **vendor_info.try_borrow_mut_lamports()? += vendor_amount;

    // Transfer fee to treasury
    let treasury_info = ctx.accounts.treasury.to_account_info();
    **treasury_info.try_borrow_mut_lamports()? += fee;

    // Update escrow state
    escrow.released_amount += amount;
    escrow.status = EscrowStatus::Released;

    // Update profiles
    let vendor_profile = &mut ctx.accounts.vendor_profile;
    vendor_profile.vendor_tx_count += 1;
    vendor_profile.total_volume += amount;
    vendor_profile.fair_score = vendor_profile.calculate_new_score(true, false);
    vendor_profile.updated_at = clock.unix_timestamp;

    let buyer_profile = &mut ctx.accounts.buyer_profile;
    buyer_profile.buyer_tx_count += 1;
    buyer_profile.total_volume += amount;
    buyer_profile.fair_score = buyer_profile.calculate_new_score(true, false);
    buyer_profile.updated_at = clock.unix_timestamp;

    // Update platform volume
    let config = &mut ctx.accounts.platform_config;
    config.total_volume += amount;

    msg!(
        "Payment released: {} to vendor, {} fee to treasury",
        vendor_amount,
        fee
    );

    Ok(())
}
