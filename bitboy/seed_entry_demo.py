"""
https://github.com/m5stack/M5Cloud/tree/master/examples/FACES
"""

from machine import I2C, Pin

PIN = Pin(5)

class Keyboard:
    '''M5Stack MicroPython FACES keyboard I2C driver'''

    def __init__(self, i2c=None):
        if i2c == None:
            self.i2c = I2C(sda=Pin(21), scl=Pin(22))
        else:
            self.i2c = i2c
        self.addr = 0x08
        self.cb = None

    def read(self):
        return self.i2c.readfrom(self.addr, 1)

    def _callback(self, pin):
        if pin == PIN:
            self.cb(self.read())

    def callback(self, cb):
        self.pin = PIN
        self.pin.init(Pin.IN)
        self.pin.irq(trigger=Pin.IRQ_FALLING, handler=self._callback)
        self.cb = cb

from bitcoin.mnemonic import WORD_LIST
from m5stack import LCD, fonts

lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()

keyboard = Keyboard()

current = ''
seed = []
seed_length = 2
ascii_lowercase = b'abcdefghijklmnopqrstuvwxyz'

class Symbols:
    enter = b'\r'
    backspace = b'\x08'

# callback
def enter_seed(value):
    global seed, current, keyboard

    # for debugging
    print(value)

    # backspace deletes last character in current seed word
    if value == Symbols.backspace:
        current = current[:-1]

    # they're attempting to finish entering a word
    elif value == Symbols.enter:

        # add the word if it's in bip39 word list
        if current in WORD_LIST:
            # copy current so we can delete reference
            current_copy = current[::]
            seed.append(current_copy)  
            current = ''

        # don't add word if it isn't in bip39 word list
        else:
            lcd.print('"{}" not in BIP39 word list'.format(current))
            return

        # display ending credits if we've finished adding seed words
        if len(seed) == seed_length:
            lcd.erase()
            lcd.print('seed')
            lcd.print(' '.join(seed))
            keyboard.callback(noop)
            return

    # another valid letter has been entered
    elif value in ascii_lowercase:
        current += value.decode()

    # ignore everything else
    else:
        pass

    # FIXME: better UI
    # print current word
    index = len(seed) + 1
    lcd.print("{}) {}".format(index, current))

def noop(value):
    pass

def main():
    # set callback
    keyboard.callback(enter_seed)

    # show initial screen
    lcd.print('Enter you seed')
    lcd.print('1)')

if __name__ == '__main__':
    main()
