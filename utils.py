from bitcoinrpc.authproxy import AuthServiceProxy
from serial.tools import list_ports


def find_port():
    ports = list(list_ports.grep('CP2104 USB to UART Bridge Controller'))
    if len(ports) > 1:
        raise OSError("too many devices plugged in")
    elif len(ports) == 0:
        raise OSError("no device plugged in")
    else:
        return ports[0].device


class RPC:

    def __init__(self, uri):
        self.rpc = AuthServiceProxy(uri)

    def __getattr__(self, name):
        """Hack to establish a new AuthServiceProxy every time this is called"""
        return getattr(self.rpc, name)


rpc_template = "http://%s:%s@%s:%s"
mainnet = RPC(rpc_template % ('bitcoin', 'python', 'localhost', 8332))
testnet = RPC(rpc_template % ('bitcoin', 'python', 'localhost', 18332))

# regtest
rpc_template = "http://%s:%s@%s:%s/wallet/%s"
regtest = RPC(rpc_template % ('bitcoin', 'python', 'localhost', 18332, ''))
regtest_bitboy = RPC(rpc_template % ('bitcoin', 'python', 'localhost', 18332, 'bitboy'))
