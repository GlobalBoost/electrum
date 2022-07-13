import QtQuick 2.6
import QtQuick.Controls.Material 2.0

Item {
    readonly property int paddingTiny: 4 //deprecated
    readonly property int paddingXXSmall: 4
    readonly property int paddingXSmall: 6
    readonly property int paddingSmall: 8
    readonly property int paddingMedium: 12
    readonly property int paddingLarge: 16
    readonly property int paddingXLarge: 20
    readonly property int paddingXXLarge: 28

    readonly property int fontSizeXSmall: 10
    readonly property int fontSizeSmall: 12
    readonly property int fontSizeMedium: 15
    readonly property int fontSizeLarge: 18
    readonly property int fontSizeXLarge: 22
    readonly property int fontSizeXXLarge: 28

    readonly property int iconSizeSmall: 16
    readonly property int iconSizeMedium: 24
    readonly property int iconSizeLarge: 32
    readonly property int iconSizeXLarge: 48
    readonly property int iconSizeXXLarge: 64

    property color colorCredit: "#ff80ff80"
    property color colorDebit: "#ffff8080"
    property color mutedForeground: 'gray' //Qt.lighter(Material.background, 2)
    property color colorMine: "yellow"

    property color colorLightningLocal: "blue"
    property color colorLightningRemote: "yellow"

}
