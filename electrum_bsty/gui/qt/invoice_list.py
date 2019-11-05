#!/usr/bin/env python
#
# Electrum - lightweight Bitcoin client
# Copyright (C) 2015 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from enum import IntEnum

from PyQt5.QtCore import Qt, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont
from PyQt5.QtWidgets import QHeaderView, QMenu, QVBoxLayout, QGridLayout, QLabel, QTreeWidget, QTreeWidgetItem

from electrum_bsty.i18n import _
from electrum_bsty.util import format_time, PR_UNPAID, PR_PAID, PR_INFLIGHT
from electrum_bsty.util import get_request_status
from electrum_bsty.util import PR_TYPE_ONCHAIN, PR_TYPE_LN
from electrum_bsty.lnutil import format_short_channel_id
from electrum_bsty.bitcoin import COIN
from electrum_bsty import constants

from .util import (MyTreeView, read_QIcon, MONOSPACE_FONT,
                   import_meta_gui, export_meta_gui, pr_icons)
from .util import CloseButton, Buttons
from .util import WindowModalDialog



ROLE_REQUEST_TYPE = Qt.UserRole
ROLE_REQUEST_ID = Qt.UserRole + 1


class InvoiceList(MyTreeView):

    class Columns(IntEnum):
        DATE = 0
        DESCRIPTION = 1
        AMOUNT = 2
        STATUS = 3

    headers = {
        Columns.DATE: _('Date'),
        Columns.DESCRIPTION: _('Description'),
        Columns.AMOUNT: _('Amount'),
        Columns.STATUS: _('Status'),
    }
    filter_columns = [Columns.DATE, Columns.DESCRIPTION, Columns.AMOUNT]

    def __init__(self, parent):
        super().__init__(parent, self.create_menu,
                         stretch_column=self.Columns.DESCRIPTION,
                         editable_columns=[])
        self.logs = {}
        self.setSortingEnabled(True)
        self.setModel(QStandardItemModel(self))
        self.update()

    def update_item(self, key, status, log):
        req = self.parent.wallet.get_invoice(key)
        if req is None:
            return
        model = self.model()
        for row in range(0, model.rowCount()):
            item = model.item(row, 0)
            if item.data(ROLE_REQUEST_ID) == key:
                break
        else:
            return
        status_item = model.item(row, self.Columns.STATUS)
        status_str = get_request_status(req)
        if log:
            self.logs[key] = log
            if status == PR_INFLIGHT:
                status_str += '... (%d)'%len(log)
        status_item.setText(status_str)
        status_item.setIcon(read_QIcon(pr_icons.get(status)))

    def update(self):
        _list = self.parent.wallet.get_invoices()
        # filter out paid invoices unless we have the log
        _list = [x for x in _list if x and x.get('status') != PR_PAID or x.get('rhash') in self.logs]
        self.model().clear()
        self.update_headers(self.__class__.headers)
        for idx, item in enumerate(_list):
            invoice_type = item['type']
            if invoice_type == PR_TYPE_LN:
                key = item['rhash']
                icon_name = 'lightning.png'
            elif invoice_type == PR_TYPE_ONCHAIN:
                key = item['id']
                icon_name = 'bitcoin.png'
                if item.get('bip70'):
                    icon_name = 'seal.png'
            else:
                raise Exception('Unsupported type')
            status = item['status']
            status_str = get_request_status(item) # convert to str
            message = item['message']
            amount = item['amount']
            timestamp = item.get('time', 0)
            date_str = format_time(timestamp) if timestamp else _('Unknown')
            amount_str = self.parent.format_amount(amount, whitespaces=True)
            labels = [date_str, message, amount_str, status_str]
            items = [QStandardItem(e) for e in labels]
            self.set_editability(items)
            items[self.Columns.DATE].setIcon(read_QIcon(icon_name))
            items[self.Columns.STATUS].setIcon(read_QIcon(pr_icons.get(status)))
            items[self.Columns.DATE].setData(key, role=ROLE_REQUEST_ID)
            items[self.Columns.DATE].setData(invoice_type, role=ROLE_REQUEST_TYPE)
            self.model().insertRow(idx, items)

        self.selectionModel().select(self.model().index(0,0), QItemSelectionModel.SelectCurrent)
        # sort requests by date
        self.model().sort(self.Columns.DATE)
        # hide list if empty
        if self.parent.isVisible():
            b = self.model().rowCount() > 0
            self.setVisible(b)
            self.parent.invoices_label.setVisible(b)
        self.filter()

    def import_invoices(self):
        import_meta_gui(self.parent, _('invoices'), self.parent.invoices.import_file, self.update)

    def export_invoices(self):
        export_meta_gui(self.parent, _('invoices'), self.parent.invoices.export_file)

    def create_menu(self, position):
        idx = self.indexAt(position)
        item = self.model().itemFromIndex(idx)
        item_col0 = self.model().itemFromIndex(idx.sibling(idx.row(), self.Columns.DATE))
        if not item or not item_col0:
            return
        key = item_col0.data(ROLE_REQUEST_ID)
        request_type = item_col0.data(ROLE_REQUEST_TYPE)
        menu = QMenu(self)
        self.add_copy_menu(menu, idx)
        invoice = self.parent.wallet.get_invoice(key)
        menu.addAction(_("Details"), lambda: self.parent.show_invoice(key))
        if invoice['status'] == PR_UNPAID:
            menu.addAction(_("Pay"), lambda: self.parent.do_pay_invoice(invoice))
        if key in self.logs:
            menu.addAction(_("View log"), lambda: self.show_log(key))
        menu.addAction(_("Delete"), lambda: self.parent.delete_invoice(key))
        menu.exec_(self.viewport().mapToGlobal(position))

    def show_log(self, key):
        log = self.logs.get(key)
        d = WindowModalDialog(self, _("Payment log"))
        vbox = QVBoxLayout(d)
        log_w = QTreeWidget()
        log_w.setHeaderLabels([_('Route'), _('Channel ID'), _('Message'), _('Blacklist')])
        for i, (route, success, failure_log) in enumerate(log):
            route_str = '%d'%len(route)
            if not success:
                sender_idx, failure_msg, blacklist = failure_log
                short_channel_id = route[sender_idx+1].short_channel_id
                data = failure_msg.data
                message = repr(failure_msg.code)
            else:
                short_channel_id = route[-1].short_channel_id
                message = _('Success')
                blacklist = False
            chan_str = format_short_channel_id(short_channel_id)
            x = QTreeWidgetItem([route_str, chan_str, message, repr(blacklist)])
            log_w.addTopLevelItem(x)
        vbox.addWidget(log_w)
        vbox.addLayout(Buttons(CloseButton(d)))
        d.exec_()
