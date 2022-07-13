from typing import Optional, TYPE_CHECKING, Sequence, List, Union
import queue
import time
import asyncio
import threading

from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject, QUrl, QTimer

from electrum.i18n import _
from electrum.util import (Satoshis, format_time, parse_max_spend, InvalidPassword,
                           event_listener)
from electrum.logging import get_logger
from electrum.wallet import Wallet, Abstract_Wallet
from electrum.storage import StorageEncryptionVersion
from electrum import bitcoin
from electrum.transaction import PartialTxOutput
from electrum.invoices import (Invoice, InvoiceError,
                               PR_DEFAULT_EXPIRATION_WHEN_CREATING, PR_PAID,
                               PR_UNPAID, PR_UNKNOWN, PR_EXPIRED, PR_UNCONFIRMED)
from electrum.network import TxBroadcastError, BestEffortRequestFailed

from .qeinvoicelistmodel import QEInvoiceListModel, QERequestListModel
from .qetransactionlistmodel import QETransactionListModel
from .qeaddresslistmodel import QEAddressListModel
from .qechannellistmodel import QEChannelListModel
from .qetypes import QEAmount
from .auth import AuthMixin, auth_protect
from .util import QtEventListener, qt_event_listener

class QEWallet(AuthMixin, QObject, QtEventListener):
    __instances = []

    # this factory method should be used to instantiate QEWallet
    # so we have only one QEWallet for each electrum.wallet
    @classmethod
    def getInstanceFor(cls, wallet):
        for i in cls.__instances:
            if i.wallet == wallet:
                return i
        i = QEWallet(wallet)
        cls.__instances.append(i)
        return i

    _logger = get_logger(__name__)

    # emitted when wallet wants to display a user notification
    # actual presentation should be handled on app or window level
    userNotify = pyqtSignal(object, object)

    # shared signal for many static wallet properties
    dataChanged = pyqtSignal()

    isUptodateChanged = pyqtSignal()
    requestStatusChanged = pyqtSignal([str,int], arguments=['key','status'])
    requestCreateSuccess = pyqtSignal()
    requestCreateError = pyqtSignal([str,str], arguments=['code','error'])
    invoiceStatusChanged = pyqtSignal([str,int], arguments=['key','status'])
    invoiceCreateSuccess = pyqtSignal()
    invoiceCreateError = pyqtSignal([str,str], arguments=['code','error'])
    paymentSucceeded = pyqtSignal([str], arguments=['key'])
    paymentFailed = pyqtSignal([str,str], arguments=['key','reason'])
    requestNewPassword = pyqtSignal()

    _network_signal = pyqtSignal(str, object)

    def __init__(self, wallet, parent=None):
        super().__init__(parent)
        self.wallet = wallet

        self._historyModel = None
        self._addressModel = None
        self._requestModel = None
        self._invoiceModel = None
        self._channelModel = None

        self.tx_notification_queue = queue.Queue()
        self.tx_notification_last_time = 0

        self.notification_timer = QTimer(self)
        self.notification_timer.setSingleShot(False)
        self.notification_timer.setInterval(500)  # msec
        self.notification_timer.timeout.connect(self.notify_transactions)

        #self._network_signal.connect(self.on_network_qt)
        interests = ['wallet_updated', 'new_transaction', 'status', 'verified',
                     'on_history', 'channel', 'channels_updated', 'payment_failed',
                     'payment_succeeded', 'invoice_status', 'request_status']
        # To avoid leaking references to "self" that prevent the
        # window from being GC-ed when closed, callbacks should be
        # methods of this class only, and specifically not be
        # partials, lambdas or methods of subobjects.  Hence...
        #register_callback(self.on_network, interests)
        self.register_callbacks()
        self.destroyed.connect(lambda: self.on_destroy())

    @pyqtProperty(bool, notify=isUptodateChanged)
    def isUptodate(self):
        return self.wallet.is_up_to_date()

    def on_network(self, event, *args):
        if event in ['new_transaction', 'payment_succeeded']:
            # Handle in GUI thread (_network_signal -> on_network_qt)
            self._network_signal.emit(event, args)
        else:
            self.on_network_qt(event, args)

    def on_network_qt(self, event, args=None):
        # note: we get events from all wallets! args are heterogenous so we can't
        # shortcut here
        if event != 'status':
            wallet = args[0]
            if wallet == self.wallet:
                self._logger.debug('event %s' % event)

    @event_listener
    def on_event_status(self, *args, **kwargs):
        #if event == 'status':
            self.isUptodateChanged.emit()


    #    elif event == 'request_status':
    @event_listener
    def on_event_request_status(self, wallet, key, status):
            #wallet, key, status = args
        if wallet == self.wallet:
            self._logger.debug('request status %d for key %s' % (status, key))
            self.requestStatusChanged.emit(key, status)
    #    elif event == 'invoice_status':
    @event_listener
    def on_event_invoice_status(self, wallet, key):
            #wallet, key = args
        if wallet == self.wallet:
            self._logger.debug('invoice status update for key %s' % key)
            # FIXME event doesn't pass the new status, so we need to retrieve
            invoice = self.wallet.get_invoice(key)
            if invoice:
                status = self.wallet.get_invoice_status(invoice)
                self.invoiceStatusChanged.emit(key, status)
            else:
                self._logger.debug(f'No invoice found for key {key}')

        #elif event == 'new_transaction':
    @qt_event_listener
    def on_event_new_transaction(self, *args):
        wallet, tx = args
        if wallet == self.wallet:
            self.add_tx_notification(tx)
            self.historyModel.init_model() # TODO: be less dramatic


    #    elif event == 'verified':
    @qt_event_listener
    def on_event_verified(self, wallet, txid, info):
            #wallet, txid, info = args
        if wallet == self.wallet:
            self.historyModel.update_tx(txid, info)


    #    elif event == 'wallet_updated':
    @event_listener
    def on_event_wallet_updated(self, wallet):
            #wallet, = args
        if wallet == self.wallet:
            self._logger.debug('wallet %s updated' % str(wallet))
            self.balanceChanged.emit()

    #    elif event == 'channel':
    @event_listener
    def on_event_channel(self, wallet, channel):
            #wallet, channel = args
            if wallet == self.wallet:
                self.balanceChanged.emit()

    #    elif event == 'channels_updated':
    @event_listener
    def on_event_channels_updated(self, wallet):
            #wallet, = args
        if wallet == self.wallet:
            self.balanceChanged.emit()
    #    elif event == 'payment_succeeded':

    @qt_event_listener
    def on_event_payment_succeeded(self, wallet, key):
            #wallet, key = args
        if wallet == self.wallet:
            self.paymentSucceeded.emit(key)
            self.historyModel.init_model() # TODO: be less dramatic

    #    elif event == 'payment_failed':
    @event_listener
    def on_event_payment_failed(self, wallet, key, reason):
            #wallet, key, reason = args
        if wallet == self.wallet:
            self.paymentFailed.emit(key, reason)
        #else:
            #self._logger.debug('unhandled event: %s %s' % (event, str(args)))

    def on_destroy(self):
        #unregister_callback(self.on_network)
        self.unregister_callbacks()

    def add_tx_notification(self, tx):
        self._logger.debug('new transaction event')
        self.tx_notification_queue.put(tx)
        if not self.notification_timer.isActive():
            self._logger.debug('starting wallet notification timer')
            self.notification_timer.start()

    def notify_transactions(self):
        if self.tx_notification_queue.qsize() == 0:
            self._logger.debug('queue empty, stopping wallet notification timer')
            self.notification_timer.stop()
            return
        if not self.wallet.is_up_to_date():
            return  # no notifications while syncing
        now = time.time()
        rate_limit = 20  # seconds
        if self.tx_notification_last_time + rate_limit > now:
            return
        self.tx_notification_last_time = now
        self._logger.info("Notifying app about new transactions")
        txns = []
        while True:
            try:
                txns.append(self.tx_notification_queue.get_nowait())
            except queue.Empty:
                break

        config = self.wallet.config
        # Combine the transactions if there are at least three
        if len(txns) >= 3:
            total_amount = 0
            for tx in txns:
                tx_wallet_delta = self.wallet.get_wallet_delta(tx)
                if not tx_wallet_delta.is_relevant:
                    continue
                total_amount += tx_wallet_delta.delta
            self.userNotify.emit(self.wallet, _("{} new transactions: Total amount received in the new transactions {}").format(len(txns), config.format_amount_and_units(total_amount)))
        else:
            for tx in txns:
                tx_wallet_delta = self.wallet.get_wallet_delta(tx)
                if not tx_wallet_delta.is_relevant:
                    continue
                self.userNotify.emit(self.wallet,
                    _("New transaction: {}").format(config.format_amount_and_units(tx_wallet_delta.delta)))

    historyModelChanged = pyqtSignal()
    @pyqtProperty(QETransactionListModel, notify=historyModelChanged)
    def historyModel(self):
        if self._historyModel is None:
            self._historyModel = QETransactionListModel(self.wallet)
        return self._historyModel

    addressModelChanged = pyqtSignal()
    @pyqtProperty(QEAddressListModel, notify=addressModelChanged)
    def addressModel(self):
        if self._addressModel is None:
            self._addressModel = QEAddressListModel(self.wallet)
        return self._addressModel

    requestModelChanged = pyqtSignal()
    @pyqtProperty(QERequestListModel, notify=requestModelChanged)
    def requestModel(self):
        if self._requestModel is None:
            self._requestModel = QERequestListModel(self.wallet)
        return self._requestModel

    invoiceModelChanged = pyqtSignal()
    @pyqtProperty(QEInvoiceListModel, notify=invoiceModelChanged)
    def invoiceModel(self):
        if self._invoiceModel is None:
            self._invoiceModel = QEInvoiceListModel(self.wallet)
        return self._invoiceModel

    channelModelChanged = pyqtSignal()
    @pyqtProperty(QEChannelListModel, notify=channelModelChanged)
    def channelModel(self):
        if self._channelModel is None:
            self._channelModel = QEChannelListModel(self.wallet)
        return self._channelModel

    nameChanged = pyqtSignal()
    @pyqtProperty(str, notify=nameChanged)
    def name(self):
        return self.wallet.basename()

    isLightningChanged = pyqtSignal()
    @pyqtProperty(bool, notify=isLightningChanged)
    def isLightning(self):
        return bool(self.wallet.lnworker)

    @pyqtProperty(bool, notify=dataChanged)
    def canHaveLightning(self):
        return self.wallet.can_have_lightning()

    @pyqtProperty(bool, notify=dataChanged)
    def hasSeed(self):
        return self.wallet.has_seed()

    @pyqtProperty(str, notify=dataChanged)
    def txinType(self):
        return self.wallet.get_txin_type(self.wallet.dummy_address())

    @pyqtProperty(bool, notify=dataChanged)
    def isWatchOnly(self):
        return self.wallet.is_watching_only()

    @pyqtProperty(bool, notify=dataChanged)
    def isDeterministic(self):
        return self.wallet.is_deterministic()

    @pyqtProperty(bool, notify=dataChanged)
    def isEncrypted(self):
        return self.wallet.storage.is_encrypted()

    @pyqtProperty(bool, notify=dataChanged)
    def isHardware(self):
        return self.wallet.storage.is_encrypted_with_hw_device()

    @pyqtProperty(str, notify=dataChanged)
    def derivationPrefix(self):
        keystores = self.wallet.get_keystores()
        if len(keystores) > 1:
            self._logger.debug('multiple keystores not supported yet')
        return keystores[0].get_derivation_prefix()

    @pyqtProperty(str, notify=dataChanged)
    def masterPubkey(self):
        return self.wallet.get_master_public_key()

    balanceChanged = pyqtSignal()

    @pyqtProperty(QEAmount, notify=balanceChanged)
    def frozenBalance(self):
        c, u, x = self.wallet.get_frozen_balance()
        self._frozenbalance = QEAmount(amount_sat=c+x)
        return self._frozenbalance

    @pyqtProperty(QEAmount, notify=balanceChanged)
    def unconfirmedBalance(self):
        self._unconfirmedbalance = QEAmount(amount_sat=self.wallet.get_balance()[1])
        return self._unconfirmedbalance

    @pyqtProperty(QEAmount, notify=balanceChanged)
    def confirmedBalance(self):
        c, u, x = self.wallet.get_balance()
        self._confirmedbalance = QEAmount(amount_sat=c+x)
        return self._confirmedbalance

    @pyqtProperty(QEAmount, notify=balanceChanged)
    def lightningBalance(self):
        if not self.isLightning:
            self._lightningbalance = QEAmount()
        else:
            self._lightningbalance = QEAmount(amount_sat=int(self.wallet.lnworker.get_balance()))
        return self._lightningbalance

    @pyqtProperty(QEAmount, notify=balanceChanged)
    def lightningCanSend(self):
        if not self.isLightning:
            self._lightningcansend = QEAmount()
        else:
            self._lightningcansend = QEAmount(amount_sat=int(self.wallet.lnworker.num_sats_can_send()))
        return self._lightningcansend

    @pyqtProperty(QEAmount, notify=balanceChanged)
    def lightningCanReceive(self):
        if not self.isLightning:
            self._lightningcanreceive = QEAmount()
        else:
            self._lightningcanreceive = QEAmount(amount_sat=int(self.wallet.lnworker.num_sats_can_receive()))
        return self._lightningcanreceive

    @pyqtSlot()
    def enableLightning(self):
        self.wallet.init_lightning(password=None) # TODO pass password if needed
        self.isLightningChanged.emit()

    @pyqtSlot(str, int, int, bool)
    def send_onchain(self, address, amount, fee=None, rbf=False):
        self._logger.info('send_onchain: %s %d' % (address,amount))
        coins = self.wallet.get_spendable_coins(None)
        if not bitcoin.is_address(address):
            self._logger.warning('Invalid Bitcoin Address: ' + address)
            return False

        outputs = [PartialTxOutput.from_address_and_value(address, amount)]
        self._logger.info(str(outputs))
        output_values = [x.value for x in outputs]
        if any(parse_max_spend(outval) for outval in output_values):
            output_value = '!'
        else:
            output_value = sum(output_values)
        self._logger.info(str(output_value))
        # see qt/confirm_tx_dialog qt/main_window
        tx = self.wallet.make_unsigned_transaction(coins=coins,outputs=outputs, fee=None)
        self._logger.info(str(tx.to_json()))

        use_rbf = bool(self.wallet.config.get('use_rbf', True))
        tx.set_rbf(use_rbf)
        self.sign_and_broadcast(tx)

    @auth_protect
    def sign_and_broadcast(self, tx):
        def cb(result):
            self._logger.info('signing was succesful? %s' % str(result))
        tx = self.wallet.sign_transaction(tx, None)
        if not tx.is_complete():
            self._logger.info('tx not complete')
            return

        self.network = self.wallet.network # TODO not always defined?

        try:
            self._logger.info('running broadcast in thread')
            self.network.run_from_another_thread(self.network.broadcast_transaction(tx))
            self._logger.info('broadcast submit done')
        except TxBroadcastError as e:
            self._logger.info(e)
            return
        except BestEffortRequestFailed as e:
            self._logger.info(e)
            return

        return

    paymentAuthRejected = pyqtSignal()
    def ln_auth_rejected(self):
        self.paymentAuthRejected.emit()

    @pyqtSlot(str)
    @auth_protect(reject='ln_auth_rejected')
    def pay_lightning_invoice(self, invoice_key):
        self._logger.debug('about to pay LN')
        invoice = self.wallet.get_invoice(invoice_key)
        assert(invoice)
        assert(invoice.lightning_invoice)

        amount_msat = invoice.get_amount_msat()

        def pay_thread():
            try:
                coro = self.wallet.lnworker.pay_invoice(invoice.lightning_invoice, amount_msat=amount_msat)
                fut = asyncio.run_coroutine_threadsafe(coro, self.wallet.network.asyncio_loop)
                fut.result()
            except Exception as e:
                self.userNotify.emit(repr(e))

        threading.Thread(target=pay_thread).start()

    def create_bitcoin_request(self, amount: int, message: str, expiration: int, ignore_gap: bool) -> Optional[str]:
        addr = self.wallet.get_unused_address()
        if addr is None:
            if not self.wallet.is_deterministic():  # imported wallet
                # TODO implement
                return
                #msg = [
                    #_('No more addresses in your wallet.'), ' ',
                    #_('You are using a non-deterministic wallet, which cannot create new addresses.'), ' ',
                    #_('If you want to create new addresses, use a deterministic wallet instead.'), '\n\n',
                    #_('Creating a new payment request will reuse one of your addresses and overwrite an existing request. Continue anyway?'),
                   #]
                #if not self.question(''.join(msg)):
                    #return
                #addr = self.wallet.get_receiving_address()
            else:  # deterministic wallet
                if not ignore_gap:
                    self.requestCreateError.emit('gaplimit',_("Warning: The next address will not be recovered automatically if you restore your wallet from seed; you may need to add it manually.\n\nThis occurs because you have too many unused addresses in your wallet. To avoid this situation, use the existing addresses first.\n\nCreate anyway?"))
                    return
                addr = self.wallet.create_new_address(False)

        req_key = self.wallet.create_request(amount, message, expiration, addr)
        #try:
            #self.wallet.add_payment_request(req)
        #except Exception as e:
            #self.logger.exception('Error adding payment request')
            #self.requestCreateError.emit('fatal',_('Error adding payment request') + ':\n' + repr(e))
        #else:
            ## TODO: check this flow. Only if alias is defined in config. OpenAlias?
            #pass
            ##self.sign_payment_request(addr)

        return req_key, addr

    @pyqtSlot(QEAmount, str, int)
    @pyqtSlot(QEAmount, str, int, bool)
    @pyqtSlot(QEAmount, str, int, bool, bool)
    def create_request(self, amount: QEAmount, message: str, expiration: int, is_lightning: bool = False, ignore_gap: bool = False):
        # TODO: unify this method and create_bitcoin_request
        try:
            if is_lightning:
                if not self.wallet.lnworker.channels:
                    self.requestCreateError.emit('fatal',_("You need to open a Lightning channel first."))
                    return
                # TODO maybe show a warning if amount exceeds lnworker.num_sats_can_receive (as in kivy)
                # TODO fallback address robustness
                addr = self.wallet.get_unused_address()
                key = self.wallet.create_request(amount.satsInt, message, expiration, addr)
            else:
                key, addr = self.create_bitcoin_request(amount.satsInt, message, expiration, ignore_gap)
                if not key:
                    return
                self.addressModel.init_model()
        except InvoiceError as e:
            self.requestCreateError.emit('fatal',_('Error creating payment request') + ':\n' + str(e))
            return

        assert key is not None
        self._requestModel.add_invoice(self.wallet.get_request(key))
        self.requestCreateSuccess.emit()

    @pyqtSlot(str)
    def delete_request(self, key: str):
        self._logger.debug('delete req %s' % key)
        self.wallet.delete_request(key)
        self._requestModel.delete_invoice(key)

    @pyqtSlot(str, result='QVariant')
    def get_request(self, key: str):
        return self._requestModel.get_model_invoice(key)

    @pyqtSlot(str)
    def delete_invoice(self, key: str):
        self._logger.debug('delete inv %s' % key)
        self.wallet.delete_invoice(key)
        self._invoiceModel.delete_invoice(key)

    @pyqtSlot(str, result='QVariant')
    def get_invoice(self, key: str):
        return self._invoiceModel.get_model_invoice(key)

    @pyqtSlot(str, result=bool)
    def verify_password(self, password):
        try:
            self.wallet.storage.check_password(password)
            return True
        except InvalidPassword as e:
            return False

    @pyqtSlot(str)
    def set_password(self, password):
        storage = self.wallet.storage

        # HW wallet not supported yet
        if storage.is_encrypted_with_hw_device():
            return

        self._logger.debug('Ok to set password for wallet with path %s' % storage.path)
        if password:
            enc_version = StorageEncryptionVersion.USER_PASSWORD
        else:
            enc_version = StorageEncryptionVersion.PLAINTEXT
        storage.set_password(password, enc_version=enc_version)
        self.wallet.save_db()
