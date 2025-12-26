"""
Smart Contract Deployment Script

This script:
1. Compiles the VotingContract.sol
2. Deploys it to the blockchain (Ganache)
3. Saves the contract address

Usage:
    python manage.py shell
    >>> from blockchain.deploy_contract import deploy_contract
    >>> contract_address = deploy_contract()
"""

import json
from pathlib import Path
from solcx import compile_standard, install_solc, get_installed_solc_versions
from web3 import Web3
from eth_account import Account
from django.conf import settings


def deploy_contract():
    """
    Compile and deploy the VotingContract to the blockchain.
    
    Returns:
        str: The deployed contract address
    """
    print("=" * 60)
    print("SMART CONTRACT DEPLOYMENT")
    print("=" * 60)
    
    # ============ STEP 1: Install/Check Solidity Compiler ============
    print("\n[1/7] Checking Solidity compiler...")
    
    solc_version = '0.8.19'
    installed_versions = get_installed_solc_versions()
    
    if solc_version not in [str(v) for v in installed_versions]:
        print(f"      Installing solc {solc_version}...")
        install_solc(solc_version)
        print(f"      ✓ solc {solc_version} installed")
    else:
        print(f"      ✓ solc {solc_version} already installed")
    
    # ============ STEP 2: Read Contract Source ============
    print("\n[2/7] Reading contract source code...")
    
    # Get the path to the contract file
    base_dir = Path(__file__).parent
    contract_path = base_dir / 'contracts' / 'VotingContract.sol'
    
    if not contract_path.exists():
        print(f"      ERROR: Contract not found at {contract_path}")
        return None
    
    # IMPORTANT: Use encoding='utf-8' to handle special characters
    try:
        with open(contract_path, 'r', encoding='utf-8') as f:
            contract_source = f.read()
        print(f"      ✓ Read {len(contract_source)} characters")
    except UnicodeDecodeError:
        # Fallback: try reading with errors ignored
        print("      Retrying with error handling...")
        with open(contract_path, 'r', encoding='utf-8', errors='ignore') as f:
            contract_source = f.read()
        print(f"      ✓ Read {len(contract_source)} characters (with fallback)")
    
    # ============ STEP 3: Compile Contract ============
    print("\n[3/7] Compiling contract...")
    
    try:
        compiled = compile_standard(
            {
                "language": "Solidity",
                "sources": {
                    "VotingContract.sol": {
                        "content": contract_source
                    }
                },
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["abi", "metadata", "evm.bytecode", "evm.sourceMap"]
                        }
                    },
                    "optimizer": {
                        "enabled": True,
                        "runs": 200
                    }
                }
            },
            solc_version=solc_version
        )
        print("      ✓ Contract compiled successfully")
    except Exception as e:
        print(f"      ERROR: Compilation failed: {e}")
        return None
    
    # Extract ABI and Bytecode
    contract_data = compiled['contracts']['VotingContract.sol']['VotingContract']
    abi = contract_data['abi']
    bytecode = contract_data['evm']['bytecode']['object']
    
    print(f"      ✓ ABI has {len(abi)} entries")
    print(f"      ✓ Bytecode length: {len(bytecode)} chars")
    
    # ============ STEP 4: Save ABI to JSON ============
    print("\n[4/7] Saving ABI to VotingContract.json...")
    
    json_path = base_dir / 'contracts' / 'VotingContract.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'abi': abi,
            'bytecode': bytecode
        }, f, indent=2)
    
    print(f"      ✓ Saved to VotingContract.json")
    
    # ============ STEP 5: Connect to Blockchain ============
    print("\n[5/7] Connecting to blockchain...")
    
    config = settings.BLOCKCHAIN_CONFIG
    provider_url = config.get('PROVIDER_URL', 'http://127.0.0.1:8545')
    
    w3 = Web3(Web3.HTTPProvider(provider_url))
    
    if not w3.is_connected():
        print(f"      ERROR: Cannot connect to {provider_url}")
        print("      Make sure Ganache is running!")
        return None
    
    print(f"      ✓ Connected to {provider_url}")
    print(f"      ✓ Chain ID: {w3.eth.chain_id}")
    print(f"      ✓ Latest block: {w3.eth.block_number}")
    
    # ============ STEP 6: Setup Account ============
    print("\n[6/7] Setting up deployment account...")
    
    private_key = config.get('PRIVATE_KEY', '')
    
    if not private_key:
        print("      ERROR: No PRIVATE_KEY in settings")
        print("      Add BLOCKCHAIN_PRIVATE_KEY to your .env file")
        return None
    
    account = Account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    balance_eth = w3.from_wei(balance, 'ether')
    
    print(f"      ✓ Account: {account.address}")
    print(f"      ✓ Balance: {balance_eth} ETH")
    
    if balance == 0:
        print("      WARNING: Account has 0 ETH. Deployment will fail!")
        return None
    
    # ============ STEP 7: Deploy Contract ============
    print("\n[7/7] Deploying contract...")
    
    # Create contract instance
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    
    # Get nonce (transaction count)
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Build deployment transaction
    chain_id = config.get('CHAIN_ID', 1337)
    
    tx = Contract.constructor().build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 3000000,
        'gasPrice': w3.eth.gas_price,
        'chainId': chain_id
    })
    
    print("      Signing transaction...")
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    
    print("      Sending transaction...")
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print("      Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    contract_address = receipt['contractAddress']
    
    # ============ SUCCESS ============
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUCCESSFUL!")
    print("=" * 60)
    print(f"\nContract Address: {contract_address}")
    print(f"Transaction Hash: {tx_hash.hex()}")
    print(f"Gas Used: {receipt['gasUsed']}")
    print(f"Block Number: {receipt['blockNumber']}")
    
    print("\n" + "-" * 60)
    print("NEXT STEPS:")
    print("-" * 60)
    print(f"\n1. Add this to your .env file:")
    print(f"   VOTING_CONTRACT_ADDRESS={contract_address}")
    print(f"\n2. Restart your Django server")
    print(f"\n3. Test the blockchain API endpoints")
    
    return contract_address


if __name__ == '__main__':
    deploy_contract()