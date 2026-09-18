// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./IRandomness.sol";

/// @title BlockhashRandomness — TESTNET-ONLY randomness via future blockhash
/// @notice NOT safe for mainnet (miner/validator influence). For the Monad
///         testnet demo it is acceptable and fully transparent. Anything with
///         real value must plug a VRF provider behind IRandomness instead.
contract BlockhashRandomness is IRandomness {
    uint32 private _nextId = 1;
    /// @notice requestId => target block whose hash becomes the randomness
    mapping(uint32 => uint256) public targetBlock;
    mapping(uint32 => bool) public fulfilled;

    error NotReady();
    error AlreadyFulfilled();
    error UnknownRequest();

    /// @notice Randomness is the hash of the block 3 blocks after the request,
    ///         so the requester cannot know it at request time.
    function requestRandomness() external override returns (uint32 requestId) {
        requestId = _nextId++;
        targetBlock[requestId] = block.number + 3;
    }

    function isReady(uint32 requestId) external view override returns (bool) {
        if (targetBlock[requestId] == 0) revert UnknownRequest();
        if (fulfilled[requestId]) return false;
        return block.number > targetBlock[requestId];
    }

    function fulfillRandomness(uint32 requestId) external override returns (bytes32 randomness) {
        uint256 tb = targetBlock[requestId];
        if (tb == 0) revert UnknownRequest();
        if (fulfilled[requestId]) revert AlreadyFulfilled();
        if (block.number <= tb) revert NotReady();
        // blockhash only works for the last 256 blocks; testnet sessions are short-lived.
        randomness = blockhash(tb);
        require(randomness != bytes32(0), "blockhash expired");
        fulfilled[requestId] = true;
    }
}
