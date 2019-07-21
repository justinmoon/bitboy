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


def script_from_hex(script_hex):
    script_bytes = unhexlify(script_hex)
    script_encoded = encode_varint(len(script_bytes)) + script_bytes
    script = Script.parse(BytesIO(script_encoded))
    return script


def handle_msg(msg):
    if msg["command"] == "sign":
        # parse transaction
        tx = Tx.parse(BytesIO(unhexlify(msg['payload']['tx'])), testnet=True)
        script_pubkeys = [script_from_hex(hx) for hx in msg['payload']['script_pubkeys']]
        input_values = msg['payload']['input_values']
        signed = sign(tx, script_pubkeys, input_values)
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
        print("received msg:", repr(data))
        try:
            msg = json.loads(data)
            print('json read:', msg)
        except Exception as e:
            print('json error', e)
            continue
        handle_msg(msg)


def sign(tx, script_pubkeys, input_values):
    """only supports 1 input from hard-coded private key for now"""
    print("signing")
    # hard-coded secret
    secret = 58800187338825965989061197411175755305019286370732616970021105328088303800804
    secret = 8675309
    key = PrivateKey(secret)

    # tx.segwit = True
    
    for i, tx_in in enumerate(tx.tx_ins):
        script_pubkey = script_pubkeys[i]
        print("signing {} w/ pubkey {}".format(tx_in, script_pubkey))
        if script_pubkeys[i].is_p2sh_script_pubkey():
            sec = key.public_key.sec(compressed=True)
            redeem_script = Script(cmds=[sec, 172])
            input_value = None
        elif script_pubkeys[i].is_p2wpkh_script_pubkey():
            redeem_script = None
            input_value = input_values[i]
        else:
            redeem_script = None
            input_value = None
        tx.sign_input(i, key, script_pubkey=script_pubkey, redeem_script=redeem_script,
                      input_value=input_value)
        print("script_sig", tx_in.script_sig)
        print("witness", tx_in.witness)

    # return signed transaction in hexidecimal
    return hexlify(tx.serialize())


reader()
