import sys
import json

from serial import Serial
from serial.tools import list_ports

from rpc import WalletRPC, sat_to_btc
from bedrock.helper import encode_varstr

def find_port():
    '''figure out which port to connect to'''
    ports = list(list_ports.grep('CP2104 USB to UART Bridge Controller'))
    if len(ports) > 1:
        raise OSError("too many devices plugged in")
    elif len(ports) == 0:
        raise OSError("no device plugged in")
    else:
        return ports[0].device

def send_and_recv(msg):
    # this is the connection to the serial port
    ser =  Serial(find_port(), baudrate=115200)
    # send msg to device
    ser.write(msg.encode() + b'\n')
    # get response from device
    while True:
        raw = ser.read_until(b'\n').strip(b'\n').decode()
        try:
            msg = json.loads(raw)
            return msg
        except:
            print('bad msg', raw)
            continue

def xpub(derivation_path):
    msg = json.dumps({'command': 'xpub', 'derivation_path': derivation_path})
    return send_and_recv(msg)['xpub']

def address():
    msg = json.dumps({'command': 'address'})
    return send_and_recv(msg)['xpub']

def sign(tx, input_meta, output_meta):
    msg = json.dumps({'command': 'sign', 'tx': tx, 'input_meta': input_meta,
                      'output_meta': output_meta})
    res = send_and_recv(msg)
    if 'error' in res:
        raise Exception('cancelled by user')
    return res['tx']

if __name__ == '__main__':
    sign()
