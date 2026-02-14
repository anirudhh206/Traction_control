use anchor_lang::prelude::*;
use crate::state::{Escrow, EscrowStatus, Dispute, DisputeReason};
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct OpenDispute<'info> {
    pub initiator: Signer<'info>,

    #[account(
        mut,
        constraint = (escrow.buyer == initiator.key() || escrow.vendor == initiator.key())
            @ RepEscrowError::Unauthorized,
        constraint = escrow.status == EscrowStatus::Funded
            || escrow.status == EscrowStatus::Submitted
            @ RepEscrowError::InvalidEscrowStatus,
    )]
    pub escrow: Account<'info, Escrow>,
}

pub fn handler(ctx: Context<OpenDispute>, reason: DisputeReason) -> Result<()> {
    let escrow = &mut ctx.accounts.escrow;
    let clock = Clock::get()?;

    require!(
        escrow.dispute.is_none(),
        RepEscrowError::DisputeAlreadyOpen
    );

    escrow.dispute = Some(Dispute {
        initiated_by: ctx.accounts.initiator.key(),
        reason,
        arbitrator: None,
        resolution_vendor_pct: None,
        created_at: clock.unix_timestamp,
        resolved_at: None,
    });

    escrow.status = EscrowStatus::Disputed;

    msg!(
        "Dispute opened on escrow by {}. Reason: {:?}",
        ctx.accounts.initiator.key(),
        reason
    );
    Ok(())
}
