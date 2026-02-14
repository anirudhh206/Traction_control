use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::state::{Escrow, EscrowStatus};
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct FundEscrow<'info> {
    #[account(mut)]
    pub buyer: Signer<'info>,

    #[account(
        mut,
        constraint = escrow.buyer == buyer.key() @ RepEscrowError::Unauthorized,
        constraint = escrow.status == EscrowStatus::Created @ RepEscrowError::InvalidEscrowStatus,
    )]
    pub escrow: Account<'info, Escrow>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<FundEscrow>) -> Result<()> {
    let escrow = &mut ctx.accounts.escrow;

    // Transfer SOL from buyer to escrow PDA
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.buyer.to_account_info(),
                to: escrow.to_account_info(),
            },
        ),
        escrow.amount,
    )?;

    escrow.status = EscrowStatus::Funded;

    msg!("Escrow funded with {} lamports by {}", escrow.amount, escrow.buyer);
    Ok(())
}
