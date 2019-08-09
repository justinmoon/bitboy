'''
- This displays a qr code for string "some text here" and then waits for qr scans
- If you scan the m5stack screen you should see b"some text here" printed to the repl
'''


import machine
import time

import qrencode
import m5stack

from m5stack import LCD, fonts, color565

uart = machine.UART(2,9600)

lcd = LCD()
lcd.set_color(color565(0,50,250), color565(255,255,255)) # text color, background color
lcd.erase()


def read_qr():
    count = uart.any()
    output = uart.read(count)
    return output

def read_qr_loop():
    while True:
        data = read_qr()
        print(data)
        time.sleep(1)

def display_qr(x0=0, y0=0, data="some text here"):
	s = qrencode.make(data).decode('utf-8')
	arr = s.split('\n')
	y = y0
	color = color565(0,0,0)
	for l in arr:
		y = y + 1
		x = x0
		for b in l:
			x = x + 1
			if b == '\x01':
				lcd.pixel(x,y,color)

def display_big_qr(x0=0, y0=0, data="some text here"):
	s = qrencode.make(data).decode('utf-8')
	arr = s.split('\n')
	y = y0
        step = 8
	color = color565(0,0,0)
	for l in arr:
		y = y + step
		x = x0
		for b in l:
			x = x + step
			if b == '\x01':
                                lcd.fill_rectangle(x, y, step, step, color)

display_big_qr()

read_qr_loop()
