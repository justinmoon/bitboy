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


def sign(tx, script_pubkeys):
    # request signature over serial port
    command = "sign"
    msg = {
        "command": command,
        "payload": {
            "tx": tx,
            "script_pubkeys": script_pubkeys,
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
 

def parse():
    parser = argparse.ArgumentParser(description='BitBoy Bitcoin Wallet')
    subparsers = parser.add_subparsers(help='sub-command help')

    # "bitboy send"
    send = subparsers.add_parser('send', help='send bitcoins')
    send.add_argument('recipient', help='bitcoin address')
    send.add_argument('amount', type=Decimal, help='how many bitcoins to send')
    send.set_defaults(func=handle_send)

    return parser.parse_args()


def handle_send(args):
    # construct inputs
    utxos = [(u['txid'], u['vout']) for u in testnet.listunspent(0)]
    tx_ins = []
    input_sum = Decimal(0)
    script_pubkeys = []
    for tx_id, tx_index in utxos:
        tx = testnet.getrawtransaction(tx_id, True)
        # no segwit yet
        if tx["vout"][tx_index]["scriptPubKey"]["type"] not in["pubkeyhash", "scripthash"]:
            continue
        tx_ins.append({
            "txid": tx_id,
            "vout": int(tx_index),
        })
        input_sum += tx['vout'][tx_index]['value']
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

    # sign & broadcast 
    signed = sign(tx, script_pubkeys)
    sent = testnet.sendrawtransaction(signed)

    # request signature from bitboy
    signed = sign(tx, script_pubkeys=script_pubkeys)

    # broadcast to bitcoin p2p network
    sent = testnet.sendrawtransaction(signed)
    print("broadcasted:", sent)



if __name__ == '__main__':
    args = parse()
    args.func(args)

