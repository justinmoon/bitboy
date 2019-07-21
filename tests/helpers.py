"""
steps to run this:
- send some coins to bitcoind on testnet
- `bitcoin-cli -testnet listunspent` and choose a P2SH output
- `bitcoin-cli -testnet decoderawtransaction $rawtx` to get the redeem script hash (inside "asm")

Use these values to define `tx` and `redeem_script` below
"""
from binascii import hexlify, unhexlify
from io import BytesIO

from bitcoin.ecc import PrivateKey

from tx import Tx
from script import Script, p2sh_script

secret = 58800187338825965989061197411175755305019286370732616970021105328088303800804
key = PrivateKey(secret)

tx_hex = '0200000001a037edd6051abbd9101504c6de948d98082721f09392b44de772a8e032f4ee9c0000000000ffffffff01a08601000000000017a914076e203ae0877b2de7ead90c04532b881e7145318700000000'
tx_bytes = unhexlify(tx_hex)
tx_stream = BytesIO(tx_bytes)

# script_pubkey = Script.parse(BytesIO(unhexlify('a91451a9d3efade5a7a8bed4a256f2421498625deb2087')))
redeem_script = p2sh_script(
    unhexlify('076e203ae0877b2de7ead90c04532b881e714531'),
)


tx = Tx.parse(tx_stream, testnet=True)
print("*** Parsed Transaction ***")
print(tx)

print("*** Script Sigs ***")
for tx_in in tx.tx_ins:
    print(tx_in.script_sig)

print("*** Signing Transaction ***")
for index, tx_in in enumerate(tx.tx_ins):
    tx.sign_input(index, key, redeem_script=redeem_script)

print("*** Script Sigs ***")
for tx_in in tx.tx_ins:
    print(tx_in.script_sig)

print("*** Signed & Serialized ***")
print(hexlify(tx.serialize()))
