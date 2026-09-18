// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/IERC8004.sol";

/// @title AgentReputation — bridges STARFORGE gameplay to ERC-8004 reputation
/// @notice Flow:
///   1. An agent owner calls linkAgent(agentId). We verify ownership via the
///      Identity Registry (ownerOf) or the verified agentWallet.
///   2. After every settled session, StarforgeArena calls recordSession(...).
///   3. We post per-session feedback to the ERC-8004 Reputation Registry:
///      value = session RTP in bps (payout*10000/wager), tag1 = "starforge",
///      tag2 = "session". Aggregation (lifetime RTP, win rate, leaderboard)
///      happens off-chain via getSummary / event indexing — the intended
///      ERC-8004 pattern: raw signals on-chain, scoring off-chain.
/// @notice The Arena contract is the feedback *client*: feedback is
///         cryptographically attributable to gameplay that really happened.
contract AgentReputation {
    IERC8004Identity public immutable identityRegistry;
    IERC8004Reputation public immutable reputationRegistry;
    address public arena;
    address public immutable owner;

    string public constant TAG_GAME = "starforge";
    string public constant TAG_SESSION = "session";

    /// @notice player wallet => ERC-8004 agentId (0 = not linked)
    mapping(address => uint256) public walletToAgent;
    /// @notice lifetime stats per agentId (mirrors on-chain feedback)
    mapping(uint256 => uint256) public agentSessions;
    mapping(uint256 => uint256) public agentWagered;
    mapping(uint256 => uint256) public agentPaid;

    error OnlyArena();
    error OnlyOwner();
    error NotAgentOwner();
    error AlreadyLinked();
    error ArenaAlreadySet();

    event AgentLinked(address indexed wallet, uint256 indexed agentId);
    event SessionRecorded(uint256 indexed agentId, uint256 rtpBps, uint256 payout);

    modifier onlyArena() {
        if (msg.sender != arena) revert OnlyArena();
        _;
    }

    constructor(address _identityRegistry, address _reputationRegistry) {
        identityRegistry = IERC8004Identity(_identityRegistry);
        reputationRegistry = IERC8004Reputation(_reputationRegistry);
        owner = msg.sender;
    }

    /// @notice One-time wiring: set the Arena authorized to record sessions.
    function setArena(address _arena) external {
        if (msg.sender != owner) revert OnlyOwner();
        if (arena != address(0)) revert ArenaAlreadySet();
        arena = _arena;
    }

    /// @notice Link the caller's wallet to an ERC-8004 agent identity.
    /// @dev Accepts ownerOf(agentId) == msg.sender OR the verified agentWallet.
    function linkAgent(uint256 agentId) external {
        if (walletToAgent[msg.sender] != 0) revert AlreadyLinked();
        bool isOwner = identityRegistry.ownerOf(agentId) == msg.sender;
        bool isWallet = identityRegistry.getAgentWallet(agentId) == msg.sender;
        if (!isOwner && !isWallet) revert NotAgentOwner();
        walletToAgent[msg.sender] = agentId;
        emit AgentLinked(msg.sender, agentId);
    }

    /// @notice Record one settled session as reputation feedback. Only the Arena.
    /// @param player the session's player wallet
    /// @param wager wager amount (same units as payout)
    /// @param payout final payout (0 on full loss)
    function recordSession(address player, uint256 wager, uint256 payout)
        external
        onlyArena
    {
        uint256 agentId = walletToAgent[player];
        if (agentId == 0) return; // unlinked players simply don't earn reputation

        uint256 rtpBps = wager == 0 ? 0 : (payout * 10000) / wager;
        // cap the int128 range defensively (1000x max payout = 10_000_000 bps)
        int128 value = rtpBps > uint256(uint128(type(int128).max))
            ? type(int128).max
            : int128(uint128(rtpBps));

        _postFeedback(agentId, value);

        agentSessions[agentId] += 1;
        agentWagered[agentId] += wager;
        agentPaid[agentId] += payout;
        emit SessionRecorded(agentId, rtpBps, payout);
    }

    /// @dev Split out to keep recordSession's stack shallow (string tags are
    ///      dynamic types; one external call frame per function avoids
    ///      "stack too deep" on the legacy codegen pipeline).
    function _postFeedback(uint256 agentId, int128 value) internal {
        reputationRegistry.giveFeedback(
            agentId,
            value,
            0, // valueDecimals: rtpBps is already integer bps
            TAG_GAME,
            TAG_SESSION,
            "", // endpoint: none (feedback client is the Arena contract itself)
            "", // feedbackURI: none
            bytes32(0)
        );
    }

    /// @notice Lifetime RTP (bps) for an agent, from our own accounting.
    function lifetimeRtpBps(uint256 agentId) external view returns (uint256) {
        uint256 w = agentWagered[agentId];
        return w == 0 ? 0 : (agentPaid[agentId] * 10000) / w;
    }
}
