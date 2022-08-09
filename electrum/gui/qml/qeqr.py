import asyncio
import qrcode
import math
import urllib

from PIL import Image, ImageQt

from PyQt5.QtCore import pyqtProperty, pyqtSignal, pyqtSlot, QObject, QRect, QPoint
from PyQt5.QtGui import QImage,QColor
from PyQt5.QtQuick import QQuickImageProvider

from electrum.logging import get_logger
from electrum.qrreader import get_qr_reader
from electrum.i18n import _
from electrum.util import profiler, get_asyncio_loop

class QEQRParser(QObject):
    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        self._text = text
        self.qrreader = get_qr_reader()
        if not self.qrreader:
            raise Exception(_("The platform QR detection library is not available."))

    _logger = get_logger(__name__)

    busyChanged = pyqtSignal()
    dataChanged = pyqtSignal()
    imageChanged = pyqtSignal()

    _busy = False
    _image = None

    @pyqtSlot('QImage')
    def scanImage(self, image=None):
        if self._busy:
            self._logger.warning("Already processing an image. Check 'busy' property before calling scanImage")
            return

        if image == None:
            self._logger.warning("No image to decode")
            return

        self._busy = True
        self.busyChanged.emit()

        self.logImageStats(image)
        self._parseQR(image)

    def logImageStats(self, image):
        self._logger.info('width: ' + str(image.width()))
        self._logger.info('height: ' + str(image.height()))
        self._logger.info('depth: ' + str(image.depth()))
        self._logger.info('format: ' + str(image.format()))

    def _parseQR(self, image):
        self.w = image.width()
        self.h = image.height()
        img_crop_rect = self._get_crop(image, 360)
        frame_cropped = image.copy(img_crop_rect)

        async def co_parse_qr(image):
            # Convert to Y800 / GREY FourCC (single 8-bit channel)
            # This creates a copy, so we don't need to keep the frame around anymore
            frame_y800 = image.convertToFormat(QImage.Format_Grayscale8)

            self.frame_id = 0
            # Read the QR codes from the frame
            self.qrreader_res = self.qrreader.read_qr_code(
                frame_y800.constBits().__int__(),
                frame_y800.byteCount(),
                frame_y800.bytesPerLine(),
                frame_y800.width(),
                frame_y800.height(),
                self.frame_id
                )

            if len(self.qrreader_res) > 0:
                result = self.qrreader_res[0]
                self._data = result
                self.dataChanged.emit()

            self._busy = False
            self.busyChanged.emit()

        asyncio.run_coroutine_threadsafe(co_parse_qr(frame_cropped), get_asyncio_loop())

    def _get_crop(self, image: QImage, scan_size: int) -> QRect:
        """
        Returns a QRect that is scan_size x scan_size in the middle of the resolution
        """
        self.scan_pos_x = (image.width() - scan_size) // 2
        self.scan_pos_y = (image.height() - scan_size) // 2
        return QRect(self.scan_pos_x, self.scan_pos_y, scan_size, scan_size)

    @pyqtProperty(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @pyqtProperty('QImage', notify=imageChanged)
    def image(self):
        return self._image

    @pyqtProperty(str, notify=dataChanged)
    def data(self):
        return self._data.data

    @pyqtProperty('QPoint', notify=dataChanged)
    def center(self):
        (x,y) = self._data.center
        return QPoint(x+self.scan_pos_x, y+self.scan_pos_y)

    @pyqtProperty('QVariant', notify=dataChanged)
    def points(self):
        result = []
        for item in self._data.points:
            (x,y) = item
            result.append(QPoint(x+self.scan_pos_x, y+self.scan_pos_y))
        return result

class QEQRImageProvider(QQuickImageProvider):
    def __init__(self, max_size, parent=None):
        super().__init__(QQuickImageProvider.Image)
        self._max_size = max_size

    _logger = get_logger(__name__)

    @profiler
    def requestImage(self, qstr, size):
        # Qt does a urldecode before passing the string here
        # but BIP21 (and likely other uri based specs) requires urlencoding,
        # so we re-encode percent-quoted if a 'scheme' is found in the string
        uri = urllib.parse.urlparse(qstr)
        if uri.scheme:
            # urlencode request parameters
            query = urllib.parse.parse_qs(uri.query)
            query = urllib.parse.urlencode(query, doseq=True, quote_via=urllib.parse.quote)
            uri = uri._replace(query=query)
            qstr = urllib.parse.urlunparse(uri)

        self._logger.debug('QR requested for %s' % qstr)
        qr = qrcode.QRCode(version=1, border=2)
        qr.add_data(qstr)

        # calculate best box_size
        pixelsize = min(self._max_size, 400)
        modules = 17 + 4 * qr.best_fit() + qr.border * 2
        qr.box_size = math.floor(pixelsize/modules)

        qr.make(fit=True)

        pimg = qr.make_image(fill_color='black', back_color='white')
        self.qimg = ImageQt.ImageQt(pimg)
        return self.qimg, self.qimg.size()

# helper for placing icon exactly where it should go on the QR code
# pyqt5 is unwilling to accept slots on QEQRImageProvider, so we need to define
# a separate class (sigh)
class QEQRImageProviderHelper(QObject):
    def __init__(self, max_size, parent=None):
        super().__init__(parent)
        self._max_size = max_size

    @pyqtSlot(str, result='QVariantMap')
    def getDimensions(self, qstr):
        qr = qrcode.QRCode(version=1, border=2)
        qr.add_data(qstr)

        # calculate best box_size
        pixelsize = min(self._max_size, 400)
        modules = 17 + 4 * qr.best_fit() + qr.border * 2
        qr.box_size = math.floor(pixelsize/modules)

        # calculate icon width in modules
        icon_modules = int(modules / 5)
        icon_modules += (icon_modules+1)%2 # force odd

        return { 'modules': modules, 'box_size': qr.box_size, 'icon_modules': icon_modules }

