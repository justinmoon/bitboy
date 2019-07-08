import sys
import time
import json
import subprocess

from pprint import pprint

import serial


port = sys.argv[1]
ser =  serial.Serial(port, baudrate=115200)


def sign(tx, script_pubkey):
    command = "sign"
    msg = {
        "command": command,
        "payload": {
            "tx": tx,
            "script_pubkey": script_pubkey,
        }
    }
    ser.write(json.dumps(msg).encode() + b'\r\n')
    # wallet response
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
 
def rpc(*args, returns_json=True):
    print(args)
    res = subprocess.run(['bitcoin-cli', '-testnet'] + list(args), 
                          capture_output=True)
    if not res.stderr:
        if returns_json:
            return json.loads(res.stdout)
        else:
            return res.stdout
    else:
        raise Exception(res.stderr)

def main():
    # show them their unspents
    unspent = rpc('listunspent')
    pprint(unspent)

    # let them select one by pasting txid
    txid, vout = input("txid:vout to spend: ").split(":")
    # txid, vout = "0fae469f3d3c546c3d57f612c82eefc153648c9ce9adda69082258fd0a740d7c:0".split(":")
    tx = rpc('gettransaction', txid)

    # collect recipient
    recipient_addr = input("address of recipient: ")
    # recipient_addr = "2MsvWeJqUG9QQwCDJ16q4iJhjybqAeK33tL"

    # construct unsigned transaction
    inputs = json.dumps([{
        "txid": txid,
        "vout": int(vout),
    }])
    outputs = json.dumps([{
        recipient_addr: str(round(float(tx['amount']) - 0.0001, 9))
    }])
    tx = rpc('createrawtransaction', inputs, outputs, returns_json=False)
    tx = tx.strip().decode()

    # get scriptPubKey
    for u in unspent:
        if u['txid'] == txid:
            print(u)
            script_pubkey = u['scriptPubKey']
            break

    signed = sign(tx, script_pubkey)
    print("signed", signed)

    sent = rpc('sendrawtransaction', signed, returns_json=False)
    print(sent)


if __name__ == '__main__':
    main()
