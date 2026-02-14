use anchor_lang::prelude::*;
use crate::state::{Escrow, EscrowStatus, UserProfile};
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct Refund<'info> {
    /// CHECK: Buyer receiving refund
    #[account(mut)]
    pub buyer: UncheckedAccount<'info>,

    pub vendor: Signer<'info>,

    #[account(
        mut,
        constraint = escrow.vendor == vendor.key() @ RepEscrowError::Unauthorized,
        constraint = escrow.buyer == buyer.key() @ RepEscrowError::InvalidBuyer,
        constraint = escrow.status == EscrowStatus::Funded
            || escrow.status == EscrowStatus::Submitted
            @ RepEscrowError::InvalidEscrowStatus,
    )]
    pub escrow: Account<'info, Escrow>,

    #[account(
        mut,
        seeds = [b"user_profile", vendor.key().as_ref()],
        bump = vendor_profile.bump,
    )]
    pub vendor_profile: Account<'info, UserProfile>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<Refund>) -> Result<()> {
    let escrow = &mut ctx.accounts.escrow;
    let clock = Clock::get()?;

    let refund_amount = escrow.amount - escrow.released_amount;
    require!(refund_amount > 0, RepEscrowError::NothingToRefund);

    // Transfer from escrow PDA to buyer
    let escrow_info = escrow.to_account_info();
    **escrow_info.try_borrow_mut_lamports()? -= refund_amount;

    let buyer_info = ctx.accounts.buyer.to_account_info();
    **buyer_info.try_borrow_mut_lamports()? += refund_amount;

    escrow.status = EscrowStatus::Refunded;

    // Vendor initiated refund — slight score impact
    let vendor_profile = &mut ctx.accounts.vendor_profile;
    vendor_profile.fair_score = vendor_profile.calculate_new_score(false, false);
    vendor_profile.updated_at = clock.unix_timestamp;

    msg!("Refund of {} lamports to buyer {}", refund_amount, escrow.buyer);
    Ok(())
}
