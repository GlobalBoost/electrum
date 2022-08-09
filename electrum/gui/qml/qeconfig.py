from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject

from decimal import Decimal

from electrum.logging import get_logger
from electrum.util import DECIMAL_POINT_DEFAULT, format_satoshis

from .qetypes import QEAmount
from .auth import AuthMixin, auth_protect

class QEConfig(AuthMixin, QObject):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

    _logger = get_logger(__name__)

    autoConnectChanged = pyqtSignal()
    @pyqtProperty(bool, notify=autoConnectChanged)
    def autoConnect(self):
        return self.config.get('auto_connect')

    @autoConnect.setter
    def autoConnect(self, auto_connect):
        self.config.set_key('auto_connect', auto_connect, True)
        self.autoConnectChanged.emit()

    # auto_connect is actually a tri-state, expose the undefined case
    @pyqtProperty(bool, notify=autoConnectChanged)
    def autoConnectDefined(self):
        return self.config.get('auto_connect') is not None

    serverStringChanged = pyqtSignal()
    @pyqtProperty('QString', notify=serverStringChanged)
    def serverString(self):
        return self.config.get('server')

    @serverString.setter
    def serverString(self, server):
        self.config.set_key('server', server, True)
        self.serverStringChanged.emit()

    manualServerChanged = pyqtSignal()
    @pyqtProperty(bool, notify=manualServerChanged)
    def manualServer(self):
        return self.config.get('oneserver')

    @manualServer.setter
    def manualServer(self, oneserver):
        self.config.set_key('oneserver', oneserver, True)
        self.manualServerChanged.emit()

    baseUnitChanged = pyqtSignal()
    @pyqtProperty(str, notify=baseUnitChanged)
    def baseUnit(self):
        return self.config.get_base_unit()

    @baseUnit.setter
    def baseUnit(self, unit):
        self.config.set_base_unit(unit)
        self.baseUnitChanged.emit()

    thousandsSeparatorChanged = pyqtSignal()
    @pyqtProperty(bool, notify=thousandsSeparatorChanged)
    def thousandsSeparator(self):
        return self.config.get('amt_add_thousands_sep', False)

    @thousandsSeparator.setter
    def thousandsSeparator(self, checked):
        self.config.set_key('amt_add_thousands_sep', checked)
        self.config.amt_add_thousands_sep = checked
        self.thousandsSeparatorChanged.emit()

    spendUnconfirmedChanged = pyqtSignal()
    @pyqtProperty(bool, notify=spendUnconfirmedChanged)
    def spendUnconfirmed(self):
        return not self.config.get('confirmed_only', False)

    @spendUnconfirmed.setter
    def spendUnconfirmed(self, checked):
        self.config.set_key('confirmed_only', not checked, True)
        self.spendUnconfirmedChanged.emit()

    pinCodeChanged = pyqtSignal()
    @pyqtProperty(str, notify=pinCodeChanged)
    def pinCode(self):
        return self.config.get('pin_code', '')

    @pinCode.setter
    def pinCode(self, pin_code):
        if pin_code == '':
            self.pinCodeRemoveAuth()
        else:
            self.config.set_key('pin_code', pin_code, True)
            self.pinCodeChanged.emit()

    @auth_protect(method='wallet')
    def pinCodeRemoveAuth(self):
        self.config.set_key('pin_code', '', True)
        self.pinCodeChanged.emit()

    useGossipChanged = pyqtSignal()
    @pyqtProperty(bool, notify=useGossipChanged)
    def useGossip(self):
        return self.config.get('use_gossip', False)

    @useGossip.setter
    def useGossip(self, gossip):
        self.config.set_key('use_gossip', gossip)
        self.useGossipChanged.emit()

    @pyqtSlot('qint64', result=str)
    @pyqtSlot('qint64', bool, result=str)
    @pyqtSlot(QEAmount, result=str)
    @pyqtSlot(QEAmount, bool, result=str)
    def formatSats(self, satoshis, with_unit=False):
        if isinstance(satoshis, QEAmount):
            satoshis = satoshis.satsInt
        if with_unit:
            return self.config.format_amount_and_units(satoshis)
        else:
            return self.config.format_amount(satoshis)

    @pyqtSlot(QEAmount, result=str)
    @pyqtSlot(QEAmount, bool, result=str)
    def formatMilliSats(self, amount, with_unit=False):
        if isinstance(amount, QEAmount):
            msats = amount.msatsInt
        else:
            return '---'

        s = format_satoshis(msats/1000,
                            decimal_point=self.decimal_point(),
                            precision=3)
        return s
        #if with_unit:
            #return self.config.format_amount_and_units(msats)
        #else:
            #return self.config.format_amount(satoshis)

    # TODO delegate all this to config.py/util.py
    def decimal_point(self):
        return self.config.get('decimal_point', DECIMAL_POINT_DEFAULT)

    def max_precision(self):
        return self.decimal_point() + 0 #self.extra_precision

    @pyqtSlot(str, result=QEAmount)
    def unitsToSats(self, unitAmount):
        self._amount = QEAmount()
        try:
            x = Decimal(unitAmount)
        except:
            return self._amount

        # scale it to max allowed precision, make it an int
        max_prec_amount = int(pow(10, self.max_precision()) * x)
        # if the max precision is simply what unit conversion allows, just return
        if self.max_precision() == self.decimal_point():
            self._amount = QEAmount(amount_sat=max_prec_amount)
            return self._amount
        self._logger.debug('fallthrough')
        # otherwise, scale it back to the expected unit
        #amount = Decimal(max_prec_amount) / Decimal(pow(10, self.max_precision()-self.decimal_point()))
        #return int(amount) #Decimal(amount) if not self.is_int else int(amount)
        return self._amount

    @pyqtSlot('quint64', result=float)
    def satsToUnits(self, satoshis):
        return satoshis / pow(10,self.config.decimal_point)
