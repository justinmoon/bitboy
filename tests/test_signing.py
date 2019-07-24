import logging

from decimal import Decimal
from io import BytesIO

from bedrock.tx import Tx, TxIn, TxOut
from bedrock.ecc import PrivateKey
from bedrock.helper import decode_base58, little_endian_to_int, hash256, decode_bech32
from bedrock.script import p2pkh_script, p2sh_script, p2wpkh_script, Script

from cli import sign

# change log level to logging.DEBUG for more information
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

secret = 58800187338825965989061197411175755305019286370732616970021105328088303800803
key = PrivateKey(secret)


def test_sign_p2pkh():
    raw_tx = '0100000001aab6e859ca31f1e6a954323c5ca0d0ec02244016e1d45df502989ff3eadb92690000000000ffffffff014c400f00000000001976a914f34a4401e484bfb7862d0e3ecfbed4c484f5480a88ac00000000'
    script_pubkey = p2pkh_script(key.point.hash160())
    print(script_pubkey.is_p2pkh_script_pubkey())
    raw_script_pubkey = script_pubkey.raw_serialize().hex()
    script_pubkeys = [raw_script_pubkey]
    input_values = []
    result = sign(raw_tx, script_pubkeys, input_values)
    signed_tx = Tx.parse(BytesIO(bytes.fromhex(result)), testnet=True)
    print(f"Received Signed TX: {result}")
    assert signed_tx.verify()


def test_spend_p2sh():
    raw_tx = "01000000014b1ed28bb000739dee2c58b5e3b18e0dfdf929c6917c212da20ab3d7231960f20000000000ffffffff01b8820100000000001976a914507b27411ccf7f16f10297de6cef3f291623eddf88ac00000000"
    input_values = []  # FIXME: don't need this for p2sh or p2pkh ...
    script_pubkey = p2sh_script(key.point.hash160())
    raw_script_pubkey = script_pubkey.raw_serialize().hex()
    script_pubkeys = [raw_script_pubkey]
    result = sign(raw_tx, script_pubkeys, input_values)
    signed_tx = Tx.parse(BytesIO(bytes.fromhex(result)), testnet=True)
    print(f"Received Signed TX: {result}")
    assert signed_tx.verify()

def test_spend_p2wpkh():
    raw_tx = '01000000000101ebd12d3bd14fb3d7488b2deb74949b8180bb3138130b22274550e47c691e23630100000000ffffffff01ac8401000000000017a914d2d78617c37107637e76c1b20ffdbc8b58df4e84870000000000'
    input_values = [100000]
    script_pubkey = p2wpkh_script(key.point.hash160())
    raw_script_pubkey = script_pubkey.raw_serialize().hex()
    script_pubkeys = [raw_script_pubkey]
    result = sign(raw_tx, script_pubkeys, input_values)
    signed_tx = Tx.parse(BytesIO(bytes.fromhex(result)), testnet=True)
    print(f"Received Signed TX: {result}")
    assert signed_tx.verify()


def test_spend_p2sh_p2wpkh():
    pass

def test_spent_p2sh_p2wsh():
    pass

def test_spend_p2wsh():
    pass
