const fs = require('fs');
const { Keypair } = require('@solana/web3.js');

const keypairFile = fs.readFileSync('target/deploy/repescrow-keypair.json');
const keypairBytes = JSON.parse(keypairFile);
const keypair = Keypair.fromSecretKey(Uint8Array.from(keypairBytes));

console.log('Program ID:', keypair.publicKey.toBase58());
