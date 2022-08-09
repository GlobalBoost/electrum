import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.1

import org.electrum 1.0

import "controls"

Pane {
    id: openwalletdialog
    
    property string title: qsTr("Open Wallet")

    property string name
    property string path

    property bool _unlockClicked: false

    GridLayout {
        columns: 2
        width: parent.width

        Label {
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignHCenter
            text: name
        }

        MessagePane {
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Wallet requires password to unlock")
            visible: wallet_db.needsPassword
            width: parent.width * 2/3
            warning: true
        }

        MessagePane {
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Invalid Password")
            visible: !wallet_db.validPassword && _unlockClicked
            width: parent.width * 2/3
            error: true
        }

        RowLayout {
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: parent.width * 2/3
            Label {
                text: qsTr('Password')
                visible: wallet_db.needsPassword
                Layout.fillWidth: true
            }

            PasswordField {
                id: password
                visible: wallet_db.needsPassword
                Layout.fillWidth: true
                onTextChanged: {
                    unlockButton.enabled = true
                    _unlockClicked = false
                }
                onAccepted: {
                    unlock()
                }
            }
        }

        Button {
            id: unlockButton
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignHCenter
            visible: wallet_db.needsPassword
            text: qsTr("Unlock")
            onClicked: {
                unlock()
            }
        }

        Label {
            text: qsTr('Select HW device')
            visible: wallet_db.needsHWDevice
        }

        ComboBox {
            id: hw_device
            model: ['','Not implemented']
            visible: wallet_db.needsHWDevice
        }

        Label {
            text: qsTr('Wallet requires splitting')
            visible: wallet_db.requiresSplit
        }

        Button {
            visible: wallet_db.requiresSplit
            text: qsTr('Split wallet')
            onClicked: wallet_db.doSplit()
        }
        
        BusyIndicator {
            id: busy
            running: false
            Layout.columnSpan: 2
            Layout.alignment: Qt.AlignHCenter
        }
    }

    function unlock() {
        unlockButton.enabled = false
        _unlockClicked = true
        wallet_db.password = password.text
        wallet_db.verify()
        openwalletdialog.forceActiveFocus()
    }
    
    WalletDB {
        id: wallet_db
        path: openwalletdialog.path
        onSplitFinished: {
            // if wallet needed splitting, we close the pane and refresh the wallet list
            Daemon.availableWallets.reload()
            app.stack.pop()
        }
        onReadyChanged: {
            if (ready) {
                busy.running = true
                Daemon.load_wallet(openwalletdialog.path, password.text)
                app.stack.pop(null)
            }
        }
        onInvalidPassword: {
            password.forceActiveFocus()
        }
    }
    
    Component.onCompleted: {
        wallet_db.verify()
        password.forceActiveFocus()
    }
}
