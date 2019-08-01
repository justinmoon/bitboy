'''
steps:
- [x] asyncio button task that prints "Button N" to screen
- [x] asyncio serial task that prints messages to screen (2 tasks at once)
- [x] screen for traversing HD hierarchy
- [x] mnemonic screen
- signing
'''

import json
import uasyncio
from aswitch import Pushbutton
from machine import Pin
# FIXME: rename to BUTTON_A. Or maybe just A, B, C and PIN_A, PIN_B, PIN_C
# FIXME: next two lines should be one import
from m5stack.pins import BUTTON_A_PIN, BUTTON_B_PIN, BUTTON_C_PIN
from m5stack import LCD, fonts
from sys import stdin, stdout
from bitcoin.hd import HDPrivateKey
from bitcoin.mnemonic import secure_mnemonic
from binascii import hexlify, unhexlify
from bitcoin.tx import Tx
from bitcoin.script import Script
from io import BytesIO
import urandom

A_PIN = Pin(BUTTON_A_PIN, Pin.IN, Pin.PULL_UP)
B_PIN = Pin(BUTTON_B_PIN, Pin.IN, Pin.PULL_UP)
C_PIN = Pin(BUTTON_C_PIN, Pin.IN, Pin.PULL_UP)

A_BUTTON = Pushbutton(A_PIN)
B_BUTTON = Pushbutton(B_PIN)
C_BUTTON = Pushbutton(C_PIN)

MASTER = None  # HDPrivateKey
INDEX = 0
ADDRESS = "bech32"  # bech32 or legacy
PATH_PREFIX = "m/84'/1'/0'"

lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()

def get_path():
    path = PATH_PREFIX + '/' + str(INDEX)
    return path.encode()

def release_button(pin): 
    if pin == A_PIN:
        lcd.print("Button A")
    if pin == B_PIN:
        lcd.print("Button B")
    if pin == C_PIN:
        lcd.print("Button C")

def print_address():
    path = get_path()
    key = MASTER.traverse(path)
    if ADDRESS == 'bech32':
        address = key.bech32_address()
    elif ADDRESS == 'legacy':
        # FIXME: rename to .legacy_address()
        address = key.address()
    else:
        raise ValueError("Invalid ADDRESS value")
    lcd.erase()
    lcd.set_pos(20, 20)
    lcd.print(path.decode())
    lcd.print(address)


def traverse_button(pin):
    global INDEX, ADDRESS
    if pin == A_PIN:
        if INDEX != 0:
            INDEX -= 1
    if pin == B_PIN:
        ADDRESS = 'bech32' if ADDRESS == 'legacy' else 'legacy' 
    if pin == C_PIN:
        INDEX += 1
    print_address()


async def button_manager():
    # TODO: i'm not sure why this must run in a coroutine ...
    A_BUTTON.release_func(traverse_button, (A_PIN,))
    B_BUTTON.release_func(traverse_button, (B_PIN,))
    C_BUTTON.release_func(traverse_button, (C_PIN,))

async def serial_manager():
    sreader = uasyncio.StreamReader(stdin)
    swriter = uasyncio.StreamWriter(stdout, {})  # TODO: what is this second param?
    while True:
        raw_msg = await sreader.readline()
        try:
            msg = json.loads(raw_msg.decode().strip())
        except Exception as e:
            continue
        result = handle_msg(msg)
        response = {"result": result}
        json_res = json.dumps(response) + '\r\n'  # FIXME
        await swriter.awrite(json_res)

def title(s):
    # calculations
    sw = fonts.tt32.get_width(s)
    padding = (lcd.width - sw) // 2

    # configure lcd
    lcd.set_font(fonts.tt32)
    lcd.set_pos(padding, 20)

    # print
    lcd.print(s)

def mnemonic_columns(mnemonic):
    # print title
    title("Seed Words")

    # set font
    lcd.set_font(fonts.tt24)

    # variables for printing
    words = mnemonic.split()
    labeled = [str(i) + ". " + word for i, word in enumerate(words, 1)]
    words_per_col = len(words) // 2
    col_width = max([lcd._font.get_width(w) for w in labeled])
    # 2 colunms with equal spacing on all sides
    pad_x = (lcd.width - 2 * col_width) // 3
    pad_y = 20
    left_col_x, left_col_y = pad_x, lcd._y + pad_y
    right_col_x, right_col_y = 2 * pad_x + col_width, lcd._y + pad_y

    # print left column
    lcd.set_pos(left_col_x, left_col_y)
    for word in labeled[:words_per_col]:
        lcd.print(word)

    # print right column
    lcd.set_pos(right_col_x, right_col_y)
    for word in labeled[words_per_col:]:
        lcd.print(word)

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
        return handle_sign(tx, script_pubkeys, redeem_scripts, witness_scripts, input_values)
    elif msg["command"] == "addr":
        path = msg['payload']['path'].encode()
        return handle_addr(path)
    elif msg["command"] == "xpub":
        path = msg['payload']['path'].encode()
        return handle_xpub(path)
    else:
        return {
            "error": "command not recognized: " + msg['command'],
        }

def handle_sign(tx, script_pubkeys, redeem_scripts, witness_scripts, input_values):
    """only supports 1 input from hard-coded private key for now"""
    # useful for testing
    # secret = 58800187338825965989061197411175755305019286370732616970021105328088303800803
    # private_key = PrivateKey(secret)

    private_key = MASTER.traverse(get_path()).private_key

    items = list(zip(range(len(tx.tx_ins)), tx.tx_ins, script_pubkeys, redeem_scripts, witness_scripts, input_values))
    assert len(items) == len(tx.tx_ins), 'items were mangled'
    for input_index, tx_in, script_pubkey, redeem_script, witness_script, input_value in items:
        if script_pubkey.is_p2pkh_script_pubkey():
            print("signing p2pkh")
            tx.sign_input_p2pkh(input_index, private_key, script_pubkey)
        elif script_pubkey.is_p2sh_script_pubkey():
            print("signing p2sh")
            tx.sign_input_p2sh(input_index, private_key, redeem_script)
        elif script_pubkey.is_p2wpkh_script_pubkey():
            print("signing p2wpkh")
            tx.segwit = True  # FIXME
            assert input_value is not None, "input value needed for segwit signature"
            tx.sign_input_p2wpkh(input_index, input_value, private_key, script_pubkey)
        elif script_pubkey.is_p2wsh_script_pubkey():
            print("signing p2wsh")
            assert input_value is not None, "input value needed for segwit signature"
            assert witness_script is not None, "witness script required to sign p2wsh input"
            tx.sign_input_p2wsh(input_index, input_value, private_key, witness_script)
        else:
            raise ValueError('unknown input type')
    return hexlify(tx.serialize())

def handle_addr(path):
    return MASTER.traverse(path).bech32_address()

def handle_xpub(path):
    key = MASTER.traverse(path)
    return key.pub.xpub()

async def start():
    global MASTER

    # attempt to load MASTER from filesystem, otherwise generate and print mnemonic
    try:
        with open('key', 'rb') as f:
            MASTER = HDPrivateKey.parse(f)
            print_address()
            print("loaded private key")
    except:
        mnemonic = secure_mnemonic()
        mnemonic_columns(mnemonic)
        password = ""
        path = b"m"
        MASTER = HDPrivateKey.from_mnemonic(mnemonic, password, path=path, testnet=True)

        # TODO
        # sd = machine.SDCard(slot=2, mosi=23, miso=19, sck=18, cs=4)
        # uos.mount(sd, '/sd')

        with open("key", "wb") as f:
            f.write(MASTER.serialize())
            print("generated and saved private key to disk")

def main():
    loop = uasyncio.get_event_loop()
    loop.create_task(button_manager())
    loop.create_task(serial_manager())
    loop.create_task(start())
    loop.run_forever()

if __name__ == '__main__':
    main()
