from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from electrum.i18n import _
from electrum.logging import get_logger
from electrum.util import format_time, AddTransactionException
from electrum.transaction import tx_from_any

from .qewallet import QEWallet
from .qetypes import QEAmount
from .util import QtEventListener, event_listener

class QETxDetails(QObject, QtEventListener):
    _logger = get_logger(__name__)

    confirmRemoveLocalTx = pyqtSignal([str], arguments=['message'])
    saveTxError = pyqtSignal([str,str], arguments=['code', 'message'])
    saveTxSuccess = pyqtSignal()

    detailsChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.register_callbacks()
        self.destroyed.connect(lambda: self.on_destroy())

        self._wallet = None
        self._txid = ''
        self._rawtx = ''
        self._label = ''

        self._tx = None

        self._status = ''
        self._amount = QEAmount()
        self._lnamount = QEAmount()
        self._fee = QEAmount()
        self._inputs = []
        self._outputs = []

        self._is_lightning_funding_tx = False
        self._can_bump = False
        self._can_dscancel = False
        self._can_broadcast = False
        self._can_cpfp = False
        self._can_save_as_local = False
        self._can_remove = False
        self._can_sign = False
        self._is_unrelated = False
        self._is_complete = False
        self._is_mined = False
        self._is_final = False

        self._mempool_depth = ''

        self._date = ''
        self._height = 0
        self._confirmations = 0
        self._txpos = -1
        self._header_hash = ''

    def on_destroy(self):
        self.unregister_callbacks()

    @event_listener
    def on_event_verified(self, wallet, txid, info):
        if wallet == self._wallet.wallet and txid == self._txid:
            self._logger.debug('verified event for our txid %s' % txid)
            self.update()

    walletChanged = pyqtSignal()
    @pyqtProperty(QEWallet, notify=walletChanged)
    def wallet(self):
        return self._wallet

    @wallet.setter
    def wallet(self, wallet: QEWallet):
        if self._wallet != wallet:
            self._wallet = wallet
            self.walletChanged.emit()

    txidChanged = pyqtSignal()
    @pyqtProperty(str, notify=txidChanged)
    def txid(self):
        return self._txid

    @txid.setter
    def txid(self, txid: str):
        if self._txid != txid:
            self._logger.debug('txid set -> %s' % txid)
            self._txid = txid
            self.txidChanged.emit()
            self.update()

    @pyqtProperty(str, notify=detailsChanged)
    def rawtx(self):
        return self._rawtx

    @rawtx.setter
    def rawtx(self, rawtx: str):
        if self._rawtx != rawtx:
            self._logger.debug('rawtx set -> %s' % rawtx)
            self._rawtx = rawtx
            if not rawtx:
                return
            try:
                self._tx = tx_from_any(rawtx, deserialize=True)
                self.txid = self._tx.txid() # triggers update()
            except Exception as e:
                self._tx = None
                self._logger.error(repr(e))

    labelChanged = pyqtSignal()
    @pyqtProperty(str, notify=labelChanged)
    def label(self):
        return self._label

    @pyqtSlot(str)
    def set_label(self, label: str):
        if label != self._label:
            self._wallet.wallet.set_label(self._txid, label)
            self._label = label
            self.labelChanged.emit()

    @pyqtProperty(str, notify=detailsChanged)
    def status(self):
        return self._status

    @pyqtProperty(QEAmount, notify=detailsChanged)
    def amount(self):
        return self._amount

    @pyqtProperty(QEAmount, notify=detailsChanged)
    def lnAmount(self):
        return self._lnamount

    @pyqtProperty(QEAmount, notify=detailsChanged)
    def fee(self):
        return self._fee

    @pyqtProperty('QVariantList', notify=detailsChanged)
    def inputs(self):
        return self._inputs

    @pyqtProperty('QVariantList', notify=detailsChanged)
    def outputs(self):
        return self._outputs

    @pyqtProperty(bool, notify=detailsChanged)
    def isMined(self):
        return self._is_mined

    @pyqtProperty(str, notify=detailsChanged)
    def mempoolDepth(self):
        return self._mempool_depth

    @pyqtProperty(str, notify=detailsChanged)
    def date(self):
        return self._date

    @pyqtProperty(int, notify=detailsChanged)
    def height(self):
        return self._height

    @pyqtProperty(int, notify=detailsChanged)
    def confirmations(self):
        return self._confirmations

    @pyqtProperty(int, notify=detailsChanged)
    def txpos(self):
        return self._txpos

    @pyqtProperty(str, notify=detailsChanged)
    def headerHash(self):
        return self._header_hash

    @pyqtProperty(bool, notify=detailsChanged)
    def isLightningFundingTx(self):
        return self._is_lightning_funding_tx

    @pyqtProperty(bool, notify=detailsChanged)
    def canBump(self):
        return self._can_bump

    @pyqtProperty(bool, notify=detailsChanged)
    def canCancel(self):
        return self._can_dscancel

    @pyqtProperty(bool, notify=detailsChanged)
    def canBroadcast(self):
        return self._can_broadcast

    @pyqtProperty(bool, notify=detailsChanged)
    def canCpfp(self):
        return self._can_cpfp

    @pyqtProperty(bool, notify=detailsChanged)
    def canSaveAsLocal(self):
        return self._can_save_as_local

    @pyqtProperty(bool, notify=detailsChanged)
    def canRemove(self):
        return self._can_remove

    @pyqtProperty(bool, notify=detailsChanged)
    def canSign(self):
        return self._can_sign

    @pyqtProperty(bool, notify=detailsChanged)
    def isUnrelated(self):
        return self._is_unrelated

    @pyqtProperty(bool, notify=detailsChanged)
    def isComplete(self):
        return self._is_complete

    @pyqtProperty(bool, notify=detailsChanged)
    def isFinal(self):
        return self._is_final

    def update(self):
        if self._wallet is None:
            self._logger.error('wallet undefined')
            return

        if not self._rawtx:
            # abusing get_input_tx to get tx from txid
            self._tx = self._wallet.wallet.get_input_tx(self._txid)

        #self._logger.debug(repr(self._tx.to_json()))

        self._logger.debug('adding info from wallet')
        self._tx.add_info_from_wallet(self._wallet.wallet)

        self._inputs = list(map(lambda x: x.to_json(), self._tx.inputs()))
        self._outputs = list(map(lambda x: {
            'address': x.get_ui_address_str(),
            'value': QEAmount(amount_sat=x.value),
            'is_mine': self._wallet.wallet.is_mine(x.get_ui_address_str())
            }, self._tx.outputs()))

        txinfo = self._wallet.wallet.get_tx_info(self._tx)

        self._logger.debug(repr(txinfo))

        # can be None if outputs unrelated to wallet seed,
        # e.g. to_local local_force_close commitment CSV-locked p2wsh script
        if txinfo.amount is None:
            self._amount.satsInt = 0
        else:
            self._amount.satsInt = txinfo.amount

        self._status = txinfo.status
        self._fee.satsInt = txinfo.fee

        self._is_mined = False if not txinfo.tx_mined_status else txinfo.tx_mined_status.height > 0
        if self._is_mined:
            self.update_mined_status(txinfo.tx_mined_status)
        else:
            self._mempool_depth = self._wallet.wallet.config.depth_tooltip(txinfo.mempool_depth_bytes)

        if self._wallet.wallet.lnworker:
            lnworker_history = self._wallet.wallet.lnworker.get_onchain_history()
            if self._txid in lnworker_history:
                item = lnworker_history[self._txid]
                self._lnamount.satsInt = int(item['amount_msat'] / 1000)
            else:
                self._lnamount.satsInt = 0

        self._is_complete = self._tx.is_complete()
        self._is_final = self._tx.is_final()
        self._is_unrelated = txinfo.amount is None and self._lnamount.isEmpty
        self._is_lightning_funding_tx = txinfo.is_lightning_funding_tx
        self._can_bump = txinfo.can_bump
        self._can_dscancel = txinfo.can_dscancel
        self._can_broadcast = txinfo.can_broadcast
        self._can_cpfp = txinfo.can_cpfp
        self._can_save_as_local = txinfo.can_save_as_local and not txinfo.can_remove
        self._can_remove = txinfo.can_remove
        self._can_sign = not self._is_complete and self._wallet.wallet.can_sign(self._tx)

        self.detailsChanged.emit()

        if self._label != txinfo.label:
            self._label = txinfo.label
            self.labelChanged.emit()

    def update_mined_status(self, tx_mined_info):
        self._mempool_depth = ''
        self._date = format_time(tx_mined_info.timestamp)
        self._height = tx_mined_info.height
        self._confirmations = tx_mined_info.conf
        self._txpos = tx_mined_info.txpos
        self._header_hash = tx_mined_info.header_hash

    @pyqtSlot()
    def sign(self):
        try:
            self._wallet.transactionSigned.disconnect(self.onSigned)
        except:
            pass
        self._wallet.transactionSigned.connect(self.onSigned)
        self._wallet.sign(self._tx)
        # side-effect: signing updates self._tx
        # we rely on this for broadcast

    @pyqtSlot(str)
    def onSigned(self, txid):
        if txid != self._txid:
            return

        self._logger.debug('onSigned')
        self._wallet.transactionSigned.disconnect(self.onSigned)
        self.update()

    @pyqtSlot()
    def broadcast(self):
        assert self._tx.is_complete()

        try:
            self._wallet.broadcastfailed.disconnect(self.onBroadcastFailed)
        except:
            pass
        self._wallet.broadcastFailed.connect(self.onBroadcastFailed)

        self._can_broadcast = False
        self.detailsChanged.emit()

        self._wallet.broadcast(self._tx)

    @pyqtSlot(str,str,str)
    def onBroadcastFailed(self, txid, code, reason):
        if txid != self._txid:
            return

        self._wallet.broadcastFailed.disconnect(self.onBroadcastFailed)

        self._can_broadcast = True
        self.detailsChanged.emit()

    @pyqtSlot()
    @pyqtSlot(bool)
    def removeLocalTx(self, confirm = False):
        txid = self._txid

        if not confirm:
            num_child_txs = len(self._wallet.wallet.adb.get_depending_transactions(txid))
            question = _("Are you sure you want to remove this transaction?")
            if num_child_txs > 0:
                question = (
                    _("Are you sure you want to remove this transaction and {} child transactions?")
                    .format(num_child_txs))
            self.confirmRemoveLocalTx.emit(question)
            return

        self._wallet.wallet.adb.remove_transaction(txid)
        self._wallet.wallet.save_db()

    @pyqtSlot()
    def save(self):
        if not self._tx:
            return

        try:
            if not self._wallet.wallet.adb.add_transaction(self._tx):
                self.saveTxError.emit('conflict',
                        _("Transaction could not be saved.") + "\n" + _("It conflicts with current history."))
                return
            self._wallet.wallet.save_db()
            self.saveTxSuccess.emit()
        except AddTransactionException as e:
            self.saveTxError.emit('error', str(e))
        finally:
            self._can_save_as_local = False
            self._can_remove = True
            self.detailsChanged.emit()

    @pyqtSlot(result=str)
    @pyqtSlot(bool, result=str)
    def serializedTx(self, for_qr=False):
        if for_qr:
            return self._tx.to_qr_data()
        else:
            return str(self._tx)
