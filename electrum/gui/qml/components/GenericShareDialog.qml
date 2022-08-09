import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.14
import QtQuick.Controls.Material 2.0

import "controls"

ElDialog {
    id: dialog

    property string text

    title: ''
    parent: Overlay.overlay
    modal: true
    standardButtons: Dialog.Ok

    width: parent.width
    height: parent.height

    Overlay.modal: Rectangle {
        color: "#aa000000"
    }

    header: RowLayout {
        width: dialog.width
        Label {
            Layout.fillWidth: true
            text: dialog.title
            visible: dialog.title
            elide: Label.ElideRight
            padding: constants.paddingXLarge
            bottomPadding: 0
            font.bold: true
            font.pixelSize: constants.fontSizeMedium
        }
    }

    Flickable {
        anchors.fill: parent
        contentHeight: rootLayout.height
        clip:true
        interactive: height < contentHeight

        ColumnLayout {
            id: rootLayout
            width: parent.width
            spacing: constants.paddingMedium

            Rectangle {
                height: 1
                Layout.fillWidth: true
                color: Material.accentColor
            }

            QRImage {
                id: qr
                Layout.alignment: Qt.AlignHCenter
                Layout.topMargin: constants.paddingSmall
                Layout.bottomMargin: constants.paddingSmall
            }

            Rectangle {
                height: 1
                Layout.fillWidth: true
                color: Material.accentColor
            }

            TextHighlightPane {
                Layout.fillWidth: true
                Label {
                    width: parent.width
                    text: dialog.text
                    wrapMode: Text.Wrap
                    font.pixelSize: constants.fontSizeLarge
                    font.family: FixedFont
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignHCenter
                Button {
                    text: qsTr('Copy')
                    icon.source: '../../icons/copy_bw.png'
                    onClicked: AppController.textToClipboard(dialog.text)
                }
                Button {
                    //enabled: false
                    text: qsTr('Share')
                    icon.source: '../../icons/share.png'
                    onClicked: {
                        AppController.doShare(dialog.text, dialog.title)
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        qr.qrdata = dialog.text
    }
}
