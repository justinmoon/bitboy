import json

from os.path import isfile
from io import BytesIO
from random import randint

from bedrock.tx import Tx, TxIn, TxOut
from bedrock.script import address_to_script_pubkey
from bedrock.helper import sha256
from bedrock.hd import HDPublicKey
from bedrock.helper import encode_varstr

from rpc import WalletRPC, sat_to_btc

import usb

class Wallet:

    filename = "wallet.json"
    export_size = 100

    def __init__(self, xpub, address_index=0):
        self.xpub = xpub
        self.address_index = address_index

    @classmethod
    def create(cls, xpub):  # artificially low for testing
        if isfile(cls.filename):
            raise OSError("wallet file already exists")
        # create watch-only Bitcoin Core wallet
        # WalletRPC('').create_watchonly_wallet('bitboy')  # FIXME
        # export first chunk of receiving & change addresses
        xpub = HDPublicKey.parse(BytesIO(xpub.encode()))
        wallet = cls(xpub)
        wallet.bitcoind_export()
        wallet.save()
        return wallet

    def serialize(self):
        dict = {
            'xpub': self.xpub.xpub(),
            'address_index': self.address_index,
        }
        return json.dumps(dict, indent=4)

    def save(self):
        with open(self.filename, 'w') as f:
            data = self.serialize()
            f.write(data)

    @classmethod
    def deserialize(cls, raw_json):
        data = json.loads(raw_json)
        data['xpub'] = HDPublicKey.parse(BytesIO(data['xpub'].encode()))
        return cls(**data)

    @classmethod
    def open(cls):
        with open(cls.filename, 'r') as f:
            raw_json = f.read()
            wallet = cls.deserialize(raw_json)
            # load associated Bitcoin Core watch-only wallet
            WalletRPC('').load_wallet('bitboy')
            return wallet

    def descriptor(self):
        return f"pkh({self.xpub.xpub()}/*)"

    def bitcoind_export(self):
        descriptor = self.descriptor()
        export_range = (self.address_index, self.address_index + self.export_size)
        WalletRPC('bitboy').export(descriptor, export_range, False)  # FIXME: change=False

    def derive_pubkey(self, address_index):
        path = f"m/{address_index}"
        return self.xpub.traverse(path.encode()), path

    def pubkeys(self):
        keys = []
        for address_index in range(self.address_index):
            key, path = self.derive_pubkey(address_index)
            keys.append((key, path))
        return keys

    def lookup_pubkey(self, address):
        for pubkey, path in self.pubkeys():
            if pubkey.point.address(testnet=True) == address:
                return pubkey, path
        return None, None

    def addresses(self):
        return [pubkey.point.address(testnet=True) for key, path in self.pubkeys()]

    def consume_address(self):
        if self.address_index % self.export_size == 0:
            self.bitcoind_export()
        self.address_index += 1
        pubkey, path = self.derive_pubkey(self.address_index)
        self.save()
        return pubkey.point.address(testnet=True)

    def balance(self):
        return WalletRPC('bitboy').get_balance()

    def unspent(self):
        return WalletRPC('bitboy').get_unspent()

    def transactions(self):
        return WalletRPC('bitboy').get_transactions()

    def prepare_tx(self, address, amount, fee):
        # FIXME: amount -> satoshis
        rpc = WalletRPC('bitboy')

        # create unfunded transaction
        tx_ins = []
        tx_outs = [
            {address: sat_to_btc(amount)},
        ]
        rawtx = rpc.create_raw_transaction(tx_ins, tx_outs)
        
        # fund it
        change_address = self.consume_address()
        fundedtx = rpc.fund_raw_transaction(rawtx, change_address)

        # input metadata
        input_meta = []
        decoded = rpc.rpc().decoderawtransaction(fundedtx)
        for tx_in in decoded['vin']:
            print('iterate input')
            tx_id = tx_in['txid']
            tx_index = tx_in['vout']
            prev_tx = rpc.rpc().getrawtransaction(tx_id, True)
            script_pubkey = encode_varstr(bytes.fromhex(prev_tx['vout'][tx_index]['scriptPubKey']['hex'])).hex()
            input_address = prev_tx['vout'][tx_index]['scriptPubKey']['addresses'][0]
            pubkey, path = self.lookup_pubkey(input_address)
            derivation_path = f"m/69'/{path[2:]}"
            print('PATH', derivation_path)
            input_meta = [{'script_pubkey': script_pubkey, 'derivation_path': derivation_path}]

        # output metadata
        output_meta = []
        for tx_out in decoded['vout']:
            print('iterate output')
            address = tx_out['scriptPubKey']['addresses'][0]
            pubkey, path = self.lookup_pubkey(address)
            if path is None:
                output_meta.append({'change': False})
            else:
                derivation_path = f"m/69'/{path[2:]}"
                output_meta.append({'change': True, 'derivation_path': derivation_path})

        return fundedtx, input_meta, output_meta

    def send(self, address, amount, fee):
        # FIXME: what about QR?
        funded_tx, input_meta, output_meta = self.prepare_tx(address, amount, fee)
                
        # send to device 
        # TODO: handle failure
        print('sending to device')
        signed = usb.sign(fundedtx, input_meta, output_meta)

        # broadcast
        return rpc.broadcast(signed)

