import os
import asyncio
from collections import defaultdict

from aiohttp import web

from electrum.util import log_exceptions, ignore_exceptions
from electrum.logging import Logger
from electrum.util import EventListener
from electrum.lnaddr import lndecode

class SwapServer(Logger, EventListener):
    """
    public API:
    - getpairs
    - createswap
    """

    WWW_DIR = os.path.join(os.path.dirname(__file__), 'www')

    def __init__(self, config, wallet):
        Logger.__init__(self)
        self.config = config
        self.wallet = wallet
        self.sm = self.wallet.lnworker.swap_manager
        self.port = self.config.SWAPSERVER_PORT
        self.register_callbacks() # eventlistener

        self.pending = defaultdict(asyncio.Event)
        self.pending_msg = {}

    @ignore_exceptions
    @log_exceptions
    async def run(self):
        app = web.Application()
        app.add_routes([web.get('/getpairs', self.get_pairs)])
        app.add_routes([web.post('/createswap', self.create_swap)])
        app.add_routes([web.post('/createnormalswap', self.create_normal_swap)])
        app.add_routes([web.post('/addswapinvoice', self.add_swap_invoice)])

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host='localhost', port=self.port)
        await site.start()
        self.logger.info(f"running and listening on port {self.port}")

    async def get_pairs(self, r):
        sm = self.sm
        sm.init_pairs()
        pairs = {
            "info": [],
            "warnings": [],
            "htlcFirst": True,
            "pairs": {
                "BTC/BTC": {
                    "rate": 1,
                    "limits": {
                        "maximal": sm._max_amount,
                        "minimal": sm._min_amount,
                        "maximalZeroConf": {
                            "baseAsset": 0,
                            "quoteAsset": 0
                        }
                    },
                    "fees": {
                        "percentage": 0.5,
                        "minerFees": {
                            "baseAsset": {
                                "normal": sm.normal_fee,
                                "reverse": {
                                    "claim": sm.claim_fee,
                                    "lockup": sm.lockup_fee
                                }
                            },
                            "quoteAsset": {
                                "normal": sm.normal_fee,
                                "reverse": {
                                    "claim": sm.claim_fee,
                                    "lockup": sm.lockup_fee
                                }
                            }
                        }
                    }
                }
            }
        }
        return web.json_response(pairs)

    async def add_swap_invoice(self, r):
        request = await r.json()
        invoice = request['invoice']
        self.sm.add_invoice(invoice, pay_now=True)
        return web.json_response({})

    async def create_normal_swap(self, r):
        # normal for client, reverse for server
        request = await r.json()
        lightning_amount_sat = request['invoiceAmount']
        their_pubkey = bytes.fromhex(request['refundPublicKey'])
        assert len(their_pubkey) == 33
        swap = self.sm.create_reverse_swap(
            payment_hash=None,
            lightning_amount_sat=lightning_amount_sat,
            their_pubkey=their_pubkey
        )
        response = {
            "id": swap.payment_hash.hex(),
            'preimageHash': swap.payment_hash.hex(),
            "acceptZeroConf": False,
            "expectedAmount": swap.onchain_amount,
            "timeoutBlockHeight": swap.locktime,
            "address": swap.lockup_address,
            "redeemScript": swap.redeem_script.hex(),
        }
        return web.json_response(response)

    async def create_swap(self, r):
        self.sm.init_pairs()
        request = await r.json()
        req_type = request['type']
        assert request['pairId'] == 'BTC/BTC'
        if req_type == 'reversesubmarine':
            lightning_amount_sat=request['invoiceAmount']
            payment_hash=bytes.fromhex(request['preimageHash'])
            their_pubkey=bytes.fromhex(request['claimPublicKey'])
            assert len(payment_hash) == 32
            assert len(their_pubkey) == 33
            swap, invoice, prepay_invoice = self.sm.create_normal_swap(
                lightning_amount_sat=lightning_amount_sat,
                payment_hash=payment_hash,
                their_pubkey=their_pubkey
            )
            response = {
                'id': payment_hash.hex(),
                'invoice': invoice,
                'minerFeeInvoice': prepay_invoice,
                'lockupAddress': swap.lockup_address,
                'redeemScript': swap.redeem_script.hex(),
                'timeoutBlockHeight': swap.locktime,
                "onchainAmount": swap.onchain_amount,
            }
        elif req_type == 'submarine':
            # old protocol
            their_invoice=request['invoice']
            their_pubkey=bytes.fromhex(request['refundPublicKey'])
            assert len(their_pubkey) == 33
            lnaddr = lndecode(their_invoice)
            payment_hash = lnaddr.paymenthash
            lightning_amount_sat = int(lnaddr.get_amount_sat()) # should return int
            swap = self.sm.create_reverse_swap(
                lightning_amount_sat=lightning_amount_sat,
                payment_hash=payment_hash,
                their_pubkey=their_pubkey
            )
            self.sm.add_invoice(their_invoice, pay_now=False)
            response = {
                "id": payment_hash.hex(),
                "acceptZeroConf": False,
                "expectedAmount": swap.onchain_amount,
                "timeoutBlockHeight": swap.locktime,
                "address": swap.lockup_address,
                "redeemScript": swap.redeem_script.hex()
            }
        else:
            raise Exception('unsupported request type:' + req_type)
        return web.json_response(response)
