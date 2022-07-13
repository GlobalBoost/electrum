from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from electrum.i18n import _
from electrum.logging import get_logger
from electrum.lnutil import extract_nodeid, ConnStringFormatError, LNPeerAddr, ln_dummy_address
from electrum.lnworker import hardcoded_trampoline_nodes
from electrum.gui import messages

from .qewallet import QEWallet
from .qetypes import QEAmount
from .qetxfinalizer import QETxFinalizer

class QEChannelOpener(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    _logger = get_logger(__name__)

    _wallet = None
    _nodeid = None
    _amount = QEAmount()
    _valid = False
    _opentx = None

    validationError = pyqtSignal([str,str], arguments=['code','message'])
    conflictingBackup = pyqtSignal([str], arguments=['message'])
    channelOpenError = pyqtSignal([str], arguments=['message'])
    channelOpenSuccess = pyqtSignal([str,bool], arguments=['cid','has_backup'])

    dataChanged = pyqtSignal() # generic notify signal

    walletChanged = pyqtSignal()
    @pyqtProperty(QEWallet, notify=walletChanged)
    def wallet(self):
        return self._wallet

    @wallet.setter
    def wallet(self, wallet: QEWallet):
        if self._wallet != wallet:
            self._wallet = wallet
            self.walletChanged.emit()

    nodeidChanged = pyqtSignal()
    @pyqtProperty(str, notify=nodeidChanged)
    def nodeid(self):
        return self._nodeid

    @nodeid.setter
    def nodeid(self, nodeid: str):
        if self._nodeid != nodeid:
            self._logger.debug('nodeid set -> %s' % nodeid)
            self._nodeid = nodeid
            self.nodeidChanged.emit()
            self.validate()

    amountChanged = pyqtSignal()
    @pyqtProperty(QEAmount, notify=amountChanged)
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, amount: QEAmount):
        if self._amount != amount:
            self._amount = amount
            self.amountChanged.emit()
            self.validate()

    validChanged = pyqtSignal()
    @pyqtProperty(bool, notify=validChanged)
    def valid(self):
        return self._valid

    finalizerChanged = pyqtSignal()
    @pyqtProperty(QETxFinalizer, notify=finalizerChanged)
    def finalizer(self):
        return self._finalizer

    @pyqtProperty(list, notify=dataChanged)
    def trampolineNodeNames(self):
        return list(hardcoded_trampoline_nodes().keys())

    # FIXME min channel funding amount
    # FIXME have requested funding amount
    def validate(self):
        nodeid_valid = False
        if self._nodeid:
            if not self._wallet.wallet.config.get('use_gossip', False):
                self._peer = hardcoded_trampoline_nodes()[self._nodeid]
                nodeid_valid = True
            else:
                try:
                    node_pubkey, host_port = extract_nodeid(self._nodeid)
                    host, port = host_port.split(':',1)
                    self._peer = LNPeerAddr(host, int(port), node_pubkey)
                    nodeid_valid = True
                except ConnStringFormatError as e:
                    self.validationError.emit('invalid_nodeid', repr(e))
                except ValueError as e:
                    self.validationError.emit('invalid_nodeid', repr(e))

        if not nodeid_valid:
            self._valid = False
            self.validChanged.emit()
            return

        self._logger.debug('amount=%s' % str(self._amount))
        if not self._amount or not (self._amount.satsInt > 0 or self._amount.isMax):
            self._valid = False
            self.validChanged.emit()
            return

        self._valid = True
        self.validChanged.emit()

    # FIXME "max" button in amount_dialog should enforce LN_MAX_FUNDING_SAT
    @pyqtSlot()
    @pyqtSlot(bool)
    def open_channel(self, confirm_backup_conflict=False):
        if not self.valid:
            return

        self._logger.debug('Connect String: %s' % str(self._peer))

        lnworker = self._wallet.wallet.lnworker
        if lnworker.has_conflicting_backup_with(self._peer.pubkey) and not confirm_backup_conflict:
            self.conflictingBackup.emit(messages.MGS_CONFLICTING_BACKUP_INSTANCE)
            return

        amount = '!' if self._amount.isMax else self._amount.satsInt
        self._logger.debug('amount = %s' % str(amount))

        coins = self._wallet.wallet.get_spendable_coins(None, nonlocal_only=True)

        mktx = lambda amt: lnworker.mktx_for_open_channel(
            coins=coins,
            funding_sat=amt,
            node_id=self._peer.pubkey,
            fee_est=None)

        acpt = lambda tx: self.do_open_channel(tx, str(self._peer), None)

        self._finalizer = QETxFinalizer(self, make_tx=mktx, accept=acpt)
        self._finalizer.canRbf = False
        self._finalizer.amount = self._amount
        self._finalizer.wallet = self._wallet
        self.finalizerChanged.emit()

    def do_open_channel(self, funding_tx, conn_str, password):
        self._logger.debug('opening channel')
        # read funding_sat from tx; converts '!' to int value
        funding_sat = funding_tx.output_value_for_address(ln_dummy_address())
        lnworker = self._wallet.wallet.lnworker
        try:
            chan, funding_tx = lnworker.open_channel(
                connect_str=conn_str,
                funding_tx=funding_tx,
                funding_sat=funding_sat,
                push_amt_sat=0,
                password=password)
        except Exception as e:
            self._logger.exception("Problem opening channel")
            self.channelOpenError.emit(_('Problem opening channel: ') + '\n' + repr(e))
            return

        self._logger.debug('opening channel succeeded')
        self.channelOpenSuccess.emit(chan.channel_id.hex(), chan.has_onchain_backup())

        # TODO: it would be nice to show this before broadcasting
        #if chan.has_onchain_backup():
            #self.maybe_show_funding_tx(chan, funding_tx)
        #else:
            #title = _('Save backup')
            #help_text = _(messages.MSG_CREATED_NON_RECOVERABLE_CHANNEL)
            #data = lnworker.export_channel_backup(chan.channel_id)
            #popup = QRDialog(
                #title, data,
                #show_text=False,
                #text_for_clipboard=data,
                #help_text=help_text,
                #close_button_text=_('OK'),
                #on_close=lambda: self.maybe_show_funding_tx(chan, funding_tx))
            #popup.open()
