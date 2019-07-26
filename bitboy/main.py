'''
steps:
- [x] asyncio button task that prints "Button N" to screen
- [x] asyncio serial task that prints messages to screen (2 tasks at once)
- [x] screen for traversing HD hierarchy
- mnemonic screen
- signing
'''

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
import urandom

A_PIN = Pin(BUTTON_A_PIN, Pin.IN, Pin.PULL_UP)
B_PIN = Pin(BUTTON_B_PIN, Pin.IN, Pin.PULL_UP)
C_PIN = Pin(BUTTON_C_PIN, Pin.IN, Pin.PULL_UP)

A_BUTTON = Pushbutton(A_PIN)
B_BUTTON = Pushbutton(B_PIN)
C_BUTTON = Pushbutton(C_PIN)

KEY = None  # HDPrivateKey
INDEX = 0
ADDRESS = "bech32"  # bech32 or legacy

lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()

def release_button(pin): 
    if pin == A_PIN:
        lcd.print("Button A")
    if pin == B_PIN:
        lcd.print("Button B")
    if pin == C_PIN:
        lcd.print("Button C")

def print_address(key):
    if ADDRESS == 'bech32':
        address = key.bech32_address()
    elif ADDRESS == 'legacy':
        # FIXME: rename to .legacy_address()
        address = key.address()
    else:
        raise ValueError("Invalid ADDRESS value")
    lcd.erase()
    lcd.set_pos(20, 20)
    path = "m/84'/1'/0'/" + str(INDEX)  # FIXME: copy pasta
    lcd.print(path)
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
    key = KEY.child(INDEX, False)
    print_address(key)


async def button_manager():
    # TODO: i'm not sure why this must run in a coroutine ...
    A_BUTTON.release_func(traverse_button, (A_PIN,))
    B_BUTTON.release_func(traverse_button, (B_PIN,))
    C_BUTTON.release_func(traverse_button, (C_PIN,))

async def serial_manager():
    sreader = uasyncio.StreamReader(stdin)
    swriter = uasyncio.StreamWriter(stdout, {})  # TODO: what is this second param?
    while True:
        msg = await sreader.readline()
        res = '(recv) ' + msg.decode().strip()
        await swriter.awrite(res)
        lcd.print(res)

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

async def start():
    global KEY

    # attempt to load KEY from filesystem, otherwise generate and print mnemonic
    try:
        with open('key', 'rb') as f:
            KEY = HDPrivateKey.parse(f)
            child = KEY.child(0, False)
            print_address(child)
    except:
        mnemonic = secure_mnemonic()
        mnemonic_columns(mnemonic)
        password = ""
        path = b"m/84'/1'/0'"
        KEY = HDPrivateKey.from_mnemonic(mnemonic, password, path=path, testnet=True)
        with open("key", "wb") as f:
            f.write(KEY.serialize())

def main():
    loop = uasyncio.get_event_loop()
    loop.create_task(button_manager())
    loop.create_task(serial_manager())
    loop.create_task(start())
    loop.run_forever()

if __name__ == '__main__':
    main()
