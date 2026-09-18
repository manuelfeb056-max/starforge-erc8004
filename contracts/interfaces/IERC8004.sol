// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title IERC8004Identity — minimal interface of the ERC-8004 Identity Registry
/// @notice Based on ERC-8004 (Trustless Agents) v1.0. Confirm exact ABI against
///         the deployed registry before mainnet use. See docs/ERC8004_NOTES.md.
interface IERC8004Identity {
    struct MetadataEntry {
        string metadataKey;
        bytes metadataValue;
    }

    /// @notice Mint a new agent NFT bound to an agentURI (registration file).
    function register(string calldata agentURI, MetadataEntry[] calldata metadata)
        external
        returns (uint256 agentId);

    /// @notice Mint a new agent NFT without URI (set later via setAgentURI).
    function register() external returns (uint256 agentId);

    /// @notice Update the agent's registration-file URI.
    function setAgentURI(uint256 agentId, string calldata newURI) external;

    /// @notice Set an on-chain metadata key/value for an agent.
    function setMetadata(uint256 agentId, string calldata key, bytes calldata value) external;

    /// @notice Read an on-chain metadata value.
    function getMetadata(uint256 agentId, string calldata key)
        external
        view
        returns (bytes memory);

    /// @notice ERC-721 owner of the agent identity.
    function ownerOf(uint256 tokenId) external view returns (address);

    /// @notice Verified payment wallet of the agent (EIP-712 verified).
    function getAgentWallet(uint256 agentId) external view returns (address);

    event Registered(uint256 indexed agentId, string agentURI, address indexed owner);
    event URIUpdated(uint256 indexed agentId, string newURI, address indexed updatedBy);
    event MetadataSet(uint256 indexed agentId, string indexed metadataKey, bytes metadataValue);
}

/// @title IERC8004Reputation — minimal interface of the ERC-8004 Reputation Registry
/// @notice Feedback is a signed fixed-point value + decimals, tagged for filtering.
///         Raw signals live on-chain; aggregation happens off-chain (getSummary).
///         Signatures verified against the official erc-8004-contracts
///         (ReputationRegistryUpgradeable): tags are STRINGS, not bytes32.
interface IERC8004Reputation {
    /// @notice Post feedback about an agent. Only value/valueDecimals are required.
    /// @param value signed fixed-point score (e.g. 9750 with 2 decimals = 97.50)
    /// @param valueDecimals decimals of value (0-18)
    /// @param tag1 free-form tag string, e.g. "starforge"
    /// @param tag2 free-form tag string, e.g. "session" or "lifetime"
    function giveFeedback(
        uint256 agentId,
        int128 value,
        uint8 valueDecimals,
        string calldata tag1,
        string calldata tag2,
        string calldata endpoint,
        string calldata feedbackURI,
        bytes32 feedbackHash
    ) external;

    /// @notice Revoke one of the caller's own feedback entries (1-indexed).
    function revokeFeedback(uint256 agentId, uint64 feedbackIndex) external;

    /// @notice Read one feedback entry (1-indexed).
    function readFeedback(uint256 agentId, address clientAddress, uint64 feedbackIndex)
        external
        view
        returns (
            int128 value,
            uint8 valueDecimals,
            string memory tag1,
            string memory tag2,
            bool isRevoked
        );

    /// @notice Aggregated score across a set of clients' feedback.
    function getSummary(
        uint256 agentId,
        address[] calldata clientAddresses,
        string calldata tag1,
        string calldata tag2
    ) external view returns (uint64 count, int128 summaryValue, uint8 summaryValueDecimals);

    event NewFeedback(
        uint256 indexed agentId,
        address indexed clientAddress,
        uint64 feedbackIndex,
        int128 value,
        uint8 valueDecimals,
        string indexed indexedTag1,
        string tag1,
        string tag2,
        string endpoint,
        string feedbackURI,
        bytes32 feedbackHash
    );
}
