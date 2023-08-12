import os
from typing import TYPE_CHECKING

from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from electrum.logging import get_logger
from electrum.storage import WalletStorage, StorageEncryptionVersion
from electrum.wallet_db import WalletDB
from electrum.wallet import Wallet
from electrum.bip32 import normalize_bip32_derivation, xpub_type
from electrum.util import InvalidPassword, WalletFileException, send_exception_to_crash_reporter
from electrum import keystore

if TYPE_CHECKING:
    from electrum.simple_config import SimpleConfig


class QEWalletDB(QObject):
    _logger = get_logger(__name__)

    fileNotFound = pyqtSignal()
    walletOpenProblem = pyqtSignal([str], arguments=['error'])
    pathChanged = pyqtSignal([bool], arguments=['ready'])
    needsPasswordChanged = pyqtSignal()
    needsHWDeviceChanged = pyqtSignal()
    passwordChanged = pyqtSignal()
    validPasswordChanged = pyqtSignal()
    requiresSplitChanged = pyqtSignal()
    splitFinished = pyqtSignal()
    readyChanged = pyqtSignal()
    invalidPassword = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        from .qeapp import ElectrumQmlApplication
        self.daemon = ElectrumQmlApplication._daemon
        self._config = self.daemon.config  # type: SimpleConfig

        self.reset()

    def reset(self):
        self._path = None
        self._needsPassword = False
        self._needsHWDevice = False
        self._password = ''
        self._requiresSplit = False
        self._validPassword = True

        self._storage = None
        self._db = None

        self._ready = False

    @pyqtProperty('QString', notify=pathChanged)
    def path(self):
        return self._path

    @path.setter
    def path(self, wallet_path):
        self._logger.debug('setting path: ' + wallet_path)
        self.reset()
        self._path = wallet_path

        self.pathChanged.emit(self._ready)

    @pyqtProperty(bool, notify=needsPasswordChanged)
    def needsPassword(self):
        return self._needsPassword

    @needsPassword.setter
    def needsPassword(self, wallet_needs_password):
        if wallet_needs_password == self._needsPassword:
            return

        self._needsPassword = wallet_needs_password
        self.needsPasswordChanged.emit()

    @pyqtProperty(bool, notify=needsHWDeviceChanged)
    def needsHWDevice(self):
        return self._needsHWDevice

    @needsHWDevice.setter
    def needsHWDevice(self, wallet_needs_hw_device):
        if wallet_needs_hw_device == self._needsHWDevice:
            return

        self._needsHWDevice = wallet_needs_hw_device
        self.needsHWDeviceChanged.emit()

    @pyqtProperty('QString', notify=passwordChanged)
    def password(self):
        return '' # no read access

    @password.setter
    def password(self, wallet_password):
        if wallet_password == self._password:
            return

        self._password = wallet_password
        self.passwordChanged.emit()

    @pyqtProperty(bool, notify=requiresSplitChanged)
    def requiresSplit(self):
        return self._requiresSplit

    @pyqtProperty(bool, notify=validPasswordChanged)
    def validPassword(self):
        return self._validPassword

    @validPassword.setter
    def validPassword(self, validPassword):
        if self._validPassword != validPassword:
            self._validPassword = validPassword
            self.validPasswordChanged.emit()

    @pyqtProperty(bool, notify=readyChanged)
    def ready(self):
        return self._ready

    @pyqtSlot()
    def verify(self):
        try:
            self._load_storage()
            if self._storage:
                self._load_db()
        except WalletFileException as e:
            self._logger.error(f"verify errored: {repr(e)}")
            self._storage = None
            self.walletOpenProblem.emit(str(e))
            if e.should_report_crash:
                send_exception_to_crash_reporter(e)

    @pyqtSlot()
    def doSplit(self):
        self._logger.warning('doSplit')
        if not self._requiresSplit:
            return

        self._db.split_accounts(self._path)

        self.splitFinished.emit()

    def _load_storage(self):
        """can raise WalletFileException"""
        self._storage = WalletStorage(self._path)
        if not self._storage.file_exists():
            self._logger.warning('file does not exist')
            self.fileNotFound.emit()
            self._storage = None
            return

        if self._storage.is_encrypted():
            self.needsPassword = True

            try:
                self._storage.decrypt('' if not self._password else self._password)
                self.validPassword = True
            except InvalidPassword as e:
                self.validPassword = False
                self.invalidPassword.emit()
        else:  # storage not encrypted; but it might still have a keystore pw
            # FIXME hack... load both db and full wallet, just to tell if it has keystore pw.
            #       this also completely ignores db.requires_split(), db.get_action(), etc
            db = WalletDB(self._storage.read(), manual_upgrades=False)
            wallet = Wallet(db, self._storage, config=self._config)
            self.needsPassword = wallet.has_password()
            if self.needsPassword:
                try:
                    wallet.check_password('' if not self._password else self._password)
                    self.validPassword = True
                except InvalidPassword as e:
                    self.validPassword = False
                    self._storage = None
                    self.invalidPassword.emit()

        if self._storage:
            if not self._storage.is_past_initial_decryption():
                self._storage = None

    def _load_db(self):
        """can raise WalletFileException"""
        # needs storage accessible
        self._db = WalletDB(self._storage.read(), manual_upgrades=True)
        if self._db.requires_split():
            self._logger.warning('wallet requires split')
            self._requiresSplit = True
            self.requiresSplitChanged.emit()
            return
        if self._db.get_action():
            self._logger.warning('action pending. QML version doesn\'t support continuation of wizard')
            return

        if self._db.requires_upgrade():
            self._logger.warning('wallet requires upgrade, upgrading')
            self._db.upgrade()
            self._db.write(self._storage)

        self._ready = True
        self.readyChanged.emit()
