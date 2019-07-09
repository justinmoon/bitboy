import sys
import time
import json
import subprocess
import argparse

from pprint import pprint

import serial
from serial.tools import list_ports


def sign(tx, script_pubkey=None, redeem_script=None):
    command = "sign"
    msg = {
        "command": command,
        "payload": {
            "tx": tx,
            "script_pubkey": script_pubkey,
            # "redeem_script": redeem_script,
        }
    }
    ser.write(json.dumps(msg).encode() + b'\r\n')
    # wallet response
    while True:
        raw_res = ser.read_until(b'\r\n').strip(b'\r\n').decode()
        print(raw_res)
        try:
            res = json.loads(raw_res)
        except:
            print("error parsing:", raw_res)
            continue

        if "signed" not in res:
            print("other json:", res)
            continue

        return res['signed']
 
def rpc(*args, returns_json=True):
    res = subprocess.run(['bitcoin-cli', '-testnet'] + list(args), 
                          capture_output=True)
    if not res.stderr:
        if returns_json:
            return json.loads(res.stdout)
        else:
            return res.stdout
    else:
        raise Exception(res.stderr)

def find_port():
    ports = list(list_ports.grep('CP2104 USB to UART Bridge Controller'))
    if len(ports) > 1:
        raise OSError("too many devices plugged in")
    elif len(ports) == 0:
        raise OSError("no device plugged in")
    else:
        return ports[0].device

def parse():
    parser = argparse.ArgumentParser(description='BitBoy Bitcoin Wallet')
    subparsers = parser.add_subparsers(help='sub-command help')

    # "bitboy send"
    send = subparsers.add_parser('send', help='send bitcoins')
    send.add_argument('recipient', help='bitcoin address')
    send.add_argument('amount', help='how many bitcoins to send')
    send.add_argument('coin', help='txid:index of output to spend')
    send.set_defaults(func=handle_send)

    # "bitboy receive"
    receive = subparsers.add_parser('receive', help='receive bitcoins')

    # "bitboy balance"
    balance = subparsers.add_parser('balance', help='count your sats')

    # "bitboy history"
    history = subparsers.add_parser('history', help='your transactions')

    # "bitboy unspent"
    unspent = subparsers.add_parser('unspent', help='your utxos')
    unspent.set_defaults(func=handle_unspent)

    return parser.parse_args()


def handle_unspent(args):
    unspent = rpc('listunspent')
    pprint(unspent)


def handle_send(args):
    # construct inputs
    input_id, input_index = args.coin.split(':')
    parent = rpc('getrawtransaction', input_id, "true")
    utxo = parent['vout'][int(input_index)]
    inputs = json.dumps([{
        "txid": input_id,
        "vout": int(input_index),
    }])

    # construct outputs
    outputs = json.dumps([{
        args.recipient: args.amount
    }])

    #  have bitcoind construct transaction
    tx = rpc('createrawtransaction', inputs, outputs, returns_json=False)
    tx = tx.strip().decode()
    # print(tx)

    # gather metadata required by signature
    redeem_script = script_pubkey = witness = None
    txtype = utxo["scriptPubKey"]["type"]

    # FIXME
    # if txtype == "pubkeyhash":
        # script_pubkey = utxo["scriptPubKey"]["hex"]
    # elif txtype == 'scripthash':
        # redeem_script = utxo["scriptPubKey"]["hex"]
    # else:
        # raise NotImplementedError()
    unspent = rpc('listunspent', '0')
    for u in unspent:
        if u['txid'] == input_id and u['vout'] == int(input_index):
            if txtype == "pubkeyhash":
                script_pubkey = u["scriptPubKey"]
            elif txtype == 'scripthash':
                redeem_script = u["redeemScript"]
            break

    assert script_pubkey or redeem_script


    # sign & broadcast 
    signed = sign(tx, script_pubkey=script_pubkey, redeem_script=redeem_script)
    sent = rpc('sendrawtransaction', signed, returns_json=False)
    print(sent)

ser =  serial.Serial(find_port(), baudrate=115200)

if __name__ == '__main__':
    args = parse()
    args.func(args)

