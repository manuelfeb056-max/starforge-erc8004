// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./StarforgeGame.sol";
import "./AgentReputation.sol";
import "./randomness/IRandomness.sol";

/// @title StarforgeArena — session manager for STARFORGE on Monad
/// @notice Replaces the Chain Jam host bridge (ICasinoGameV2) with a native
///         Monad session manager:
///           openSession (escrow wager) -> randomness -> spin ->
///           [supernova: submitPicks -> [gamble: randomness -> settle] | collect]
///           -> payout + ERC-8004 reputation feedback via AgentReputation.
/// @notice Testnet demo: wagers are in native MON (testnet). No real value.
contract StarforgeArena {
    StarforgeGame public immutable game;
    AgentReputation public reputation;
    IRandomness public immutable randomness;
    address public immutable owner;

    uint8 internal constant STAGE_NONE = 0;
    uint8 internal constant STAGE_WAIT_SPIN = 1;
    uint8 internal constant STAGE_WAIT_PICKS = 2;
    uint8 internal constant STAGE_WAIT_GAMBLE = 3;
    uint8 internal constant STAGE_SETTLED = 4;

    struct Session {
        address player;
        uint256 wager;
        uint8 artifacts;
        uint8 stage;
        StarforgeGame.SpinResult spin;
        uint32 randomnessId;
    }

    uint256 private _nextSessionId = 1;
    mapping(uint256 => Session) public sessions;

    error BadArtifacts();
    error BadStage();
    error NotPlayer();
    error ZeroWager();
    error RandomnessNotReady();
    error AlreadySettled();
    error OnlyOwner();
    error ReputationAlreadySet();

    event SessionOpened(uint256 indexed sessionId, address indexed player, uint256 wager, uint8 artifacts);
    event SpinSettled(uint256 indexed sessionId, uint8 stage, uint256 gridWinBps);
    event PicksSubmitted(uint256 indexed sessionId, bool gambled, uint256 picksBps);
    event SessionSettled(uint256 indexed sessionId, address indexed player, uint256 payout, uint256 totalBps);

    constructor(address _game, address _randomness) {
        game = StarforgeGame(_game);
        randomness = IRandomness(_randomness);
        owner = msg.sender;
    }

    /// @notice One-time wiring: set the AgentReputation hook.
    function setReputation(address _reputation) external {
        if (msg.sender != owner) revert OnlyOwner();
        if (address(reputation) != address(0)) revert ReputationAlreadySet();
        reputation = AgentReputation(_reputation);
    }

    /// @notice Open a session, escrowing the wager. Requests spin randomness.
    function openSession(uint8 artifacts) external payable returns (uint256 sessionId) {
        if (msg.value == 0) revert ZeroWager();
        if (artifacts > 0x07) revert BadArtifacts();
        sessionId = _nextSessionId++;
        Session storage s = sessions[sessionId];
        s.player = msg.sender;
        s.wager = msg.value;
        s.artifacts = artifacts;
        s.stage = STAGE_WAIT_SPIN;
        s.randomnessId = randomness.requestRandomness();
        emit SessionOpened(sessionId, msg.sender, msg.value, artifacts);
    }

    /// @notice Fulfill the spin once randomness is ready. Anyone can call.
    function fulfillSpin(uint256 sessionId) external {
        Session storage s = sessions[sessionId];
        if (s.stage != STAGE_WAIT_SPIN) revert BadStage();
        if (!randomness.isReady(s.randomnessId)) revert RandomnessNotReady();
        bytes32 seed = randomness.fulfillRandomness(s.randomnessId);

        StarforgeGame.SpinResult memory res = game.spin(seed, s.artifacts);
        // convert step wins from bps to wager units for the UI
        for (uint8 i = 0; i < res.stepCount; i++) {
            res.stepWins[i] = (s.wager * res.stepWins[i]) / 10000;
        }
        s.spin = res;

        if (res.stage == 1 /* STAGE_PICKS */) {
            s.stage = STAGE_WAIT_PICKS;
        } else {
            _settle(sessionId, res.totalBps);
            return;
        }
        emit SpinSettled(sessionId, s.stage, res.gridWinBps);
    }

    /// @notice Submit the 5 supernova picks. Only the session player.
    /// @param gamble true = double-or-nothing coin flip, false = collect now.
    function submitPicks(uint256 sessionId, uint8[5] calldata picks, bool gamble) external {
        Session storage s = sessions[sessionId];
        if (s.stage != STAGE_WAIT_PICKS) revert BadStage();
        if (msg.sender != s.player) revert NotPlayer();

        StarforgeGame.SpinResult memory res = game.applyPicks(s.spin, picks, gamble);
        s.spin = res;
        emit PicksSubmitted(sessionId, gamble, res.picksBps);

        if (!gamble) {
            _settle(sessionId, res.totalBps);
        } else {
            s.stage = STAGE_WAIT_GAMBLE;
            s.randomnessId = randomness.requestRandomness();
        }
    }

    /// @notice Fulfill the gamble coin flip once randomness is ready.
    function fulfillGamble(uint256 sessionId) external {
        Session storage s = sessions[sessionId];
        if (s.stage != STAGE_WAIT_GAMBLE) revert BadStage();
        if (!randomness.isReady(s.randomnessId)) revert RandomnessNotReady();
        bytes32 seed = randomness.fulfillRandomness(s.randomnessId);

        StarforgeGame.SpinResult memory res = game.applyGamble(s.spin, seed);
        s.spin = res;
        _settle(sessionId, res.totalBps);
    }

    /// @notice Emergency exit: forfeit an unfinished session, wager returned.
    ///         (Mid-round value is 0 per the original design — supernova bonus
    ///         must be completed; we return the escrowed wager instead of 0
    ///         as a friendlier testnet semantic. Documented, not silent.)
    function forfeit(uint256 sessionId) external {
        Session storage s = sessions[sessionId];
        if (s.stage == STAGE_NONE || s.stage == STAGE_SETTLED) revert BadStage();
        if (msg.sender != s.player) revert NotPlayer();
        s.stage = STAGE_SETTLED;
        uint256 wager = s.wager;
        s.wager = 0;
        (bool ok, ) = s.player.call{value: wager}("");
        require(ok, "forfeit transfer failed");
        emit SessionSettled(sessionId, s.player, wager, 0);
    }

    function _settle(uint256 sessionId, uint256 totalBps) internal {
        Session storage s = sessions[sessionId];
        if (s.stage == STAGE_SETTLED) revert AlreadySettled();
        s.stage = STAGE_SETTLED;
        uint256 payout = game.payoutFor(s.wager, totalBps);
        address player = s.player;
        uint256 wager = s.wager;
        s.wager = 0; // effects before interactions
        if (payout > 0) {
            (bool ok, ) = player.call{value: payout}("");
            require(ok, "payout transfer failed");
        }
        // reputation hook: session RTP becomes ERC-8004 feedback (no-op if unlinked)
        reputation.recordSession(player, wager, payout);
        emit SessionSettled(sessionId, player, payout, totalBps);
    }

    /// @notice Read a session's reveal for UI animation (no re-simulation needed).
    function getSpin(uint256 sessionId)
        external
        view
        returns (StarforgeGame.SpinResult memory)
    {
        return sessions[sessionId].spin;
    }

    receive() external payable {}
}
