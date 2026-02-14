use anchor_lang::prelude::*;
use crate::state::{Escrow, EscrowStatus};
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct SubmitWork<'info> {
    pub vendor: Signer<'info>,

    #[account(
        mut,
        constraint = escrow.vendor == vendor.key() @ RepEscrowError::Unauthorized,
        constraint = escrow.status == EscrowStatus::Funded @ RepEscrowError::InvalidEscrowStatus,
    )]
    pub escrow: Account<'info, Escrow>,
}

pub fn handler(ctx: Context<SubmitWork>) -> Result<()> {
    let escrow = &mut ctx.accounts.escrow;
    let clock = Clock::get()?;

    escrow.status = EscrowStatus::Submitted;
    escrow.release_after = clock.unix_timestamp + escrow.hold_period;

    msg!(
        "Work submitted for escrow. Release after: {} (hold: {}s)",
        escrow.release_after,
        escrow.hold_period,
    );
    Ok(())
}
