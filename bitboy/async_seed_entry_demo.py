import uasyncio
import time
import io

from bitcoin.mnemonic import WORD_LIST
from m5stack import LCD, fonts, pins
from machine import Pin, I2C

# keyboard I2C
i2c = I2C(sda=Pin(21), scl=Pin(22))
addr = 0x08

# Pincall class
MP_STREAM_POLL_RD = const(1)
MP_STREAM_POLL = const(3)
MP_STREAM_ERROR = const(-1)

# LCD
lcd = LCD()
lcd.set_font(fonts.tt24)
lcd.erase()

# Seed state
current = ''
seed = []
seed_length = 2
ascii_lowercase = b'abcdefghijklmnopqrstuvwxyz'
keyboard = None


# From bottom of this section: https://github.com/peterhinch/micropython-async/blob/master/TUTORIAL.md#64-writing-streaming-device-drivers
class KeyboardDriver(io.IOBase):
    def __init__(self, *, cb_rise=None, cb_fall=None):
        self.pin = Pin(5)
        self.pin.init(Pin.IN)  # FIXME
        self.i2c = I2C(sda=Pin(21), scl=Pin(22))
        self.i2c_addr = 0x08
        self.cb_rise = cb_rise
        self.cb_fall = cb_fall
        self.pinval = self.pin.value()
        self.sreader = uasyncio.StreamReader(self)

    async def run(self):
        while True:
            print('loop')
            await self.sreader.read(1)

    def read(self, _):
        v = self.pinval
        if v and self.cb_rise is not None:
            value = self.i2c.readfrom(self.i2c_addr, 1)
            self.cb_rise(value)
        if not v and self.cb_fall is not None:
            value = self.i2c.readfrom(self.i2c_addr, 1)
            self.cb_fall(value)
        return b'\n'

    def ioctl(self, req, arg):
        ret = MP_STREAM_ERROR
        if req == MP_STREAM_POLL:
            ret = 0
            if arg & MP_STREAM_POLL_RD:
                v = self.pin.value()
                if v != self.pinval:
                    self.pinval = v
                    ret = MP_STREAM_POLL_RD
        return ret

class Symbols:
    enter = b'\r'
    backspace = b'\x08'

def enter_seed(value):
    global seed, current

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
            keyboard.pin_fall = noop
            return

    # another valid letter has been entered
    elif value in ascii_lowercase:
        current += value.decode()

    # ignore everything else
    else:
        pass

    # print current word to display
    index = len(seed) + 1
    lcd.print("{}) {}".format(index, current))

def noop(value):
    pass

def main():
    global keyboard

    # show initial screen
    lcd.print('Enter you seed')
    lcd.print('1)')

    # get loop
    loop = uasyncio.get_event_loop()

    # add keyboard driver to loop
    keyboard_driver = KeyboardDriver(cb_fall=enter_seed)
    loop.create_task(keyboard_driver.run())

    # run loop
    loop.run_forever()

if __name__ == '__main__':
    main()
