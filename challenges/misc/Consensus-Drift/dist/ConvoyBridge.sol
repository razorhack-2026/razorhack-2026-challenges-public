// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ConvoyBridge
/// @notice On-chain light client for RazerPowerCo's convoy ledger. Anyone may relay a
///         convoy block; the bridge finalizes it once it carries a supermajority of
///         distinct authority attestations and enough proof-of-work, then releases the
///         sealed salvage record it commits to.
/// @dev    The authority (validator) set is fixed at genesis and never read from relayed
///         data. Attestations are raw-digest secp256k1 signatures, verified with ecrecover.
contract ConvoyBridge {
    // --- genesis authority set -------------------------------------------------
    mapping(address => bool) public isValidator;
    uint256 public immutable validatorCount;
    uint256 public immutable threshold;          // required distinct supermajority

    // --- finalized state -------------------------------------------------------
    uint256 public finalizedHeight;              // height of the last finalized checkpoint
    bytes32 public finalizedHash;                // header hash of the last finalized block
    bytes32 public finalizedRoot;                // state root of the last finalized checkpoint

    // --- challenge target ------------------------------------------------------
    bytes32 public constant UNLOCK_RECORD = keccak256("SALVAGE:manifest:RZR-9");
    uint256 public immutable powTarget;          // finalized header keccak must be < this
    bool public solved;

    struct Header {
        uint256 height;
        bytes32 parent;       // must extend the current finalized tip
        bytes32 stateRoot;    // the block's state root
        bytes32 recordHash;   // commitment to the block's salvage record
        uint256 timestamp;
        bytes32 extra;
        uint256 nonce;
    }

    struct Att { uint8 v; bytes32 r; bytes32 s; }

    event Finalized(uint256 indexed height, bytes32 headerHash, bytes32 stateRoot);
    event Unlocked(uint256 indexed height);

    constructor(
        address[] memory validators,
        uint256 _threshold,
        uint256 _finalizedHeight,
        bytes32 _finalizedHash,
        uint256 _powTarget
    ) {
        uint256 n;
        for (uint256 i = 0; i < validators.length; i++) {
            if (!isValidator[validators[i]]) {
                isValidator[validators[i]] = true;
                n++;
            }
        }
        validatorCount = n;
        threshold = _threshold;
        finalizedHeight = _finalizedHeight;
        finalizedHash = _finalizedHash;
        powTarget = _powTarget;
    }

    /// @notice keccak of the 224-byte header preimage, used for the PoW check and as the
    ///         block's canonical hash once finalized.
    function headerHash(Header calldata h) public pure returns (bytes32) {
        return keccak256(
            abi.encode(h.height, h.parent, h.stateRoot, h.recordHash, h.timestamp, h.extra, h.nonce)
        );
    }

    /// @notice The finality digest an authority signs to attest a (height, root) checkpoint.
    function attestationDigest(uint256 height, bytes32 stateRoot) public pure returns (bytes32) {
        return keccak256(abi.encode(height, stateRoot));
    }

    /// @notice Relay and finalize a convoy block.
    /// @param h           the block header being finalized
    /// @param attestedRoot the checkpoint state root the authorities attested to
    /// @param atts        authority attestations backing this checkpoint
    function submitBlock(Header calldata h, bytes32 attestedRoot, Att[] calldata atts) external {
        require(h.height > finalizedHeight, "stale: not ahead of finalized tip");
        require(h.parent == finalizedHash, "orphan: must extend finalized tip");
        require(uint256(headerHash(h)) < powTarget, "work: header below difficulty target");

        bytes32 digest = attestationDigest(h.height, attestedRoot);

        address last = address(0);
        uint256 weight;
        for (uint256 i = 0; i < atts.length; i++) {
            address signer = ecrecover(digest, atts[i].v, atts[i].r, atts[i].s);
            require(signer != address(0), "sig: invalid");
            require(isValidator[signer], "sig: not an authority");
            require(uint160(signer) > uint160(last), "sig: unsorted or duplicate signer");
            last = signer;
            weight++;
        }
        require(weight >= threshold, "quorum: below supermajority");

        finalizedHeight = h.height;
        finalizedHash = headerHash(h);
        finalizedRoot = attestedRoot;
        emit Finalized(h.height, finalizedHash, attestedRoot);

        if (h.recordHash == UNLOCK_RECORD) {
            solved = true;
            emit Unlocked(h.height);
        }
    }
}
