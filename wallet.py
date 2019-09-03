import json

from os.path import isfile
from io import BytesIO
from random import randint

from hwilib.serializations import PSBT

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

    def __init__(self, xpub, address_index=0, psbt=None):
        self.xpub = xpub
        self.address_index = address_index
        self.psbt = psbt

    @classmethod
    def create(cls, xpub=None):
        if isfile(cls.filename):
            raise OSError("wallet file already exists")
        xpub = HDPublicKey.parse(BytesIO(xpub.encode()))
        WalletRPC('').create_watchonly_wallet('bitboy')
        wallet = cls(xpub)
        wallet.bitcoind_export()
        wallet.save()
        return wallet

    def serialize(self):
        dict = {
            'xpub': self.xpub.xpub(),
            'address_index': self.address_index,
            'psbt': self.psbt.serialize() if self.psbt else '',
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
        if data['psbt'] != '':
            psbt = PSBT()
            psbt.deserialize(data['psbt'])
            data['psbt'] = psbt
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
        rpc = WalletRPC('bitboy')
        rpc.export(descriptor, export_range, False)  # FIXME: change=False
        # FIXME: hackily update address index based on unspent descriptors ...
        # this could miss spent transactions ...
        # FIXME: skips exports between old and new index
        unspent = rpc.rpc().listunspent(0, 9999999, [], True)
        for u in unspent:
            desc = u['desc']
            ai = int(desc[desc.find('/')+1:desc.find(']')])
            self.address_index = max(self.address_index, ai+1)
        self.save()

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
        return [pubkey.point.address(testnet=True) for pubkey, path in self.pubkeys()]

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
        rpc = WalletRPC('bitboy').rpc()

        # fund it
        change_address = self.consume_address()
        raw_psbt = rpc.walletcreatefundedpsbt(
            # let Bitcoin Core choose inputs
            [],
            # Outputs
            [{address: sat_to_btc(amount)}],
            # Locktime
            0,
            {
                # Include watch-only outputs
                "includeWatching": True,
                # Provide change address b/c Core can't generate it
                "changeAddress": change_address,
            },
            # Include BIP32 derivation paths in the PSBT
            True,
        )['psbt']
        psbt = PSBT()
        psbt.deserialize(raw_psbt)
        return psbt

    def start_tx(self, address, amount, fee):
        self.psbt = self.prepare_tx(address, amount, fee)
        self.save()

    def send(self, address, amount, fee):
        # FIXME: what about QR?
        funded_tx, input_meta, output_meta = self.prepare_tx(address, amount, fee)
                
        # send to device 
        # TODO: handle failure
        print('sending to device')
        signed = usb.sign(fundedtx, input_meta, output_meta)

        # broadcast
        return rpc.broadcast(signed)

    def balance(self):
        unconfirmed_balance = 0
        confirmed_balance = 0
        unspent = WalletRPC('bitboy').listunspent(0, 9999999, [], True)
        for u in unspent:
            if u['confirmations'] > 0:
                confirmed_balance += u['amount']
            else:
                unconfirmed_balance += u['amount']
        return unconfirmed_balance, confirmed_balance


