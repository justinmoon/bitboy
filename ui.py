from flask import Flask, render_template, request, redirect, url_for
from flask_qrcode import QRcode
from wallet import Wallet
from bedrock.tx import Tx
from bedrock.script import Script
from io import BytesIO
import json
from rpc import WalletRPC

app = Flask(__name__)
QRcode(app)


@app.route("/create-transaction", methods=['GET', 'POST'])
def create_transaction():
    wallet = Wallet.open()
    if request.method == 'GET':
        if wallet.tx_data is not None:
            msg = json.dumps(wallet.tx_data)
        else:
            msg = None
    else:
        wallet = Wallet.open()
        wallet.start_tx(
            request.form['recipient'], int(request.form['satoshis']), 300
        )
        msg = json.dumps(wallet.tx_data)
    return render_template('create-transaction.html', msg=msg)

@app.route("/scan-xpub", methods=['GET', 'POST'])
def scan_xpub():
    if request.method == 'GET':
        return render_template('scan-xpub.html')
    else:
        print(request.json)
        Wallet.create(request.json['xpub'])
        return 'ok', 200

@app.route("/address")
def address():
    wallet = Wallet.open()
    return wallet.consume_address(), 200

@app.route("/add-signature", methods=['GET', 'POST'])
def add_signature():
    if request.method == 'GET':
        return render_template('add-signature.html')
    else:
        wallet = Wallet.open()
        script_sig = Script.parse(BytesIO(bytes.fromhex(request.json['signature'])))
        tx = Tx.parse(BytesIO(bytes.fromhex(wallet.tx_data['tx'])))
        for i, tx_in in enumerate(tx.tx_ins):
            if tx_in.script_sig.cmds == []:
                tx.tx_ins[i].script_sig = script_sig
                print('filled in script sig')
                break
        # FIXME: for some reason script_sig is None ...
        if all([tx_in.script_sig.cmds != [] for tx_in in tx.tx_ins]):
            rpc = WalletRPC('bitboy')
            print(tx.serialize().hex())
            rpc.broadcast(tx.serialize().hex())
            print('broadcasted')
            # wallet.tx_data = None
            # FIXME
            return tx.id()
        wallet.save()
        return 'ok'

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True, port=9999)
