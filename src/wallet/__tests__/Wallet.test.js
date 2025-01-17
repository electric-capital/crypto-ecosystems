const Wallet = require('../Wallet');
const Transaction = require('../Transaction');
const Blockchain = require('../../blockchain/Blockchain');

describe('Wallet', () => {
  let wallet;
  let blockchain;

  beforeEach(() => {
    wallet = new Wallet();
    blockchain = new Blockchain();
  });

  test('should generate key pair', () => {
    expect(wallet.publicKey).toBeDefined();
    expect(wallet.privateKey).toBeDefined();
  });

  test('should correctly sign transactions', () => {
    const transaction = new Transaction(wallet.publicKey, 'recipient-address', 50);
    const signature = wallet.signTransaction(transaction);
    expect(signature).toBeDefined();
  });

  test('should calculate correct balance', () => {
    const initialBalance = wallet.getBalance(blockchain);
    expect(initialBalance).toBe(0);

    // Add a transaction to receive coins
    blockchain.pendingTransactions = [
      { fromAddress: null, toAddress: wallet.publicKey, amount: 100 }
    ];
    blockchain.minePendingTransactions('miner-address');

    const newBalance = wallet.getBalance(blockchain);
    expect(newBalance).toBe(100);
  });
});