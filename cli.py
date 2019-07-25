import sys
import time
import json
import subprocess
import argparse

from pprint import pprint
from decimal import Decimal

from serial import Serial

from utils import find_port, testnet


CHANGE_ADDRESS = 'tb1q7v4ynhl2z3rrqshnp96w3m4n2xnd7qr954az4z'
ser =  Serial(find_port(), baudrate=115200)


def sign(tx, script_pubkeys, redeem_scripts, witness_scripts, input_values):
    # request signature over serial port
    command = "sign"
    msg = {
        "command": command,
        "payload": {
            "tx": tx,
            "script_pubkeys": script_pubkeys,
            "redeem_scripts": redeem_scripts,
            "witness_scripts": witness_scripts,
            "input_values": input_values,
        }
    }
    ser.write(json.dumps(msg).encode() + b'\r\n')

    # wait for wallet response
    while True:
        raw_res = ser.read_until(b'\r\n').strip(b'\r\n').decode()
        try:
            res = json.loads(raw_res)
        except:
            print("error parsing:", raw_res)
            continue
        if "signed" not in res:
            print("other json:", res)
            continue
        return res['signed']
 

def handle_send(args):
    # construct inputs
    utxos = [(u['txid'], u['vout']) for u in testnet.listunspent(0)]
    tx_ins = []
    input_sum = Decimal(0)
    input_values = []
    script_pubkeys = []
    for tx_id, tx_index in utxos:
        tx = testnet.getrawtransaction(tx_id, True)
        script_types = ["pubkeyhash", "scripthash", "witness_v0_keyhash"]
        if tx["vout"][tx_index]["scriptPubKey"]["type"] not in script_types:
            print('pass')
            continue
        tx_ins.append({
            "txid": tx_id,
            "vout": int(tx_index),
        })
        value = tx['vout'][tx_index]['value']
        input_sum += value
        input_values.append(int(value * 100_000_000))
        script_pubkeys.append(tx['vout'][tx_index]['scriptPubKey']['hex'])
        if input_sum > args.amount:
            break
    assert input_sum >= args.amount, "insufficient utxos to pay {}".format(args.amount)

    # construct outputs
    fee = Decimal(1000 / 100_000_000)
    change = input_sum - args.amount - fee
    tx_outs = [
        {args.recipient: "{0:.8f}".format(args.amount)},
        {CHANGE_ADDRESS: "{0:.8f}".format(change)},
    ]

    # have bitcoind construct transaction
    tx = testnet.createrawtransaction(tx_ins, tx_outs)
    print("rawtx", tx)

    # sign
    signed = sign(tx, script_pubkeys, input_values)
    print("transaction signed:", signed)

    # broadcast
    sent = testnet.sendrawtransaction(signed)

def parse():
    parser = argparse.ArgumentParser(description='BitBoy Bitcoin Wallet')
    subparsers = parser.add_subparsers(help='sub-command help')

    # "bitboy send"
    send = subparsers.add_parser('send', help='send bitcoins')
    send.add_argument('recipient', help='bitcoin address')
    send.add_argument('amount', type=Decimal, help='how many bitcoins to send')
    send.set_defaults(func=handle_send)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse()
    args.func(args)
