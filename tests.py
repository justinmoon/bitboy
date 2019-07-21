from decimal import Decimal
from io import BytesIO

from cli import sign
from serial import Serial
from utils import find_port, testnet

from bedrock.tx import Tx, TxIn, TxOut
from bedrock.ecc import PrivateKey
from bedrock.helper import decode_base58
from bedrock.script import p2pkh_script


ser =  Serial(find_port(), baudrate=115200)


def test_sign_p2pkh():
    tx_ins = []
    tx_outs = []

    script_pubkeys = []
    input_values = []

    prev_tx = Tx.parse(BytesIO(bytes.fromhex('010000000001018ba97409f90a1d5261abe64e39a77a57ab26e9e5a44b2f3173ba19e08958f3ef0100000017160014a923d0cb7c5acdbee2ddb6f34474cc1c848c8c95ffffffff0280778e06000000001976a914d52ad7ca9b3d096a38e752c2018e6fbc40cdf26f88acddfd21447400000017a914fc9ee9c069db7e91472834654654c75a04140f0a8702483045022100e41b9476ea9315fcc8375331a2a3dbc7b5b6d5d7571c9377a51c2b99ab1bab110220109aae5aea079fa92b0c875785b4cb6c29e761d96fc24a7844b1597a8b300aa20121026b0d4d9a5d5647fec05bb59a74955c9952ba796fadfe317926a9aa8de9b33cd100000000')), testnet=True)

    prev_id = bytes.fromhex('0025bc3c0fa8b7eb55b9437fdbd016870d18e0df0ace7bc9864efc38414147c8')
    tx_ins.append(TxIn(prev_id, 0))
    # inputs.append(tx.tx_tx_outs[0].amount)
    inputs = [Decimal("1.1")]
    # doesn't need the script length prefix ...
    script_pubkeys.append(prev_tx.tx_outs[0].script_pubkey.serialize()[1:].hex())
    print(script_pubkeys)

    h160 = decode_base58('mzx5YhAH9kNHtcN481u6WkjeHjYtVeKVh2')
    script_pubkey = p2pkh_script(h160)
    tx_outs.append(TxOut(amount=int(0.99 * 100000000), script_pubkey=script_pubkey))

    h160 = decode_base58('mnrVtF8DWjMu839VW3rBfgYaAfKk8983Xf')
    script_pubkey = p2pkh_script(h160)
    tx_outs.append(TxOut(amount=int(0.1 * 100000000), script_pubkey=script_pubkey))

    tx = Tx(1, tx_ins, tx_outs, 0, True)

    result = sign(tx.serialize().hex(), script_pubkeys, input_values)
    signed_tx = Tx.parse(BytesIO(bytes.fromhex(result)), testnet=True)
    print(f"Received Signed TX: {result}")
    assert signed_tx.verify()


