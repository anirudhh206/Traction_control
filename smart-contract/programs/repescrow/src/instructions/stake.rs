use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::state::UserProfile;

#[derive(Accounts)]
pub struct Stake<'info> {
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

pub fn handler(ctx: Context<Stake>, amount: u64) -> Result<()> {
    require!(amount > 0, anchor_lang::error::ErrorCode::InstructionMissing);

    // Transfer SOL from user to profile PDA (staking)
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.authority.to_account_info(),
                to: ctx.accounts.profile.to_account_info(),
            },
        ),
        amount,
    )?;

    let profile = &mut ctx.accounts.profile;
    let clock = Clock::get()?;

    profile.staked_amount += amount;
    profile.updated_at = clock.unix_timestamp;

    // Staking gives a small FairScore boost
    let boost = std::cmp::min((amount / 1_000_000_000) as u16, 25); // Max +0.25 boost
    profile.fair_score = std::cmp::min(profile.fair_score + boost, 500);

    msg!(
        "Staked {} lamports. Total staked: {}. FairScore: {}",
        amount,
        profile.staked_amount,
        profile.fair_score
    );
    Ok(())
}
