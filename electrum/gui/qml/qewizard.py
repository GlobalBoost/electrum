import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from electrum.logging import get_logger
from electrum import mnemonic
from electrum.wizard import NewWalletWizard, ServerConnectWizard

if TYPE_CHECKING:
    from electrum.gui.qml.qedaemon import QEDaemon
    from electrum.plugin import Plugins


class QEAbstractWizard(QObject):
    """ Concrete subclasses of QEAbstractWizard must also inherit from a concrete AbstractWizard subclass.
        QEAbstractWizard forms the base for all QML GUI based wizards, while AbstractWizard defines
        the base for non-gui wizard flow navigation functionality.
    """
    _logger = get_logger(__name__)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)

    @pyqtSlot(result=str)
    def startWizard(self):
        self.start()
        return self._current.view

    @pyqtSlot(str, result=str)
    def viewToComponent(self, view):
        return self.navmap[view]['gui'] + '.qml'

    @pyqtSlot('QJSValue', result='QVariant')
    def submit(self, wizard_data):
        wdata = wizard_data.toVariant()
        view = self.resolve_next(self._current.view, wdata)
        return { 'view': view.view, 'wizard_data': view.wizard_data }

    @pyqtSlot(result='QVariant')
    def prev(self):
        viewstate = self.resolve_prev()
        return viewstate.wizard_data

    @pyqtSlot('QJSValue', result=bool)
    def isLast(self, wizard_data):
        wdata = wizard_data.toVariant()
        return self.is_last_view(self._current.view, wdata)


class QENewWalletWizard(NewWalletWizard, QEAbstractWizard):
    createError = pyqtSignal([str], arguments=["error"])
    createSuccess = pyqtSignal()

    def __init__(self, daemon: 'QEDaemon', plugins: 'Plugins', parent=None):
        NewWalletWizard.__init__(self, daemon.daemon, plugins)
        QEAbstractWizard.__init__(self, parent)
        self._qedaemon = daemon
        self._path = None
        self._password = None

        # attach view names and accept handlers
        self.navmap_merge({
            'wallet_name': {'gui': 'WCWalletName'},
            'wallet_type': {'gui': 'WCWalletType'},
            'keystore_type': {'gui': 'WCKeystoreType'},
            'create_seed': {'gui': 'WCCreateSeed'},
            'confirm_seed': {'gui': 'WCConfirmSeed'},
            'have_seed': {'gui': 'WCHaveSeed'},
            'script_and_derivation': {'gui': 'WCScriptAndDerivation'},
            'have_master_key': {'gui': 'WCHaveMasterKey'},
            'multisig': {'gui': 'WCMultisig'},
            'multisig_cosigner_keystore': {'gui': 'WCCosignerKeystore'},
            'multisig_cosigner_key': {'gui': 'WCHaveMasterKey'},
            'multisig_cosigner_seed': {'gui': 'WCHaveSeed'},
            'multisig_cosigner_script_and_derivation': {'gui': 'WCScriptAndDerivation'},
            'imported': {'gui': 'WCImport'},
            'wallet_password': {'gui': 'WCWalletPassword'}
        })

    pathChanged = pyqtSignal()
    @pyqtProperty(str, notify=pathChanged)
    def path(self):
        return self._path

    @path.setter
    def path(self, path):
        self._path = path
        self.pathChanged.emit()

    def is_single_password(self):
        return self._qedaemon.singlePasswordEnabled

    @pyqtSlot('QJSValue', result=bool)
    def hasDuplicateMasterKeys(self, js_data):
        self._logger.info('Checking for duplicate masterkeys')
        data = js_data.toVariant()
        return self.has_duplicate_masterkeys(data)

    @pyqtSlot('QJSValue', result=bool)
    def hasHeterogeneousMasterKeys(self, js_data):
        self._logger.info('Checking for heterogeneous masterkeys')
        data = js_data.toVariant()
        return self.has_heterogeneous_masterkeys(data)

    @pyqtSlot(str, str, result=bool)
    def isMatchingSeed(self, seed, seed_again):
        return mnemonic.is_matching_seed(seed=seed, seed_again=seed_again)

    @pyqtSlot(str, str, str, result='QVariantMap')
    def verifySeed(self, seed, seed_variant, wallet_type='standard'):
        seed_valid, seed_type, validation_message = self.validate_seed(seed, seed_variant, wallet_type)
        return {
            'valid': seed_valid,
            'type': seed_type,
            'message': validation_message
        }

    @pyqtSlot('QJSValue', bool, str)
    def createStorage(self, js_data, single_password_enabled, single_password):
        self._logger.info('Creating wallet from wizard data')
        data = js_data.toVariant()

        if single_password_enabled and single_password:
            data['encrypt'] = True
            data['password'] = single_password

        path = os.path.join(os.path.dirname(self._qedaemon.daemon.config.get_wallet_path()), data['wallet_name'])

        try:
            self.create_storage(path, data)

            # minimally populate self after create
            self._password = data['password']
            self.path = path

            self.createSuccess.emit()
        except Exception as e:
            self._logger.exception(f"createStorage errored: {e!r}")
            self.createError.emit(str(e))


class QEServerConnectWizard(ServerConnectWizard, QEAbstractWizard):
    def __init__(self, daemon: 'QEDaemon', parent=None):
        ServerConnectWizard.__init__(self, daemon.daemon)
        QEAbstractWizard.__init__(self, parent)

        # attach view names
        self.navmap_merge({
            'welcome': {'gui': 'WCWelcome'},
            'proxy_config': {'gui': 'WCProxyConfig'},
            'server_config': {'gui': 'WCServerConfig'},
        })
