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

def script_from_hex(s):
    sbytes = unhexlify(s)
    ebytes = encode_script(sbytes)  # FIXME
    script = Script.parse(BytesIO(ebytes))
    print("script:", script)
    return script


def handle_msg(msg):
    if msg["command"] == "sign":
        print("signing")
        # parse transaction
        tx = Tx.parse(BytesIO(unhexlify(msg['payload']['tx'])), testnet=True)
        # parse script pubkey / redeem script
        if msg['payload']['script_pubkey']:
            script_pubkey = script_from_hex(msg['payload']['script_pubkey'])
            redeem_script = None
        # elif msg['payload']['redeem_script']:
            # script_pubkey = None
            # redeem_script = script_from_hex(msg['payload']['redeem_script'])
        # else:
            # raise ValueError("bad message: {}".format(msg))
        redeem_script = None
        signed = sign_p2pkh(tx, script_pubkey=script_pubkey, redeem_script=redeem_script)
        res = {
            "signed": signed,
        }
        print(json.dumps(res))  # send to cli
        return json.dumps(res)
    else:
        print("not signing")


def reader():
    while True:
        data = input()
        # raise
        # print("received msg:", data)
        try:
            msg = json.loads(data)
            print('json read:', msg)
        except Exception as e:
            print('json error', e)
            continue
        handle_msg(msg)


def sign_p2pkh(tx, script_pubkey=None, redeem_script=None):
    """only supports 1 input from hard-coded private key for now"""
    # hard-coded secret
    secret = 58800187338825965989061197411175755305019286370732616970021105328088303800804
    key = PrivateKey(secret)
    
    # sign first input
    assert len(tx.tx_ins) == 1
    tx.sign_input(0, key, script_pubkey=script_pubkey, redeem_script=redeem_script)

    # return hex-serialized signed transaction
    return hexlify(tx.serialize())


reader()

def test():
    msg = {'command': 'sign', 'payload': {'tx': '020000000181a093ad29afafa839b3914621be1b0df5772c140d25eb711343ab64fd35a13d0100000000ffffffff01301b0f000000000017a914076e203ae0877b2de7ead90c04532b881e7145318700000000', 'script_pubkey': 'a91422262ea1f6770b2cc5d7d6b3c1af80b477bfa1bb87', 'redeem_script': None}}
    print(handle_msg(msg))
