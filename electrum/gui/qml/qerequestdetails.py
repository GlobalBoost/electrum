from time import time

from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject, QTimer, Q_ENUMS

from electrum.logging import get_logger
from electrum.invoices import (PR_UNPAID, PR_EXPIRED, PR_UNKNOWN, PR_PAID, PR_INFLIGHT,
                               PR_FAILED, PR_ROUTING, PR_UNCONFIRMED, LN_EXPIRY_NEVER)

from .qewallet import QEWallet
from .qetypes import QEAmount
from .util import QtEventListener, event_listener

class QERequestDetails(QObject, QtEventListener):

    class Status:
        Unpaid = PR_UNPAID
        Expired = PR_EXPIRED
        Unknown = PR_UNKNOWN
        Paid = PR_PAID
        Inflight = PR_INFLIGHT
        Failed = PR_FAILED
        Routing = PR_ROUTING
        Unconfirmed = PR_UNCONFIRMED

    Q_ENUMS(Status)

    _logger = get_logger(__name__)

    _wallet = None
    _key = None
    _req = None
    _timer = None
    _amount = None

    detailsChanged = pyqtSignal() # generic request properties changed signal
    statusChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.register_callbacks()
        self.destroyed.connect(lambda: self.on_destroy())

    def on_destroy(self):
        self.unregister_callbacks()
        if self._timer:
            self._timer.stop()
            self._timer = None

    @event_listener
    def on_event_request_status(self, wallet, key, status):
        if wallet == self._wallet.wallet and key == self._key:
            self._logger.debug('request status %d for key %s' % (status, key))
            self.statusChanged.emit()

    walletChanged = pyqtSignal()
    @pyqtProperty(QEWallet, notify=walletChanged)
    def wallet(self):
        return self._wallet

    @wallet.setter
    def wallet(self, wallet: QEWallet):
        if self._wallet != wallet:
            self._wallet = wallet
            self.walletChanged.emit()
            self.initRequest()

    keyChanged = pyqtSignal()
    @pyqtProperty(str, notify=keyChanged)
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        if self._key != key:
            self._key = key
            self._logger.debug(f'key={key}')
            self.keyChanged.emit()
            self.initRequest()

    statusChanged = pyqtSignal()
    @pyqtProperty(int, notify=statusChanged)
    def status(self):
        return self._wallet.wallet.get_invoice_status(self._req)

    @pyqtProperty(str, notify=statusChanged)
    def status_str(self):
        return self._req.get_status_str(self.status) if self._req else ''

    @pyqtProperty(bool, notify=detailsChanged)
    def isLightning(self):
        return self._req.is_lightning()

    @pyqtProperty(str, notify=detailsChanged)
    def address(self):
        addr = self._req.get_address() if self._req else ''
        return addr if addr else ''

    @pyqtProperty(str, notify=detailsChanged)
    def message(self):
        return self._req.get_message() if self._req else ''

    @pyqtProperty(QEAmount, notify=detailsChanged)
    def amount(self):
        return self._amount

    @pyqtProperty(int, notify=detailsChanged)
    def timestamp(self):
        return self._req.get_time()

    @pyqtProperty(int, notify=detailsChanged)
    def expiration(self):
        return self._req.get_expiration_date()

    @pyqtProperty(str, notify=detailsChanged)
    def bolt11(self):
        return self._req.lightning_invoice if self._req else ''

    @pyqtProperty(str, notify=detailsChanged)
    def bip21(self):
        return self._req.get_bip21_URI() if self._req else ''


    def initRequest(self):
        if self._wallet is None or self._key is None:
            return

        self._req = self._wallet.wallet.get_request(self._key)

        if self._req is None:
            self._logger.error(f'payment request key {self._key} unknown in wallet {self._wallet.name}')
            return

        self._amount = QEAmount(from_invoice=self._req)

        self.detailsChanged.emit()
        self.initStatusStringTimer()

    def initStatusStringTimer(self):
        if self.status == PR_UNPAID:
            if self.expiration > 0 and self.expiration != LN_EXPIRY_NEVER:
                self._timer = QTimer(self)
                self._timer.setSingleShot(True)
                self._timer.timeout.connect(self.updateStatusString)

                # very roughly according to util.time_difference
                exp_in = int(self.expiration - time())
                exp_in_min = int(exp_in/60)

                interval = 0
                if exp_in < 0:
                    interval = 0
                if exp_in_min < 2:
                    interval = 1000
                elif exp_in_min < 90:
                    interval = 1000 * 60
                elif exp_in_min < 1440:
                    interval = 1000 * 60 * 60

                if interval > 0:
                    self._logger.debug(f'setting status update timer to {interval}, req expires in {exp_in} seconds')
                    self._timer.setInterval(interval)  # msec
                    self._timer.start()


    @pyqtSlot()
    def updateStatusString(self):
        self.statusChanged.emit()
        self.initStatusStringTimer()

