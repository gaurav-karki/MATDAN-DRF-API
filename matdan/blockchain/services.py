"""
Blockchain Service Module

This is the "translator" between Django and Ethereum.
It converts Django operations into blockchain transactions.
"""

import json
import logging
from typing import Optional, Dict, Any, Tuple, List
from pathlib import Path

from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account
from django.conf import settings

logger = logging.getLogger('blockchain')


class BlockchainConnectionError(Exception):
    """Raised when we can't connect to the blockchain."""
    pass


class ContractNotLoadedError(Exception):
    """Raised when the smart contract isn't loaded."""
    pass


class BlockchainService:
    """
    Service class for interacting with the Voting smart contract.
    """
    #Load config from Django settings, connects to blockchain, loads accounts and contract. Logs progress
    def __init__(self):
        """Initialize connection to blockchain."""
        logger.info("Initializing BlockchainService...")
        
        self.config = settings.BLOCKCHAIN_CONFIG # Lodas blockchain config from Django settings
        self._connect_to_blockchain()
        self._load_account()
        self._load_contract()
        
        logger.info("BlockchainService initialized successfully!")
    
    # Connects to Ethereum node(Ganache), Checks connection, logs chainID & Block number.
    def _connect_to_blockchain(self) -> None:
        """Connect to the Ethereum node (Ganache)."""
        provider_url = self.config['PROVIDER_URL']
        logger.info(f"Connecting to blockchain at {provider_url}...")
        
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        
        if not self.w3.is_connected():
            error_msg = f"Cannot connect to blockchain at {provider_url}"
            logger.error(error_msg)
            raise BlockchainConnectionError(error_msg)
        
        chain_id = self.w3.eth.chain_id
        block_number = self.w3.eth.block_number
        logger.info(f"Connected! Chain ID: {chain_id}, Latest Block: {block_number}")
    
    # Loads Ethereum  account from private key and logs address and balance
    def _load_account(self) -> None:
        """Load the Ethereum account for signing transactions."""
        private_key = self.config['PRIVATE_KEY'] #settings.py
        
        if not private_key:
            logger.warning("No private key configured - read-only mode")
            self.account = None
            return
        
        self.account = Account.from_key(private_key)
        balance_wei = self.w3.eth.get_balance(self.account.address)
        balance_eth = self.w3.from_wei(balance_wei, 'ether')
        
        logger.info(f"Account loaded: {self.account.address}")
        logger.info(f"Account balance: {balance_eth} ETH")
    
    #
    def _load_contract(self) -> None:
        """Load the smart contract so we can interact with it."""
        contract_address = self.config['CONTRACT_ADDRESS']
        
        if not contract_address:
            logger.warning("No contract address configured - deploy contract first")
            self.contract = None
            return
        
        abi_path = Path(settings.BASE_DIR) / 'blockchain' / 'contracts' / 'VotingContract.json'
        
        try:
            with open(abi_path, 'r', encoding='utf-8') as f:
                contract_data = json.load(f)
            
            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(contract_address),
                abi=contract_data['abi']
            )
            
            logger.info(f"Contract loaded at: {contract_address}")
            
        except FileNotFoundError:
            logger.error(f"ABI file not found at {abi_path}")
            self.contract = None
        except Exception as e:
            logger.error(f"Failed to load contract: {e}")
            self.contract = None
    
    def _ensure_contract_loaded(self) -> None:
        """Check that contract is loaded, raise error if not."""
        if not self.contract:
            raise ContractNotLoadedError(
                "Smart contract not loaded. "
                "Make sure VOTING_CONTRACT_ADDRESS is set in .env"
            )
    
    def _ensure_account_loaded(self) -> None:
        """Check that account is loaded, raise error if not."""
        if not self.account:
            raise ContractNotLoadedError(
                "No account configured. "
                "Make sure BLOCKCHAIN_PRIVATE_KEY is set in .env"
            )
    
    # =========================================================================
    # NEW: Required methods for views.py
    # =========================================================================
    
    def is_connected(self) -> bool:
        """
        Check if connected to blockchain.
        
        Returns:
            True if connected, False otherwise
        """
        return self.w3 is not None and self.w3.is_connected()
    
    def cast_vote(
        self,
        election_id: str,
        candidate_blockchain_id: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Cast a vote on the blockchain.
        
        Args:
            election_id: UUID of the election (as string)
            candidate_blockchain_id: The candidate's blockchain ID (integer)
            
        Returns:
            Tuple of (success, {tx_hash, vote_hash, block_number, gas_used} or {error})
        """
        self._ensure_contract_loaded() # Ensure contract is loaded before proceeding
        self._ensure_account_loaded() # Ensure accounts are loaded before proceeding
        
        logger.info(f"Casting vote: election={election_id}, candidate={candidate_blockchain_id}")
        
        try:
            # Prepare the contract function call
            function = self.contract.functions.castVote(
                election_id,
                candidate_blockchain_id
            )
            # Get the current nounce for the account(number of transaction sent)
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            #Build the transaction dictionary
            tx = function.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.config['CHAIN_ID']
            })
            # Sign the transaction with the private key
            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                self.config['PRIVATE_KEY']
            )
            # Send the transaction to the blockchain 
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            logger.info(f"Vote transaction sent: {tx_hash.hex()}")
            # Wait for the transaction to  be mined and get the receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                vote_hash = None
                try:
                    # Extract the vote hash form the VoteCast event, if present
                    vote_cast_events = self.contract.events.VoteCast().process_receipt(receipt)
                    if vote_cast_events:
                        vote_hash = vote_cast_events[0]['args']['voteHash'].hex()
                except Exception as e:
                    logger.warning(f"Could not extract vote hash: {e}")
                
                logger.info(f"Vote successful! TX: {tx_hash.hex()}")
                
                return True, {
                    'tx_hash': tx_hash.hex(),
                    'vote_hash': vote_hash,
                    'block_number': receipt['blockNumber'],
                    'gas_used': receipt['gasUsed']
                }
            else:
                return False, {"error": "Transaction reverted on blockchain"}
                
        except ContractLogicError as e:
            error_msg = str(e)
            logger.error(f"Contract error: {error_msg}")
            # Handle specific contract errors
            if "already voted" in error_msg.lower():
                return False, {"error": "You have already voted in this election"}
            elif "not active" in error_msg.lower():
                return False, {"error": "Election is not active on blockchain"}
            elif "does not exist" in error_msg.lower():
                return False, {"error": "Candidate does not exist on blockchain"}
            
            return False, {"error": error_msg}
            
        except Exception as e:
            logger.error(f"Vote casting failed: {e}")
            return False, {"error": str(e)}
    
    # =========================================================================
    # Existing methods (keep all your current methods below)
    # =========================================================================
    
    def _send_transaction(self, function) -> Tuple[bool, str]:
        """Build, sign, and send a transaction to the blockchain."""
        self._ensure_account_loaded()
        
        try:
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            
            tx = function.build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.config['CHAIN_ID']
            })
            
            signed_tx = self.w3.eth.account.sign_transaction(
                tx, 
                self.config['PRIVATE_KEY']
            )
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            
            if receipt['status'] == 1:
                return True, tx_hash.hex()
            else:
                return False, "Transaction was reverted by the contract"
                
        except ContractLogicError as e:
            logger.error(f"Contract error: {e}")
            return False, str(e)
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False, str(e)
    
    def create_election(self, election_id: str, title: str) -> Tuple[bool, str]:
        """Create a new election on the blockchain."""
        self._ensure_contract_loaded()
        logger.info(f"Creating election: {title} (ID: {election_id})")
        function = self.contract.functions.createElection(election_id, title)
        return self._send_transaction(function)
    
    def add_candidate(
        self, 
        election_id: str, 
        candidate_id: int, 
        name: str, 
        party: str
    ) -> Tuple[bool, str]:
        """Add a candidate to an election on the blockchain."""
        self._ensure_contract_loaded()
        logger.info(f"Adding candidate: {name} ({party}) to election {election_id}")
        function = self.contract.functions.addCandidate(
            election_id, candidate_id, name, party
        )
        return self._send_transaction(function)
    
    def set_election_status(self, election_id: str, is_active: bool) -> Tuple[bool, str]:
        """Activate or deactivate an election."""
        self._ensure_contract_loaded()
        status_text = "ACTIVE" if is_active else "INACTIVE"
        logger.info(f"Setting election {election_id} to {status_text}")
        function = self.contract.functions.setElectionStatus(election_id, is_active)
        return self._send_transaction(function)
    
    def get_election(self, election_id: str) -> Optional[Dict[str, Any]]:
        """Get election details from the blockchain."""
        self._ensure_contract_loaded()
        try:
            result = self.contract.functions.getElection(election_id).call()
            logger.info(f"Fetching election from blockchain with id: {election_id}")
            return {
                'id': result[0],
                'title': result[1],
                'is_active': result[2],
                'candidate_count': result[3]
            }
    
        except Exception as e:
            logger.error(f"Failed to get election: {e}")
            return None
    
    def get_candidate(self, election_id: str, candidate_id: int) -> Optional[Dict[str, Any]]:
        """Get candidate details and vote count from blockchain."""
        self._ensure_contract_loaded()
        try:
            result = self.contract.functions.getCandidate(election_id, candidate_id).call()
            return {
                'id': result[0],
                'name': result[1],
                'party': result[2],
                'vote_count': result[3]
            }
        except Exception as e:
            logger.error(f"Failed to get candidate: {e}")
            return None
    
    def get_election_results(self, election_id: str, candidate_ids: List[int]) -> List[Dict[str, Any]]:
        """Get vote counts for all candidates in an election."""
        results = []
        for cid in candidate_ids:
            candidate = self.get_candidate(election_id, cid)
            if candidate:
                results.append(candidate)
        results.sort(key=lambda x: x['vote_count'], reverse=True)
        return results
    
    def check_if_voted(self, election_id: str, voter_address: str) -> bool:
        """Check if an address has already voted in an election."""
        self._ensure_contract_loaded()
        try:
            return self.contract.functions.checkIfVoted(
                election_id,
                Web3.to_checksum_address(voter_address)
            ).call()
        except Exception as e:
            logger.error(f"Failed to check vote status: {e}")
            return False
    
    def get_vote_hash(self, election_id: str, voter_address: str) -> Optional[str]:
        """Get the vote verification hash for a voter."""
        self._ensure_contract_loaded()
        try:
            vote_hash = self.contract.functions.getVoteHash(
                election_id,
                Web3.to_checksum_address(voter_address)
            ).call()
            return vote_hash.hex()
        except Exception as e:
            logger.error(f"Failed to get vote hash: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get blockchain connection status."""
        return {
            'connected': self.w3.is_connected() if self.w3 else False,
            'provider_url': self.config['PROVIDER_URL'],
            'chain_id': self.w3.eth.chain_id if self.w3 and self.w3.is_connected() else None,
            'latest_block': self.w3.eth.block_number if self.w3 and self.w3.is_connected() else None,
            'account_address': self.account.address if self.account else None,
            'contract_loaded': self.contract is not None,
            'contract_address': self.config['CONTRACT_ADDRESS'] or None
        }


# Singleton
_blockchain_service: Optional[BlockchainService] = None


def get_blockchain_service() -> BlockchainService:
    """Get or create the blockchain service singleton."""
    global _blockchain_service
    if _blockchain_service is None:
        _blockchain_service = BlockchainService()
    return _blockchain_service


def reset_blockchain_service() -> None:
    """Reset the singleton (useful for testing or reconnecting)."""
    global _blockchain_service
    _blockchain_service = None