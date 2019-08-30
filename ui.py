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

tx = None

@app.route("/", methods=['GET', 'POST'])
def home():
    global tx
    if request.method == 'GET':
        msg = ''
        return render_template('home.html', msg=msg)
    else:
        wallet = Wallet.open()
        rawtx, input_meta, output_meta = wallet.prepare_tx(
            request.form['recipient'], int(request.form['satoshis']), 300
        )
        msg = json.dumps({'tx': rawtx,'input_meta': input_meta,'output_meta': output_meta})
        tx = Tx.parse(BytesIO(bytes.fromhex(rawtx)))
        return render_template('home.html', msg=msg)


@app.route("/xpub", methods=['POST'])
def receive_xpub():
    print(request.json)
    Wallet.create(request.json['xpub'])
    return render_template('home.html')

@app.route("/address")
def address():
    wallet = Wallet.open()
    return wallet.consume_address(), 200

@app.route("/signature", methods=['POST'])
def receive_signature():
    global tx
    script_sig = Script.parse(BytesIO(bytes.fromhex(request.json['signature'])))
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
    # json post
    # return whether we're done signing or not ...
    return render_template('home.html')

if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True, port=9999)
