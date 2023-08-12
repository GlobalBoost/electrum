import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.0
import QtQuick.Controls.Material 2.0

import org.electrum 1.0

TextHighlightPane {
    id: root

    property variant model
    property bool allowShare: true

    RowLayout {
        width: parent.width
        Label {
            text: model.address
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            font.pixelSize: constants.fontSizeLarge
            font.family: FixedFont
            color: model.is_mine
                ? model.is_change
                    ? constants.colorAddressInternal
                    : constants.colorAddressExternal
                : model.is_billing
                    ? constants.colorAddressBilling
                    : Material.foreground
        }
        Label {
            text: Config.formatSats(model.value)
            font.pixelSize: constants.fontSizeMedium
            font.family: FixedFont
        }
        Label {
            text: Config.baseUnit
            font.pixelSize: constants.fontSizeMedium
            color: Material.accentColor
        }
        ToolButton {
            visible: allowShare
            icon.source: Qt.resolvedUrl('../../../icons/share.png')
            icon.color: 'transparent'
            onClicked: {
                var dialog = app.genericShareDialog.createObject(app, {
                    title: qsTr('Tx Output'),
                    text: model.address
                })
                dialog.open()
            }
        }
    }
}

