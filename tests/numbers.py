from decimal import Decimal, getcontext


SAT = Decimal(10) ** -8

def read_btc(s):
    return Decimal(s).quantize(SAT)

def display_btc(d):
    return "{0:.8f}".format(d)

x = "0.005"
print(x, display_btc(read_btc(x)))

x = "1E-8"
print(x, display_btc(read_btc(x)))
