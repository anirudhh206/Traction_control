use anchor_lang::prelude::*;

#[error_code]
pub enum RepEscrowError {
    #[msg("You are not authorized to perform this action")]
    Unauthorized,

    #[msg("The platform is currently paused")]
    PlatformPaused,

    #[msg("Escrow amount is below the minimum")]
    AmountTooLow,

    #[msg("Too many milestones (max 10)")]
    TooManyMilestones,

    #[msg("Cannot create escrow with yourself")]
    SelfEscrow,

    #[msg("Invalid escrow status for this operation")]
    InvalidEscrowStatus,

    #[msg("Invalid vendor for this escrow")]
    InvalidVendor,

    #[msg("Invalid buyer for this escrow")]
    InvalidBuyer,

    #[msg("Invalid treasury account")]
    InvalidTreasury,

    #[msg("Hold period has not elapsed yet")]
    HoldPeriodActive,

    #[msg("Nothing to release")]
    NothingToRelease,

    #[msg("Nothing to refund")]
    NothingToRefund,

    #[msg("A dispute is already open on this escrow")]
    DisputeAlreadyOpen,

    #[msg("Invalid percentage (must be 0-100)")]
    InvalidPercentage,

    #[msg("Insufficient staked amount")]
    InsufficientStake,
}
