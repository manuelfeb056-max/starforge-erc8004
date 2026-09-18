// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title IRandomness — randomness provider interface for StarforgeArena
/// @notice Swap implementations per environment:
///         - BlockhashRandomness (Monad testnet demo)
///         - A real VRF provider for anything beyond testnet.
interface IRandomness {
    /// @notice Request fresh randomness. Returns a request id.
    function requestRandomness() external returns (uint32 requestId);

    /// @notice True once the randomness for requestId can be fulfilled.
    function isReady(uint32 requestId) external view returns (bool);

    /// @notice Consume the randomness. Reverts if not ready or already fulfilled.
    function fulfillRandomness(uint32 requestId) external returns (bytes32 randomness);
}
