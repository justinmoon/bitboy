import time
import logging
from io import BytesIO
from decimal import Decimal
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
from bedrock.tx import Tx

logger = logging.getLogger(__name__)

COIN_PER_SAT = Decimal(10) ** -8
SAT_PER_COIN = 100_000_000

def btc_to_sat(btc):
    return int(btc*SAT_PER_COIN)

def sat_to_btc(sat):
    return Decimal(sat/100_000_000).quantize(COIN_PER_SAT)

class WalletRPC:
    
    def __init__(self, account_name):
        self.wallet_name = account_name

    def rpc(self):
        rpc_template = "http://%s:%s@%s:%s/wallet/%s"
        url = rpc_template % ('bitcoin', 'python', 'localhost', 18332, self.wallet_name)
        return AuthServiceProxy(url, timeout=60*5)  # 5 minute timeouts
    
    def load_wallet(self, account_name):
        try:
            return self.rpc().loadwallet(account_name)
        except JSONRPCException:
            logger.debug(f'"{account_name}" wallet already loaded')
    
    def create_watchonly_wallet(self, account_name):
        watchonly = True
        return self.rpc().createwallet(account_name, watchonly)

    def export(self, descriptor, range, change):
        # validate descriptor
        descriptor = self.rpc().getdescriptorinfo(descriptor)['descriptor']
        # export descriptor
        self.rpc().importmulti([{
            # description of the keys we're exporting
            "desc": descriptor,
            # go this far back in blockchain looking for matching outputs
            "timestamp": int(time.time() - 60*60*24*30),  # 30 days
            # this range kinda get filled into the * in the descriptor
            "range": range,
            # matching outputs will be marked "watchonly" meaning bitcoind's wallet can't spend them
            "watchonly": True,
            # bitcoind shouldn't use these addresses when we request an address from it
            "keypool": False,
            # whether it's a change address
            "internal": change,
        }])
        logger.debug(f'bitcoind export successful: descriptor={descriptor} range={range}')

    def get_balance(self):
        confirmed = self.rpc().getbalance('*', 1, True)
        unconfirmed = self.rpc().getbalance('*', 0, True) - confirmed
        return btc_to_sat(unconfirmed), btc_to_sat(confirmed)

    def get_transactions(self):
        return self.rpc().listtransactions('*', 10, 0, True)

    def get_unspent(self):
        return self.rpc().listunspent()

    def create_raw_transaction(self, tx_ins, tx_outs):
        return self.rpc().createrawtransaction(tx_ins, tx_outs)

    def fund_raw_transaction(self, rawtx, change_address):
        options = {'changeAddress': change_address, 'includeWatching': True}
        return self.rpc().fundrawtransaction(rawtx, options)['hex']

    def get_address_for_outpoint(self, txid, index):
        rawtx = self.rpc().gettransaction(txid)['hex']
        tx = Tx.parse(BytesIO(bytes.fromhex(rawtx)))
        tx_out = tx.tx_outs[index]
        script_pubkey = tx_out.script_pubkey
        return script_pubkey.address(testnet=True)

    def broadcast(self, rawtx):
        return self.rpc().sendrawtransaction(rawtx)
