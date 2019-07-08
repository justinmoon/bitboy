import json

from io import BytesIO

from binascii import hexlify, unhexlify

from m5stack import LCD, fonts
from m5stack.pins import BUTTON_A_PIN, BUTTON_B_PIN, BUTTON_C_PIN  # FIXME

from bitcoin.helper import encode_varint
from bitcoin.tx import Tx
from bitcoin.script import Script
from bitcoin.ecc import PrivateKey


lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()

def encode_script(script_bytes):
    return encode_varint(len(script_bytes)) + script_bytes

def reader():
    while True:
        data = input()
        try:
            msg = json.loads(data)
        except json.JSONDecodeError as e:
            print('json error', e)
            continue
        if msg["command"] == "sign":
            print("signing")
            signed = sign_p2pkh(msg["payload"]["tx"], msg["payload"]["script_pubkey"])
            res = {
                "signed": signed,
            }
            print(json.dumps(res))
        else:
            print("not signing")


def sign_p2pkh(tx_hex, script_pubkey_hex):
# def sign_p2pkh():
    """only supports 1 input from hard-coded private key for now"""
    # hard-coded secret
    secret = 58800187338825965989061197411175755305019286370732616970021105328088303800804
    key = PrivateKey(secret)
    
    # parse transaction
    tx = Tx.parse(BytesIO(unhexlify(tx_hex)), testnet=True)

    # parse script pubkey
    script_pubkey_bytes = unhexlify(script_pubkey_hex)
    encoded_script_pubkey = encode_script(script_pubkey_bytes)  # FIXME
    script_pubkey = Script.parse(BytesIO(encoded_script_pubkey))

    # sign first input
    assert len(tx.tx_ins) == 1
    tx.sign_input(0, key, script_pubkey=script_pubkey)

    # return hex-serialized signed transaction
    return hexlify(tx.serialize())


reader()
