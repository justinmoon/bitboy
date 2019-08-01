import sys
import time
import json
import subprocess
import argparse

from pprint import pprint
from decimal import Decimal

from serial import Serial

from utils import find_port, testnet
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bedrock.helper import encode_varstr


CHANGE_ADDRESS = 'tb1qjy3lgaw5rtckrrdg0xxcqhxpmzx9g5zqkuraej'
ser =  Serial(find_port(), baudrate=115200)

rpc_template = "http://%s:%s@%s:%s/wallet/%s"
rpc = AuthServiceProxy(rpc_template % ('bitcoin', 'python', 'localhost', 18332, ''))
wallet_rpc = AuthServiceProxy(rpc_template % ('bitcoin', 'python', 'localhost', 18332, 'bitboy'))


def sat_to_btc(d):
    return "{0:.8f}".format(d)


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


def create_wallet_and_export(xpub):
    # load watch-only "bitboy" wallet, and create it if it doesn't exist yet
    watch_only_name = 'bitboy'
    bitcoin_wallets = rpc.listwallets()
    if watch_only_name not in bitcoin_wallets:
        try:
            rpc.loadwallet(watch_only_name)
            print(f"Loaded watch-only Bitcoin Core wallet \"{watch_only_name}\"")
        except JSONRPCException as e:
            try:
                rpc.createwallet(watch_only_name, True)
                print(f"Created watch-only Bitcoin Core wallet \"{watch_only_name}\"")
            except JSONRPCException as e:
                raise Exception("Couldn't establish watch-only Bitcoin Core wallet")

    # export address
    xpub = 'tpubDE98e6phWTmuvERETHCjXzAz6S6kmYGSnkycpBu9SERVSNFnTTBUx6WERcUMZAxwrPS6vnTReVxGnrqVJD937ASR8aJ7eTv127vGhLMPBHG'  # FIXME
    raw_descriptor = 'wpkh(' + xpub + ')'
    descriptor = wallet_rpc.getdescriptorinfo(raw_descriptor)['descriptor']
    r = wallet_rpc.importmulti([{
        'desc': descriptor,
        "timestamp": int(time.time() - 60*60*24*30),  # 30 days
        "watchonly": True,
    }])
    print("importmulti: ", r)


def handle_send(args):
    # construct inputs
    utxos = [(u['txid'], u['vout']) for u in wallet_rpc.listunspent(0)]
    tx_ins = []
    input_sum = Decimal(0)
    input_values = []
    script_pubkeys = []
    redeem_scripts = []
    witness_scripts = []
    for tx_id, tx_index in utxos:
        tx = wallet_rpc.getrawtransaction(tx_id, True)
        script_types = ["pubkeyhash", "scripthash", "witness_v0_keyhash", "witness_v0_scripthash"]
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
        script_pubkey = encode_varstr(bytes.fromhex(tx['vout'][tx_index]['scriptPubKey']['hex'])).hex()
        script_pubkeys.append(script_pubkey)
        redeem_scripts.append(None)  # FIXME
        witness_scripts.append(None)  # FIXME
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

    signed = sign(tx, script_pubkeys, redeem_scripts, witness_scripts, input_values)
    print("transaction signed:", signed)

    # broadcast
    sent = wallet_rpc.sendrawtransaction(signed)
    print("result", sent)

def handle_address(args):
    # FIXME: an "xpub" command would be better since we're using descriptors now ...


    msg = {
        "command": "addr",
    }
    ser.write(json.dumps(msg).encode() + b'\r\n')

    # FIXME
    # wait for wallet response
    while True:
        raw_res = ser.read_until(b'\r\n').strip(b'\r\n').decode()
        print(raw_res)
        try:
            res = json.loads(raw_res)
        except:
            print("error parsing:", raw_res)
            continue
        if "address" not in res:
            print("other json:", res)
            continue
        else:
            break
    address = res['address']
    print(address)
    create_wallet_and_export(address)

    create_wallet_and_export(None)

def parse():
    parser = argparse.ArgumentParser(description='BitBoy Bitcoin Wallet')
    subparsers = parser.add_subparsers(help='sub-command help')

    # "bitboy send"
    send = subparsers.add_parser('send', help='send bitcoins')
    send.add_argument('recipient', help='bitcoin address')
    send.add_argument('amount', type=Decimal, help='how many bitcoins to send')
    send.set_defaults(func=handle_send)

    # "bitboy address"
    address = subparsers.add_parser('address', help='generate receiving address')
    address.set_defaults(func=handle_address)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse()
    args.func(args)
