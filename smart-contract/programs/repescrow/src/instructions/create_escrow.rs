use anchor_lang::prelude::*;
use crate::state::{Escrow, EscrowStatus, UserProfile, PlatformConfig};
use crate::error::RepEscrowError;

#[derive(Accounts)]
#[instruction(amount: u64, milestone_count: u8)]
pub struct CreateEscrow<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,

    /// CHECK: Vendor's wallet address
    pub vendor: UncheckedAccount<'info>,

    #[account(
        seeds = [b"user_profile", vendor.key().as_ref()],
        bump = vendor_profile.bump,
    )]
    pub vendor_profile: Account<'info, UserProfile>,

    #[account(
        init,
        payer = buyer,
        space = 8 + Escrow::INIT_SPACE,
        seeds = [
            b"escrow",
            buyer.key().as_ref(),
            vendor.key().as_ref(),
            &platform_config.total_escrows.to_le_bytes(),
        ],
        bump,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [b"platform_config"],
        bump = platform_config.bump,
        constraint = platform_config.active @ RepEscrowError::PlatformPaused,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<CreateEscrow>, amount: u64, milestone_count: u8) -> Result<()> {
    let config = &ctx.accounts.platform_config;

    require!(
        amount >= config.min_escrow_amount,
        RepEscrowError::AmountTooLow
    );

    require!(
        milestone_count <= 10,
        RepEscrowError::TooManyMilestones
    );

    require!(
        ctx.accounts.buyer.key() != ctx.accounts.vendor.key(),
        RepEscrowError::SelfEscrow
    );

    let vendor_profile = &ctx.accounts.vendor_profile;
    let fee_bps = vendor_profile.get_fee_bps();
    let hold_period = vendor_profile.get_hold_period();

    let escrow = &mut ctx.accounts.escrow;
    let clock = Clock::get()?;

    escrow.buyer = ctx.accounts.buyer.key();
    escrow.vendor = ctx.accounts.vendor.key();
    escrow.amount = amount;
    escrow.released_amount = 0;
    escrow.fee_bps = fee_bps;
    escrow.status = EscrowStatus::Created;
    escrow.milestone_count = milestone_count;
    escrow.current_milestone = 0;
    escrow.hold_period = hold_period;
    escrow.created_at = clock.unix_timestamp;
    escrow.release_after = 0; // Set when work is submitted
    escrow.dispute = None;
    escrow.bump = ctx.bumps.escrow;

    // Increment platform counter
    let config = &mut ctx.accounts.platform_config;
    config.total_escrows += 1;

    msg!(
        "Escrow created: {} SOL, fee {}bps, hold {}s. Buyer: {}, Vendor: {}",
        amount,
        fee_bps,
        hold_period,
        escrow.buyer,
        escrow.vendor,
    );

    Ok(())
}
