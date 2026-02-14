use anchor_lang::prelude::*;
use crate::state::UserProfile;
use crate::error::RepEscrowError;

#[derive(Accounts)]
pub struct Unstake<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,

    #[account(
        mut,
        seeds = [b"user_profile", authority.key().as_ref()],
        bump = profile.bump,
        constraint = profile.authority == authority.key(),
    )]
    pub profile: Account<'info, UserProfile>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<Unstake>, amount: u64) -> Result<()> {
    let profile = &mut ctx.accounts.profile;
    let clock = Clock::get()?;

    require!(
        amount > 0 && amount <= profile.staked_amount,
        RepEscrowError::InsufficientStake
    );

    // Transfer from profile PDA back to user
    let profile_info = profile.to_account_info();
    **profile_info.try_borrow_mut_lamports()? -= amount;

    let authority_info = ctx.accounts.authority.to_account_info();
    **authority_info.try_borrow_mut_lamports()? += amount;

    profile.staked_amount -= amount;
    profile.updated_at = clock.unix_timestamp;

    // Remove staking boost proportionally
    let reduction = std::cmp::min((amount / 1_000_000_000) as u16, 25);
    profile.fair_score = profile.fair_score.saturating_sub(reduction);

    msg!(
        "Unstaked {} lamports. Remaining: {}. FairScore: {}",
        amount,
        profile.staked_amount,
        profile.fair_score
    );
    Ok(())
}
