use anchor_lang::prelude::*;
use crate::state::PlatformConfig;

#[derive(Accounts)]
pub struct InitializePlatform<'info> {
    #[account(mut)]
    pub admin: Signer<'info>,

    #[account(
        init,
        payer = admin,
        space = 8 + PlatformConfig::INIT_SPACE,
        seeds = [b"platform_config"],
        bump,
    )]
    pub platform_config: Account<'info, PlatformConfig>,

    /// CHECK: Treasury wallet to receive fees
    pub treasury: UncheckedAccount<'info>,

    pub system_program: Program<'info, System>,
}

pub fn handler(ctx: Context<InitializePlatform>, min_escrow_amount: u64) -> Result<()> {
    let config = &mut ctx.accounts.platform_config;

    config.admin = ctx.accounts.admin.key();
    config.treasury = ctx.accounts.treasury.key();
    config.total_escrows = 0;
    config.total_volume = 0;
    config.active = true;
    config.min_escrow_amount = min_escrow_amount;
    config.bump = ctx.bumps.platform_config;

    msg!("Platform initialized. Admin: {}", config.admin);
    Ok(())
}
