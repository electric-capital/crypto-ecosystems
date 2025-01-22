const crypto = require('crypto');
const EC = require('elliptic').ec;
const ec = new EC('secp256k1');

class Wallet {
  constructor() {
    this.keyPair = this.generateKeyPair();
    this.publicKey = this.keyPair.getPublic('hex');
    this.privateKey = this.keyPair.getPrivate('hex');
  }

  generateKeyPair() {
    return ec.genKeyPair();
  }

  getPublicKey() {
    return this.publicKey;
  }

  getBalance(blockchain) {
    let balance = 0;
    
    for (const block of blockchain.chain) {
      for (const transaction of block.transactions) {
        if (transaction.fromAddress === this.publicKey) {
          balance -= transaction.amount;
        }
        if (transaction.toAddress === this.publicKey) {
          balance += transaction.amount;
        }
      }
    }
    
    return balance;
  }

  signTransaction(transaction) {
    if (transaction.fromAddress !== this.publicKey) {
      throw new Error('You can only sign transactions for your own wallet!');
    }

    const hashTx = crypto
      .createHash('sha256')
      .update(transaction.fromAddress + transaction.toAddress + transaction.amount)
      .digest('hex');

    const sig = this.keyPair.sign(hashTx, 'base64');
    return sig.toDER('hex');
  }
}

module.exports = Wallet;