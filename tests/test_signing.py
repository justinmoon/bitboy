import logging
from decimal import Decimal
from io import BytesIO

from serial import Serial
from bedrock.tx import Tx, TxIn, TxOut
from bedrock.ecc import PrivateKey
from bedrock.helper import decode_base58, little_endian_to_int, hash256, decode_bech32
from bedrock.script import p2pkh_script, p2wsh_script, Script

from cli import sign
from utils import find_port, testnet, regtest, regtest_bitboy

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

ser =  Serial(find_port(), baudrate=115200)

SAT = Decimal(10) ** -8
SAT_PER_COIN = Decimal(10**8)
secret = 58800187338825965989061197411175755305019286370732616970021105328088303800803
key = PrivateKey(secret)


def sat_to_btc(s):
    return Decimal(s).quantize(SAT)

def p2sh_h160():
    sec = key.point.sec(compressed=True)
    redeem_script = Script(cmds=[sec, 172])  # simplest case
    raw_redeem = redeem_script.raw_serialize()
    return hash160(raw_redeem)

def get_redeem_script():
    sec = key.point.sec(compressed=True)
    return Script(cmds=[sec, 172])  # simplest case

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

def test_spend_p2sh():
    # a p2sh output we will spend
    prev_tx = Tx.parse(BytesIO(bytes.fromhex('02000000000101fb53d0df5005a34a26b139ecfa8b30da136e267bd8c1f71ddc37c82385fe2488000000001716001488937b3af68e3d0b3f06dd6f4e2e3a6cd6844bc7feffffff02a08601000000000017a9141d49e344b4a81eda4e3a3d8116b2113af42d20798772621b000000000017a914df8f7213a142d5f6e0c4b9ae0df56aba87cdd005870247304402202dcbbd3787f113d6fe4e779e7635248b2be6f9ec9b2ceb21cc3292195d8296cb0220398d2f45d8a362e6305c2c59b282a431bc6e70c5d926b1cebb5b5579e0c287ea01210305c69c9c5eb41e152614fe85280c7691a7bb0a0d7fa464ac05956f4c240fad8100000000')))
    prev_index = 0
    utxo = prev_tx.tx_outs[prev_index]

    # construct inputs
    tx_in = TxIn(prev_tx.hash(), prev_index)  # index right?
    tx_ins = [tx_in]
    utxo_amount = sat_to_btc(utxo.amount)
    input_values = []  # FIXME: don't need this for p2sh or p2pkh ...
    script_pubkeys = [utxo.script_pubkey.raw_serialize().hex()]

    # construct outputs
    fee = 1000
    h160 = decode_base58('mnrVtF8DWjMu839VW3rBfgYaAfKk8983Xf')
    script_pubkey = p2pkh_script(h160)
    tx_out = TxOut(amount=(utxo.amount - fee), script_pubkey=script_pubkey)
    tx_outs = [tx_out]

    # construct transaction
    tx = Tx(1, tx_ins, tx_outs, 0, True)

    # send to the device for a signature
    result = sign(tx.serialize().hex(), script_pubkeys, input_values)
    signed_tx = Tx.parse(BytesIO(bytes.fromhex(result)), testnet=True)
    print(f"Received Signed TX: {result}")
    assert signed_tx.verify()


def test_spend_p2wpkh():
    pass

def test_spend_p2sh_p2wpkh():
    pass

def test_spent_p2sh_p2wsh():
    pass

def test_spend_p2wsh():
    pass
