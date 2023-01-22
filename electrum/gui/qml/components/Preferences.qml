import QtQuick 2.6
import QtQuick.Layouts 1.15
import QtQuick.Controls 2.3
import QtQuick.Controls.Material 2.0

import org.electrum 1.0

import "controls"

Pane {
    id: preferences

    property string title: qsTr("Preferences")

    padding: 0

    property var _baseunits: ['BTC','mBTC','bits','sat']

    ColumnLayout {
        anchors.fill: parent

        Flickable {
            Layout.fillHeight: true
            Layout.fillWidth: true

            contentHeight: prefsPane.height
            interactive: height < contentHeight
            clip: true

            Pane {
                id: prefsPane
                width: parent.width

                GridLayout {
                    columns: 2
                    width: parent.width

                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('User Interface')
                    }

                    Label {
                        text: qsTr('Language')
                    }

                    ElComboBox {
                        id: language
                        enabled: false
                    }

                    Label {
                        text: qsTr('Base unit')
                    }

                    ElComboBox {
                        id: baseUnit
                        model: _baseunits
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Config.baseUnit = currentValue
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: thousands
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.thousandsSeparator = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Add thousands separators to bitcoin amounts')
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: checkSoftware
                            enabled: false
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Automatically check for software updates')
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: fiatEnable
                            onCheckedChanged: {
                                if (activeFocus)
                                    Daemon.fx.enabled = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Fiat Currency')
                            wrapMode: Text.Wrap
                        }
                    }

                    ElComboBox {
                        id: currencies
                        model: Daemon.fx.currencies
                        enabled: Daemon.fx.enabled
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Daemon.fx.fiatCurrency = currentValue
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: historicRates
                            enabled: Daemon.fx.enabled
                            onCheckedChanged: {
                                if (activeFocus)
                                    Daemon.fx.historicRates = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Historic rates')
                            wrapMode: Text.Wrap
                        }
                    }

                    Label {
                        text: qsTr('Exchange rate provider')
                        enabled: Daemon.fx.enabled
                    }

                    ElComboBox {
                        id: rateSources
                        enabled: Daemon.fx.enabled
                        model: Daemon.fx.rateSources
                        onModelChanged: {
                            currentIndex = rateSources.indexOfValue(Daemon.fx.rateSource)
                        }
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Daemon.fx.rateSource = currentValue
                        }
                    }

                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('Wallet behavior')
                    }

                    Label {
                        text: qsTr('PIN')
                    }

                    RowLayout {
                        Label {
                            text: Config.pinCode == '' ? qsTr('Off'): qsTr('On')
                            color: Material.accentColor
                            Layout.rightMargin: constants.paddingMedium
                        }
                        Button {
                            text: qsTr('Enable')
                            visible: Config.pinCode == ''
                            onClicked: {
                                var dialog = pinSetup.createObject(preferences, {mode: 'enter'})
                                dialog.accepted.connect(function() {
                                    Config.pinCode = dialog.pincode
                                    dialog.close()
                                })
                                dialog.open()
                            }
                        }
                        Button {
                            text: qsTr('Change')
                            visible: Config.pinCode != ''
                            onClicked: {
                                var dialog = pinSetup.createObject(preferences, {mode: 'change', pincode: Config.pinCode})
                                dialog.accepted.connect(function() {
                                    Config.pinCode = dialog.pincode
                                    dialog.close()
                                })
                                dialog.open()
                            }
                        }
                        Button {
                            text: qsTr('Remove')
                            visible: Config.pinCode != ''
                            onClicked: {
                                Config.pinCode = ''
                            }
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: spendUnconfirmed
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.spendUnconfirmed = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Spend unconfirmed')
                            wrapMode: Text.Wrap
                        }
                    }

                    Label {
                        text: qsTr('Default request expiry')
                        Layout.fillWidth: false
                    }

                    RequestExpiryComboBox {
                        onCurrentValueChanged: {
                            if (activeFocus)
                                Config.requestExpiry = currentValue
                        }
                    }

                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('Lightning')
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: useTrampolineRouting
                            onCheckedChanged: {
                                if (activeFocus) {
                                    if (!checked) {
                                        var dialog = app.messageDialog.createObject(app, {
                                            text: qsTr('Using plain gossip mode is not recommended on mobile. Are you sure?'),
                                            yesno: true
                                        })
                                        dialog.yesClicked.connect(function() {
                                            Config.useGossip = true
                                        })
                                        dialog.rejected.connect(function() {
                                            checked = true // revert
                                        })
                                        dialog.open()
                                    } else {
                                        Config.useGossip = !checked
                                    }
                                }

                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Trampoline routing')
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: useRecoverableChannels
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.useRecoverableChannels = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Create recoverable channels')
                            wrapMode: Text.Wrap
                        }
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: useFallbackAddress
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.useFallbackAddress = checked
                            }
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Use onchain fallback address for Lightning payment requests')
                            wrapMode: Text.Wrap
                        }
                    }

                    PrefsHeading {
                        Layout.columnSpan: 2
                        text: qsTr('Advanced')
                    }

                    RowLayout {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true
                        Layout.leftMargin: -constants.paddingSmall
                        spacing: 0
                        Switch {
                            id: enableDebugLogs
                            onCheckedChanged: {
                                if (activeFocus)
                                    Config.enableDebugLogs = checked
                            }
                            enabled: Config.canToggleDebugLogs
                        }
                        Label {
                            Layout.fillWidth: true
                            text: qsTr('Enable debug logs (for developers)')
                            wrapMode: Text.Wrap
                        }
                    }
                }

            }
        }

    }

    Component {
        id: pinSetup
        Pin {}
    }

    Component.onCompleted: {
        baseUnit.currentIndex = _baseunits.indexOf(Config.baseUnit)
        thousands.checked = Config.thousandsSeparator
        currencies.currentIndex = currencies.indexOfValue(Daemon.fx.fiatCurrency)
        historicRates.checked = Daemon.fx.historicRates
        rateSources.currentIndex = rateSources.indexOfValue(Daemon.fx.rateSource)
        fiatEnable.checked = Daemon.fx.enabled
        spendUnconfirmed.checked = Config.spendUnconfirmed
        useTrampolineRouting.checked = !Config.useGossip
        useFallbackAddress.checked = Config.useFallbackAddress
        enableDebugLogs.checked = Config.enableDebugLogs
        useRecoverableChannels.checked = Config.useRecoverableChannels
    }
}
