// SPDX-License-Identifier: MIT
// This line specifies the license - MIT is open source

pragma solidity ^0.8.19;
// This specifies the Solidity compiler version to use

/**
 * @title VotingContract
 * @author Matdan Team
 * @notice This contract manages elections and votes on the Ethereum blockchain
 * @dev All election and vote data is stored immutably on-chain
 * 
 * ============== HOW THIS CONTRACT WORKS ==============
 * 
 * 1. SETUP PHASE:
 *    - Admin deploys the contract (becomes the owner)
 *    - Admin creates elections using createElection()
 *    - Admin adds candidates using addCandidate()
 *    - Admin activates the election using setElectionStatus()
 * 
 * 2. VOTING PHASE:
 *    - Voters call castVote() with their choice
 *    - Contract checks: election active? already voted? valid candidate?
 *    - If all checks pass, vote is recorded
 *    - Voter receives a unique hash as proof
 * 
 * 3. RESULTS PHASE:
 *    - Anyone can call view functions to see results
 *    - Results are transparent and verifiable
 * 
 * ====================================================
 */
contract VotingContract {
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                    DATA STRUCTURES                         ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Represents a candidate in an election
     * @dev Struct is like a custom data type with multiple fields
     * 
     * Example:
     * {
     *   id: 1,
     *   name: "John Doe",
     *   party: "Democratic Party",
     *   voteCount: 150
     * }
     */
    struct Candidate {
        uint256 id;           // Unique identifier (number)
        string name;          // Candidate's full name
        string party;         // Political party
        uint256 voteCount;    // Total votes received
    }
    
    /**
     * @notice Represents an election
     * @dev Stores election metadata
     * 
     * Example:
     * {
     *   id: "a037354c-ccbe-499d-b0af-4e37a74f41f1",
     *   title: "Presidential Election 2025",
     *   isActive: true,
     *   candidateCount: 5
     * }
     */
    struct Election {
        string id;              // UUID from Django (stored as string)
        string title;           // Election title/name
        bool isActive;          // Is voting currently open?
        uint256 candidateCount; // How many candidates
    }
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                    STATE VARIABLES                         ║
    // ║         (Data stored permanently on blockchain)            ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice The address that deployed this contract
     * @dev Only this address can perform admin functions
     * 
     * Think of it like: The person who created the contract is the admin
     */
    address public owner;
    
    /**
     * @notice Stores all elections
     * @dev Mapping is like a dictionary: election_id => Election
     * 
     * Example access: elections["uuid-here"] returns Election struct
     */
    mapping(string => Election) public elections;
    
    /**
     * @notice Stores all candidates for each election
     * @dev Nested mapping: election_id => candidate_id => Candidate
     * 
     * Example access: candidates["election-uuid"][1] returns Candidate #1
     */
    mapping(string => mapping(uint256 => Candidate)) public candidates;
    
    /**
     * @notice Tracks who has voted in which election
     * @dev Mapping: election_id => voter_address => has_voted (true/false)
     * 
     * This prevents double voting!
     * Example: hasVoted["election-uuid"][0x123...] = true means this address voted
     */
    mapping(string => mapping(address => bool)) public hasVoted;
    
    /**
     * @notice Stores vote verification hashes
     * @dev Mapping: election_id => voter_address => vote_hash
     * 
     * This allows voters to verify their vote was recorded
     */
    mapping(string => mapping(address => bytes32)) public voteHashes;
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                         EVENTS                             ║
    // ║     (Logs that are stored on blockchain for tracking)      ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Emitted when a new election is created
     * @dev Events are cheap to store and easy to search
     * 
     * When Django creates an election, we can listen for this event
     */
    event ElectionCreated(
        string indexed electionId,  // 'indexed' makes it searchable
        string title
    );
    
    /**
     * @notice Emitted when a candidate is added
     */
    event CandidateAdded(
        string indexed electionId,
        uint256 candidateId,
        string name,
        string party
    );
    
    /**
     * @notice Emitted when a vote is cast
     * @dev This is the most important event - proves voting happened
     */
    event VoteCast(
        string indexed electionId,
        address indexed voter,      // Who voted (wallet address)
        uint256 candidateId,        // Who they voted for
        bytes32 voteHash           // Unique proof hash
    );
    
    /**
     * @notice Emitted when election status changes
     */
    event ElectionStatusChanged(
        string indexed electionId,
        bool isActive
    );
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                       MODIFIERS                            ║
    // ║        (Reusable conditions for functions)                 ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Restricts function to contract owner only
     * @dev If non-owner calls, transaction reverts with error message
     * 
     * Usage: function doSomething() public onlyOwner { ... }
     */
    modifier onlyOwner() {
        require(
            msg.sender == owner, 
            "Access denied: Only contract owner can perform this action"
        );
        _; // This is where the actual function code runs
    }
    
    /**
     * @notice Ensures the election exists
     * @dev Checks if election ID is stored in our mapping
     */
    modifier electionExists(string memory _electionId) {
        require(
            bytes(elections[_electionId].id).length > 0,
            "Election not found: This election ID does not exist"
        );
        _;
    }
    
    /**
     * @notice Ensures the election is currently active
     * @dev Voting can only happen when isActive = true
     */
    modifier electionIsActive(string memory _electionId) {
        require(
            elections[_electionId].isActive,
            "Election closed: This election is not currently accepting votes"
        );
        _;
    }
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                      CONSTRUCTOR                           ║
    // ║        (Runs once when contract is deployed)               ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Initializes the contract
     * @dev Sets the deployer as the owner
     * 
     * msg.sender = the address that deployed this contract
     */
    constructor() {
        owner = msg.sender;
    }
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                   ADMIN FUNCTIONS                          ║
    // ║           (Only owner can call these)                      ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Creates a new election on the blockchain
     * @dev Called by Django after creating election in database
     * 
     * @param _electionId The UUID from Django's Election model
     * @param _title The election title
     * 
     * Example call: createElection("a037354c-ccbe-499d-b0af-4e37a74f41f1", "Presidential Election 2025")
     */
    function createElection(
        string memory _electionId,
        string memory _title
    ) public onlyOwner {
        // Check election doesn't already exist
        require(
            bytes(elections[_electionId].id).length == 0,
            "Election already exists: Cannot create duplicate election"
        );
        
        // Create the election
        elections[_electionId] = Election({
            id: _electionId,
            title: _title,
            isActive: false,    // Elections start inactive
            candidateCount: 0
        });
        
        // Emit event for tracking
        emit ElectionCreated(_electionId, _title);
    }
    
    /**
     * @notice Adds a candidate to an existing election
     * @dev Must be called before election is activated
     * 
     * @param _electionId The election UUID
     * @param _candidateId Numeric ID for the candidate
     * @param _name Candidate's name
     * @param _party Political party
     * 
     * Example: addCandidate("uuid", 1, "John Doe", "Democratic Party")
     */
    function addCandidate(
        string memory _electionId,
        uint256 _candidateId,
        string memory _name,
        string memory _party
    ) public onlyOwner electionExists(_electionId) {
        // Cannot add candidates to active election (fairness)
        require(
            !elections[_electionId].isActive,
            "Election active: Cannot add candidates while voting is open"
        );
        
        // Check candidate doesn't already exist
        require(
            candidates[_electionId][_candidateId].id == 0,
            "Candidate exists: This candidate ID is already used"
        );
        
        // Add the candidate
        candidates[_electionId][_candidateId] = Candidate({
            id: _candidateId,
            name: _name,
            party: _party,
            voteCount: 0
        });
        
        // Update candidate count
        elections[_electionId].candidateCount++;
        
        // Emit event
        emit CandidateAdded(_electionId, _candidateId, _name, _party);
    }
    
    /**
     * @notice Activates or deactivates an election
     * @dev Controls whether voting is open
     * 
     * @param _electionId The election UUID
     * @param _isActive true to open voting, false to close
     */
    function setElectionStatus(
        string memory _electionId,
        bool _isActive
    ) public onlyOwner electionExists(_electionId) {
        elections[_electionId].isActive = _isActive;
        emit ElectionStatusChanged(_electionId, _isActive);
    }
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                    VOTING FUNCTION                         ║
    // ║              (The main voting logic)                       ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Cast a vote in an election
     * @dev This is the core function voters use
     * 
     * @param _electionId The election to vote in
     * @param _candidateId The candidate to vote for
     * @return voteHash A unique hash proving the vote
     * 
     * SECURITY CHECKS:
     * 1. Election must exist (electionExists modifier)
     * 2. Election must be active (electionIsActive modifier)
     * 3. Voter must not have voted before (hasVoted check)
     * 4. Candidate must exist (candidates check)
     */
    function castVote(
        string memory _electionId,
        uint256 _candidateId
    ) 
        public 
        electionExists(_electionId) 
        electionIsActive(_electionId) 
        returns (bytes32) 
    {
        // SECURITY CHECK 1: Prevent double voting
        // msg.sender is the address calling this function (the voter)
        require(
            !hasVoted[_electionId][msg.sender],
            "Already voted: You have already cast your vote in this election"
        );
        
        // SECURITY CHECK 2: Verify candidate exists
        // We check if the candidate ID matches (non-zero means it was set)
        require(
            candidates[_electionId][_candidateId].id == _candidateId && _candidateId > 0,
            "Invalid candidate: This candidate does not exist"
        );
        
        // RECORD THE VOTE
        // Increment the candidate's vote count
        candidates[_electionId][_candidateId].voteCount++;
        
        // Mark this voter as having voted
        hasVoted[_electionId][msg.sender] = true;
        
        // CREATE VOTE HASH (for verification)
        // keccak256 is a cryptographic hash function
        // We combine multiple values to create a unique hash
        bytes32 voteHash = keccak256(abi.encodePacked(
            _electionId,           // Which election
            msg.sender,            // Who voted (wallet address)
            _candidateId,          // Who they voted for
            block.timestamp,       // When they voted
            block.number          // Which block (adds uniqueness)
        ));
        
        // Store the hash for later verification
        voteHashes[_electionId][msg.sender] = voteHash;
        
        // Emit event (this is stored in blockchain logs)
        emit VoteCast(_electionId, msg.sender, _candidateId, voteHash);
        
        // Return the hash as a receipt
        return voteHash;
    }
    
    // ╔═══════════════════════════════════════════════════════════╗
    // ║                    VIEW FUNCTIONS                          ║
    // ║          (Read-only, FREE to call - no gas)                ║
    // ╚═══════════════════════════════════════════════════════════╝
    
    /**
     * @notice Get election details
     * @dev View function = no gas cost
     * 
     * @param _electionId The election UUID
     * @return id The election ID
     * @return title The election title
     * @return isActive Whether voting is open
     * @return candidateCount Number of candidates
     */
    function getElection(string memory _electionId) 
        public 
        view 
        returns (
            string memory id,
            string memory title,
            bool isActive,
            uint256 candidateCount
        ) 
    {
        Election memory e = elections[_electionId];
        return (e.id, e.title, e.isActive, e.candidateCount);
    }
    
    /**
     * @notice Get candidate details including vote count
     * @dev This is how we get election results
     * 
     * @param _electionId The election UUID
     * @param _candidateId The candidate ID
     * @return id Candidate ID
     * @return name Candidate name
     * @return party Political party
     * @return voteCount Number of votes received
     */
    function getCandidate(
        string memory _electionId,
        uint256 _candidateId
    ) 
        public 
        view 
        returns (
            uint256 id,
            string memory name,
            string memory party,
            uint256 voteCount
        ) 
    {
        Candidate memory c = candidates[_electionId][_candidateId];
        return (c.id, c.name, c.party, c.voteCount);
    }
    
    /**
     * @notice Check if an address has voted
     * @dev Useful for UI to show "You've already voted" message
     * 
     * @param _electionId The election UUID
     * @param _voter The wallet address to check
     * @return bool True if the address has voted
     */
    function checkIfVoted(
        string memory _electionId,
        address _voter
    ) public view returns (bool) {
        return hasVoted[_electionId][_voter];
    }
    
    /**
     * @notice Get the vote verification hash
     * @dev Voters can use this to prove they voted
     * 
     * @param _electionId The election UUID
     * @param _voter The wallet address
     * @return bytes32 The vote hash (0x0 if not voted)
     */
    function getVoteHash(
        string memory _electionId,
        address _voter
    ) public view returns (bytes32) {
        return voteHashes[_electionId][_voter];
    }
    
    /**
     * @notice Get the contract owner address
     * @dev Useful for verification
     */
    function getOwner() public view returns (address) {
        return owner;
    }
}