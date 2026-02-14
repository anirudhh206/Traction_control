use anchor_lang::prelude::*;
use crate::state::UserProfile;

#[derive(Accounts)]
pub struct CreateProfile<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,

    #[account(
        init,
        payer = authority,
        space = 8 + UserProfile::INIT_SPACE,
        seeds = [b"user_profile", authority.key().as_ref()],
        bump,
    )]
    pub profile: Account<'info, UserProfile>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<CreateProfile>) -> Result<()> {
    let profile = &mut ctx.accounts.profile;
    let clock = Clock::get()?;

    profile.authority = ctx.accounts.authority.key();
    profile.fair_score = 250; // Start at 2.50 (middle tier)
    profile.buyer_tx_count = 0;
    profile.vendor_tx_count = 0;
    profile.dispute_count = 0;
    profile.disputes_won = 0;
    profile.total_volume = 0;
    profile.staked_amount = 0;
    profile.created_at = clock.unix_timestamp;
    profile.updated_at = clock.unix_timestamp;
    profile.bump = ctx.bumps.profile;

    msg!("Profile created for {}. Starting FairScore: 2.50", profile.authority);
    Ok(())
}
