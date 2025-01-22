const Blockchain = require('../Blockchain');
const Block = require('../Block');

describe('Blockchain', () => {
  let blockchain;

  beforeEach(() => {
    blockchain = new Blockchain();
  });

  test('should create genesis block', () => {
    expect(blockchain.chain.length).toBe(1);
    expect(blockchain.chain[0].previousHash).toBe('0');
  });

  test('should be able to add new block', () => {
    blockchain.minePendingTransactions('test-address');
    expect(blockchain.chain.length).toBe(2);
  });

  test('should validate chain integrity', () => {
    blockchain.minePendingTransactions('test-address');
    expect(blockchain.isChainValid()).toBeTruthy();

    blockchain.chain[1].transactions = [{ amount: 100 }];
    expect(blockchain.isChainValid()).toBeFalsy();
  });
});