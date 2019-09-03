import os
import json
import time
import uasyncio

from sys import stdin, stdout
from io import BytesIO
from binascii import unhexlify, hexlify

from asyn import Event
from m5stack import LCD, fonts, color565, SDCard, buttons, keyboard, qr
from bitcoin.mnemonic import secure_mnemonic, WORD_LIST
from bitcoin.hd import HDPrivateKey
from bitcoin.psbt import PSBT
from bitcoin.tx import Tx
from bitcoin.script import Script
from bitcoin.helper import encode_varstr

# globals
lcd = LCD()
SIGN_IT = Event()
DONT_SIGN_IT = Event()
SIGNED = Event()
KEY = None
PARTIAL_QR = ''
last_qr = 0

KEYBOARD = keyboard.KeyboardDriver(cb_fall=lambda value: lcd.print(str(value)))

async def qr_callback(b):
    # this is very hacky b/c qr driver will return parts of a qr code at-a-time
    # and i don't have a standard way to know that I have the whole thing (need checksum or something)
    # also, doesn't accept commands yet ... just transaction signing ...
    global PARTIAL_QR, last_qr
    if time.time() - last_qr > 2:
        print('qr reader timeout')
        PARTIAL_QR = ''
    last_qr = time.time()
    PARTIAL_QR += b.decode()
    try:
        print('trying to deserialize')
        psbt = PSBT()
        psbt.deserialize(PARTIAL_QR.strip('\r'))
        print('deserialized')
    except Exception as e:
        print(e)
        print('incomplete')
        return
    signed = await sign_psbt(psbt)

QRSCANNER = qr.QRScanner(qr_callback)

# TODO: I need a router class that keeps track of history, can go "back"
class Screen:
    '''Abstract base class for different screens in the wallet'''

    def a_release(self):
        pass

    def b_release(self):
        pass

    def c_release(self):
        pass

    def on_keypress(self, value):
        # a little hacky that there's no self 
        pass

    def render(self):
        raise NotImplementedError()

    def visit(self):
        '''router function sets button callbacks and renders screen'''
        buttons.A.release_func(self.a_release)
        buttons.B.release_func(self.b_release)
        buttons.C.release_func(self.c_release)
        KEYBOARD.cb_fall = lambda value: self.on_keypress(value)
        self.render()

class MnemonicScreen(Screen):

    def __init__(self, mnemonic):
        self.mnemonic = mnemonic

    def on_verify(self):
        '''display addresses once they've confirmed mnemonic'''
        # FIXME: slow, display loading screen
        save_key(self.mnemonic)
        TraverseScreen().visit()

    def a_release(self):
        self.on_verify()

    def b_release(self):
        self.on_verify()

    def c_release(self):
        self.on_verify()
    
    def render(self):
        lcd.erase()  # FIXME
        lcd.title("Seed Words")

        # format mnemonic and print
        words = self.mnemonic.split()
        labeled = [str(i) + ". " + word for i, word in enumerate(words, 1)]
        words_per_col = len(words) // 2
        left = labeled[:words_per_col]
        right = labeled[words_per_col:]

        lcd.body_columns(left, right)

class DisplayXpubScreen(Screen):

    def a_release(self):
        HomeScreen().visit()

    def b_release(self):
        HomeScreen().visit()

    def c_release(self):
        HomeScreen().visit()
    
    def render(self):
        print('xpub screen')
        lcd.erase()
        # FIXME
        xpub = KEY.traverse(b"m/69'").xpub()
        lcd.qr(xpub)

class DisplaySignatures(Screen):

    def __init__(self, tx, index):
        self.tx = tx
        self.index = index

    def nav(self):
        # we're done
        if self.index + 1 == len(self.tx.tx_ins):
            HomeScreen().visit()
        # more inputs left
        else:
            DisplaySignatures(self.tx, self.index + 1)

    def a_release(self):
        self.nav()

    def b_release(self):
        self.nav()

    def c_release(self):
        self.nav()
    
    def render(self):
        print('printing script_sig')
        lcd.erase()
        script_sig = hexlify(self.tx.tx_ins[self.index].script_sig.serialize())
        lcd.qr(script_sig)

class HomeScreen(Screen):

    def render(self):
        lcd.erase()
        lcd.alert("Scan PSBT")

class ConfirmOutputScreen(Screen):

    def __init__(self, psbt, index):
        self.psbt = psbt
        self.index = index

    def a_release(self):
        print("don't sign")
        DONT_SIGN_IT.set()
        AlertScreen('Aborted', 3, HomeScreen()).visit()

    def b_release(self):
        pass

    def c_release(self):
        # confirm remaining outputs
        if len(self.psbt.tx.vout) > self.index + 1:
            ConfirmOutputScreen(self.psbt, self.index + 1).visit()
        # done confirming. sign it.
        else:
            SIGN_IT.set()
            # FIXME: some way to tell whether we're signing over usb or qr
            # AlertScreen('Transaction signed', 3, HomeScreen()).visit()


    def render(self):
        print('CONFIRM')
        lcd.erase()

        lcd.title("Confirm Output")

        lcd.set_font(fonts.tt24)
        vout = self.psbt.tx.vout[self.index]
        script_pubkey = Script.parse(BytesIO(encode_varstr(vout.scriptPubKey)))
        address = script_pubkey.address(testnet=True)
        amount = vout.nValue
        # TODO: use psbt.outputs[i]['hd_keypath'] to detect change
        msg = "Are you sure you want to send {} satoshis to {}?".format(amount, address)
        lcd.body(msg)

        lcd.label_buttons("no", "", "yes")

MNEMONIC = ['shield', 'flash', 'garage', 'effort', 'list', 'bubble', 'faculty', 'donate', 'million', 'stool', 'expect', 'frown']

class SeedChoiceScreen(Screen):

    def __init__(self):
        self.has_key = 'key.txt' in os.listdir('/sd')

    def a_release(self):

        if self.has_key:
            # home screen
            # FIXME
            # HomeScreen().visit()
            print('loading')
            load_key()
            print('loaded')
            DisplayXpubScreen().visit()
        else:
            # generate mnemonic
            mnemonic = secure_mnemonic()
            MnemonicScreen(mnemonic).visit()

    def c_release(self):
        # input mnemonic
        SeedEntryScreen(12, '', MNEMONIC[:11]).visit()  # FIXME

    def render(self):
        lcd.alert('Generate or input seed?')
        a = 'Load' if self.has_key else 'Generate'
        lcd.label_buttons(a, "", "Input")


class AlertScreen(Screen):

    def __init__(self, msg, timeout, screen):
        self.msg = msg
        self.timeout = timeout
        self.screen = screen

    def render(self):
        lcd.erase()
        lcd.alert(self.msg)
        time.sleep(self.timeout)
        self.screen.visit()

class SeedEntryCompleteScreen(Screen):

    def render(self):
        lcd.erase()
        lcd.alert("Transaction signed")
        time.sleep(3)
        HomeScreen().visit()

class SeedEntryScreen(Screen):

    ascii_lowercase = b'abcdefghijklmnopqrstuvwxyz'

    def __init__(self, seed_length, current=None, seed=None):
        self.seed_length = seed_length
        if current is None:
            current = ''
        if seed is None:
            seed = []
        self.current = current
        self.seed = seed

    def on_keypress(self, value):
        # for debugging
        print(value)

        # backspace deletes last character in current seed word
        if value == keyboard.KeyboardSymbols.backspace:
            self.current = self.current[:-1]
            lcd.erase_body()
            lcd.set_pos(int((lcd.width / 2) - 30), int(lcd.height / 2))
            lcd.write(self.current)

        # they're attempting to finish entering a word
        elif value == keyboard.KeyboardSymbols.enter:

            # add the word if it's in bip39 word list
            if self.current in WORD_LIST:
                # copy current so we can delete reference
                self.seed.append(self.current[::])
                self.current = ''
                if len(self.seed) == self.seed_length:
                    mnemonic = ' '.join(self.seed)
                    password = ''
                    derivation_path = b'm'
                    lcd.alert('Loading Key')
                    global KEY
                    KEY = HDPrivateKey.from_mnemonic(mnemonic, password, path=derivation_path, testnet=True)
                    return AlertScreen('Your XPUB', 1.5, DisplayXpubScreen()).visit()
                else:
                    return SeedEntryScreen(self.seed_length, self.current, self.seed).visit()

        # another valid letter has been entered
        elif value in self.ascii_lowercase:
            self.current += value.decode()
            print(value)
            print(value.decode())
            lcd.write(value.decode())

        # ignore everything else
        else:
            pass

    def render(self):
        lcd.erase()
        seed_number = len(self.seed) + 1
        lcd.title("Enter Word #{}".format(seed_number))
        lcd.set_pos(int((lcd.width / 2) - 30), int(lcd.height / 2))
        lcd.write(self.current)

def load_key():
    global KEY
    with open('/sd/key.txt', 'rb') as f:
        KEY = HDPrivateKey.parse(f)

def save_key(mnemonic):
    '''saves key to disk, sets global KEY variable'''
    # FIXME: make sure secrets are never overwritten with different keys
    global KEY
    password = ''
    derivation_path = b'm'
    KEY = HDPrivateKey.from_mnemonic(mnemonic, password, path=derivation_path, testnet=True)
    with open('/sd/key.txt', 'wb') as f:
        f.write(KEY.serialize())

def start():
    # FIXME
    lcd.erase()

    # mount SD card to filesystem
    sd = SDCard()
    os.mount(sd, '/sd')

    # navigate to first screen
    SeedEntryScreen(12).visit()

async def sign_psbt(psbt):
    tx = Tx.parse(BytesIO(psbt.tx.serialize()))
    print("SIGNING")

    # ask user to confirm each output
    ConfirmOutputScreen(psbt, 0).visit()
    print("navigated")

    # wait for confirmation or cancellation
    while True:
        print('waiting for SIGN_IT / DONT_SIGN_IT')
        if SIGN_IT.is_set():
            SIGN_IT.clear()
            break
        if DONT_SIGN_IT.is_set():
            DONT_SIGN_IT.clear()
            # FIXME: how to propogate cancellation
            return json.dumps({"error": "cancelled by user"})
        await uasyncio.sleep(1)

    # sign each input
    print('SIGNING')
    for i, tx_in in enumerate(tx.tx_ins):
        print(hexlify(tx_in.prev_tx))
        print(psbt.inputs[i].non_witness_utxo.hash.decode())
        assert hexlify(tx_in.prev_tx) == psbt.inputs[i].non_witness_utxo.hash
        raw_script_pubkey = psbt.inputs[i].non_witness_utxo.vout[tx_in.prev_index].scriptPubKey
        script_pubkey = Script.parse(BytesIO(encode_varstr(raw_script_pubkey)))
        for pubkey, path in psbt.inputs[i].hd_keypaths.items():
            print(pubkey, path)
            fingerprint = path[0]
            child_index = path[1]
            path = "m/69'/{}".format(child_index).encode()
            child = KEY.traverse(path)
            assert child.pub.public_key.sec(compressed=True) == pubkey
            tx.sign_input_p2pkh(i, child.private_key, script_pubkey)
            print('signed {}'.format(i))

    print('SIGNED')
    DisplaySignatures(tx, 0).visit()

if __name__ == '__main__':
    start()
    loop = uasyncio.get_event_loop()
    loop.create_task(KEYBOARD.run())
    ## FIXME: only run this in when a key is available for signing
    loop.create_task(QRSCANNER.run())
    loop.run_forever()
