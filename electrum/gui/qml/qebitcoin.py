import asyncio

from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from electrum import mnemonic
from electrum import keystore
from electrum.i18n import _
from electrum.bip32 import is_bip32_derivation, xpub_type
from electrum.logging import get_logger
from electrum.slip39 import decode_mnemonic, Slip39Error
from electrum.util import parse_URI, create_bip21_uri, InvalidBitcoinURI, get_asyncio_loop
from .qetypes import QEAmount


class QEBitcoin(QObject):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

    _logger = get_logger(__name__)

    generatedSeedChanged = pyqtSignal()
    generatedSeed = ''

    seedValidChanged = pyqtSignal()
    seedValid = False

    seedTypeChanged = pyqtSignal()
    seedType = ''

    validationMessageChanged = pyqtSignal()
    validationMessage = ''

    @pyqtProperty('QString', notify=generatedSeedChanged)
    def generated_seed(self):
        return self.generatedSeed

    @pyqtProperty(bool, notify=seedValidChanged)
    def seed_valid(self):
        return self.seedValid

    @pyqtProperty('QString', notify=seedTypeChanged)
    def seed_type(self):
        return self.seedType

    @pyqtProperty('QString', notify=validationMessageChanged)
    def validation_message(self):
        return self.validationMessage

    @validation_message.setter
    def validation_message(self, msg):
        if self.validationMessage != msg:
            self.validationMessage = msg
            self.validationMessageChanged.emit()

    @pyqtSlot()
    @pyqtSlot(str)
    @pyqtSlot(str,str)
    def generate_seed(self, seed_type='segwit', language='en'):
        self._logger.debug('generating seed of type ' + str(seed_type))

        async def co_gen_seed(seed_type, language):
            self.generatedSeed = mnemonic.Mnemonic(language).make_seed(seed_type=seed_type)
            self._logger.debug('seed generated')
            self.generatedSeedChanged.emit()

        asyncio.run_coroutine_threadsafe(co_gen_seed(seed_type, language), get_asyncio_loop())

    @pyqtSlot(str)
    @pyqtSlot(str,bool,bool)
    @pyqtSlot(str,bool,bool,str,str,str)
    def verify_seed(self, seed, bip39=False, slip39=False, wallet_type='standard', language='en'):
        self._logger.debug('bip39 ' + str(bip39))
        self._logger.debug('slip39 ' + str(slip39))

        seed_type = ''
        seed_valid = False
        self.validationMessage = ''

        if not (bip39 or slip39):
            seed_type = mnemonic.seed_type(seed)
            if seed_type != '':
                seed_valid = True
        elif bip39:
            is_checksum, is_wordlist = keystore.bip39_is_checksum_valid(seed)
            status = ('checksum: ' + ('ok' if is_checksum else 'failed')) if is_wordlist else 'unknown wordlist'
            self.validationMessage = 'BIP39 (%s)' % status

            if is_checksum:
                seed_type = 'bip39'
                seed_valid = True

        elif slip39: # TODO: incomplete impl, this code only validates a single share.
            try:
                share = decode_mnemonic(seed)
                seed_type = 'slip39'
                self.validationMessage = 'SLIP39: share #%d in %dof%d scheme' % (share.group_index, share.group_threshold, share.group_count)
            except Slip39Error as e:
                self.validationMessage = 'SLIP39: %s' % str(e)
            seed_valid = False # for now

        # cosigning seed
        if wallet_type != 'standard' and seed_type not in ['standard', 'segwit']:
            seed_type = ''
            seed_valid = False

        self.seedType = seed_type
        self.seedTypeChanged.emit()

        if self.seedValid != seed_valid:
            self.seedValid = seed_valid
            self.seedValidChanged.emit()

        self._logger.debug('seed verified: ' + str(seed_valid))

    @pyqtSlot(str, result=bool)
    @pyqtSlot(str, str, result=bool)
    def verify_master_key(self, key, wallet_type='standard'):
        self.validationMessage = ''
        if not keystore.is_master_key(key):
            self.validationMessage = _('Not a master key')
            return False

        if wallet_type == 'standard':
            # validation message?
            k = keystore.from_master_key(key)
            has_xpub = isinstance(k, keystore.Xpub)
            assert has_xpub
            t1 = xpub_type(k.xpub)
            if t1 not in ['standard', 'p2wpkh', 'p2wpkh-p2sh']:
                self.validationMessage = '%s: %s' % (_('Wrong key type'), t1)
                return False
            return True
        return False

    @pyqtSlot(str, result=bool)
    def verify_derivation_path(self, path):
        return is_bip32_derivation(path)

    @pyqtSlot(str, result='QVariantMap')
    def parse_uri(self, uri: str) -> dict:
        try:
            return parse_URI(uri)
        except InvalidBitcoinURI as e:
            return { 'error': str(e) }

    @pyqtSlot(str, QEAmount, str, int, int, result=str)
    def create_bip21_uri(self, address, satoshis, message, timestamp, expiry):
        extra_params = {}
        if expiry:
            extra_params['time'] = str(timestamp)
            extra_params['exp'] = str(expiry)

        return create_bip21_uri(address, satoshis.satsInt, message, extra_query_params=extra_params)
