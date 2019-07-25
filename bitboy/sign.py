import json

from io import BytesIO
from binascii import hexlify, unhexlify

from bitcoin.helper import encode_varstr
from bitcoin.tx import Tx
from bitcoin.script import Script
from bitcoin.ecc import PrivateKey
from m5stack import LCD, fonts

lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()

def script_from_hex(script_hex):
    if script_hex is not None:
        return Script.parse(BytesIO(unhexlify(script_hex)))

def handle_msg(msg):
    if msg["command"] == "sign":
        # parse transaction
        tx = Tx.parse(BytesIO(unhexlify(msg['payload']['tx'])), testnet=True)
        script_pubkeys = [script_from_hex(hx) for hx in msg['payload']['script_pubkeys']]
        redeem_scripts = [script_from_hex(hx) for hx in msg['payload']['redeem_scripts']]
        witness_scripts = [script_from_hex(hx) for hx in msg['payload']['witness_scripts']]
        input_values = msg['payload']['input_values']
        signed = sign(tx, script_pubkeys, redeem_scripts, witness_scripts, input_values)
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

def sign(tx, script_pubkeys, redeem_scripts, witness_scripts, input_values):
    """only supports 1 input from hard-coded private key for now"""
    secret = 58800187338825965989061197411175755305019286370732616970021105328088303800803
    private_key = PrivateKey(secret)
    items = zip(range(len(tx.tx_ins)), tx.tx_ins, script_pubkeys, redeem_scripts, witness_scripts, input_values)
    for input_index, tx_in, script_pubkey, redeem_script, witness_script, input_value in items:
        if script_pubkey.is_p2pkh_script_pubkey():
            tx.sign_input_p2pkh(input_index, private_key, script_pubkey)
        elif script_pubkey.is_p2sh_script_pubkey():
            tx.sign_input_p2sh(input_index, private_key, redeem_script)
        elif script_pubkey.is_p2wpkh_script_pubkey():
            assert input_value is not None, "input value needed for segwit signature"
            tx.sign_input_p2wpkh(input_index, input_value, private_key, script_pubkey)
        elif script_pubkey.is_p2wsh_script_pubkey():
            assert input_value is not None, "input value needed for segwit signature"
            assert witness_script is not None, "witness script required to sign p2wsh input"
            tx.sign_input_p2wsh(input_index, input_value, private_key, witness_script)
        else:
            raise ValueError('unknown input type')
    return hexlify(tx.serialize())

reader()
