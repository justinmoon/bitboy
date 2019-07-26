'''
steps:
- asyncio button task that prints "Button N" to screen
- asyncio serial task that prints messages to screen (2 tasks at once)
- screen for traversing HD hierarchy
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

A = Pin(BUTTON_A_PIN, Pin.IN, Pin.PULL_UP)
B = Pin(BUTTON_B_PIN, Pin.IN, Pin.PULL_UP)
C = Pin(BUTTON_C_PIN, Pin.IN, Pin.PULL_UP)

lcd = LCD()
lcd.set_font(fonts.tt32)
lcd.erase()

def release_button(pin): 
    if pin == A:
        lcd.print("Button A")
    if pin == B:
        lcd.print("Button B")
    if pin == C:
        lcd.print("Button C")

async def button_manager():
    # TODO: these will need to be accessible from serial coroutine.
    # basically, global variables so that new behavior can be registered w/ .x_func()
    a = Pushbutton(A)
    a.release_func(release_button, (A,))
    b = Pushbutton(B)
    b.release_func(release_button, (B,))
    c = Pushbutton(C)
    c.release_func(release_button, (C,))

def main():
    loop = uasyncio.get_event_loop()
    loop.create_task(button_manager())
    loop.run_forever()

if __name__ == '__main__':
    main()
