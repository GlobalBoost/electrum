import QtQuick 2.15
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.0

Pane {
    id: root

    property string key
    property int keycode: -1

    property QtObject kbd
    padding: 1

    function emitKeyEvent() {
        if (keycode == -1) {
            keycode = parseInt(key, 36) - 9 + 0x40 // map a-z char to key code
        }
        kbd.keyEvent(keycode, key)
    }

    FlatButton {
        anchors.fill: parent

        focusPolicy: Qt.NoFocus
        autoRepeat: true
        autoRepeatDelay: 750

        text: key

        padding: 0
        font.pixelSize: Math.max(root.height * 1/3, constants.fontSizeSmall)

        onClicked: {
            emitKeyEvent()
        }

        // send keyevent again, otherwise it is ignored
        onDoubleClicked: {
            emitKeyEvent()
        }
    }
}
