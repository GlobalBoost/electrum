import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.3
import QtQuick.Controls.Material 2.0

import "controls"

Pane {
    id: root
    objectName: 'NetworkOverview'

    padding: 0

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.topMargin: constants.paddingLarge
            Layout.leftMargin: constants.paddingLarge
            Layout.rightMargin: constants.paddingLarge

            contentHeight: contentLayout.height
            clip: true
            interactive: height < contentHeight

            GridLayout {
                id: contentLayout
                width: parent.width
                columns: 2

                Heading {
                    Layout.columnSpan: 2
                    text: qsTr('Network')
                }

                Label {
                    text: qsTr('Proxy:');
                    color: Material.accentColor
                }
                Label {
                    text: 'mode' in Network.proxy ? qsTr('enabled') : qsTr('disabled')
                }

                Label {
                    visible: 'mode' in Network.proxy
                    text: qsTr('Proxy server:');
                    color: Material.accentColor
                }
                Label {
                    visible: 'mode' in Network.proxy
                    text: Network.proxy['host'] ? Network.proxy['host'] + ':' + Network.proxy['port'] : ''
                }

                Label {
                    visible: 'mode' in Network.proxy
                    text: qsTr('Proxy type:');
                    color: Material.accentColor
                }
                RowLayout {
                    Image {
                        visible: Network.isProxyTor
                        Layout.preferredWidth: constants.iconSizeMedium
                        Layout.preferredHeight: constants.iconSizeMedium
                        source: '../../icons/tor_logo.png'
                    }
                    Label {
                        visible: 'mode' in Network.proxy
                        text: Network.isProxyTor ? 'TOR' : Network.proxy['mode']
                    }
                }

                Heading {
                    Layout.columnSpan: 2
                    text: qsTr('On-chain')
                }

                Label {
                    text: qsTr('Network:');
                    color: Material.accentColor
                }
                Label {
                    text: Network.networkName
                }

                Label {
                    text: qsTr('Server:');
                    color: Material.accentColor
                }
                Label {
                    text: Network.server
                }

                Label {
                    text: qsTr('Local Height:');
                    color: Material.accentColor
                }
                Label {
                    text: Network.height
                }

                Label {
                    text: qsTr('Status:');
                    color: Material.accentColor
                }

                RowLayout {
                    OnchainNetworkStatusIndicator {}

                    Label {
                        text: Network.status
                    }
                }

                Label {
                    text: qsTr('Network fees:');
                    color: Material.accentColor
                }
                Label {
                    id: feeHistogram
                }

                Heading {
                    Layout.columnSpan: 2
                    text: qsTr('Lightning')
                }

                Label {
                    text: qsTr('Gossip:');
                    color: Material.accentColor
                }
                ColumnLayout {
                    visible: Config.useGossip
                    Label {
                        text: qsTr('%1 peers').arg(Network.gossipInfo.peers)
                    }
                    Label {
                        text: qsTr('%1 channels to fetch').arg(Network.gossipInfo.unknown_channels)
                    }
                    Label {
                        text: qsTr('%1 nodes, %2 channels').arg(Network.gossipInfo.db_nodes).arg(Network.gossipInfo.db_channels)
                    }
                }
                Label {
                    text: qsTr('disabled');
                    visible: !Config.useGossip
                }

                Label {
                    visible: Daemon.currentWallet.isLightning
                    text: qsTr('Channel peers:');
                    color: Material.accentColor
                }
                Label {
                    visible: Daemon.currentWallet.isLightning
                    text: Daemon.currentWallet.lightningNumPeers
                }
            }

        }

        FlatButton {
            Layout.fillWidth: true
            text: qsTr('Server Settings');
            icon.source: '../../icons/network.png'
            onClicked: {
                var dialog = serverConfig.createObject(root)
                dialog.open()
            }
        }

        FlatButton {
            Layout.fillWidth: true
            text: qsTr('Proxy Settings');
            icon.source: '../../icons/status_connected_proxy.png'
            onClicked: {
                var dialog = proxyConfig.createObject(root)
                dialog.open()
            }
        }

    }

    function setFeeHistogram() {
        var txt = ''
        Network.feeHistogram.forEach(function(item) {
            txt = txt + item[0] + ': ' + item[1] + '\n';
        })
        feeHistogram.text = txt.trim()
    }

    Connections {
        target: Network
        function onFeeHistogramUpdated() {
            setFeeHistogram()
        }
    }

    Component {
        id: serverConfig
        ServerConfigDialog {
            onClosed: destroy()
        }
    }

    Component {
        id: proxyConfig
        ProxyConfigDialog {
            onClosed: destroy()
        }
    }

    Component.onCompleted: setFeeHistogram()
}
