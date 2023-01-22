import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.3
import QtQuick.Controls.Material 2.0

import org.electrum 1.0

import "controls"

Pane {
    id: root
    width: parent.width
    height: parent.height
    padding: 0

    property string channelid

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Flickable {
            Layout.preferredWidth: parent.width
            Layout.fillHeight: true

            leftMargin: constants.paddingLarge
            rightMargin: constants.paddingLarge
            topMargin: constants.paddingLarge

            contentHeight: rootLayout.height
            clip:true
            interactive: height < contentHeight

            GridLayout {
                id: rootLayout
                width: parent.width
                columns: 2

                Heading {
                    Layout.columnSpan: 2
                    text: qsTr('Channel details')
                }

                Label {
                    visible: channeldetails.name
                    text: qsTr('Node name')
                    color: Material.accentColor
                }

                Label {
                    visible: channeldetails.name
                    text: channeldetails.name
                }

                Label {
                    text: qsTr('Short channel ID')
                    color: Material.accentColor
                }

                Label {
                    text: channeldetails.short_cid
                }

                Label {
                    text: qsTr('State')
                    color: Material.accentColor
                }

                Label {
                    text: channeldetails.state
                }

                Label {
                    text: qsTr('Initiator')
                    color: Material.accentColor
                }

                Label {
                    text: channeldetails.initiator
                }

                Label {
                    text: qsTr('Capacity')
                    color: Material.accentColor
                }

                FormattedAmount {
                    amount: channeldetails.capacity
                }

                Label {
                    text: qsTr('Can send')
                    color: Material.accentColor
                }

                RowLayout {
                    visible: channeldetails.isOpen
                    FormattedAmount {
                        visible: !channeldetails.frozenForSending
                        amount: channeldetails.canSend
                        singleLine: false
                    }
                    Label {
                        visible: channeldetails.frozenForSending
                        text: qsTr('n/a (frozen)')
                    }
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                    }
                    FlatButton {
                        Layout.minimumWidth: implicitWidth
                        // icon.source: '../../icons/warning.png'
                        // icon.color: 'transparent'
                        text: channeldetails.frozenForSending ? qsTr('Unfreeze') : qsTr('Freeze')
                        onClicked: channeldetails.freezeForSending()
                    }
                }

                Label {
                    visible: !channeldetails.isOpen
                    text: qsTr('n/a (channel not open)')
                }

                Label {
                    text: qsTr('Can Receive')
                    color: Material.accentColor
                }

                RowLayout {
                    visible: channeldetails.isOpen
                    FormattedAmount {
                        visible: !channeldetails.frozenForReceiving
                        amount: channeldetails.canReceive
                        singleLine: false
                    }

                    Label {
                        visible: channeldetails.frozenForReceiving
                        text: qsTr('n/a (frozen)')
                    }
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                    }
                    FlatButton {
                        Layout.minimumWidth: implicitWidth
                        // icon.source: '../../icons/warning.png'
                        // icon.color: 'transparent'
                        text: channeldetails.frozenForReceiving ? qsTr('Unfreeze') : qsTr('Freeze')
                        onClicked: channeldetails.freezeForReceiving()
                    }
                }

                Label {
                    visible: !channeldetails.isOpen
                    text: qsTr('n/a (channel not open)')
                }

                Label {
                    text: qsTr('Channel type')
                    color: Material.accentColor
                }

                Label {
                    text: channeldetails.channelType
                }

                Label {
                    text: qsTr('Remote node ID')
                    Layout.columnSpan: 2
                    color: Material.accentColor
                }

                TextHighlightPane {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    padding: 0
                    leftPadding: constants.paddingSmall

                    RowLayout {
                        width: parent.width
                        Label {
                            text: channeldetails.pubkey
                            font.pixelSize: constants.fontSizeLarge
                            font.family: FixedFont
                            Layout.fillWidth: true
                            wrapMode: Text.Wrap
                        }
                        ToolButton {
                            icon.source: '../../icons/share.png'
                            icon.color: 'transparent'
                            onClicked: {
                                var dialog = app.genericShareDialog.createObject(root,
                                    { title: qsTr('Channel node ID'), text: channeldetails.pubkey }
                                )
                                dialog.open()
                            }
                        }
                    }
                }

            }
        }

        FlatButton {
            Layout.fillWidth: true
            text: qsTr('Backup');
            onClicked: {
                var dialog = app.genericShareDialog.createObject(root,
                    {
                        title: qsTr('Channel Backup for %1').arg(channeldetails.short_cid),
                        text: channeldetails.channelBackup(),
                        text_help: channeldetails.channelBackupHelpText(),
                        iconSource: Qt.resolvedUrl('../../icons/file.png')
                    }
                )
                dialog.open()
            }
            icon.source: '../../icons/file.png'
        }

        FlatButton {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            text: qsTr('Close channel');
            visible: channeldetails.canClose
            onClicked: {
                var dialog = closechannel.createObject(root, { 'channelid': channelid })
                dialog.open()
            }
            icon.source: '../../icons/closebutton.png'
        }

        FlatButton {
            Layout.fillWidth: true
            Layout.preferredWidth: 1
            text: qsTr('Delete channel');
            visible: channeldetails.canDelete
            onClicked: {
                var dialog = app.messageDialog.createObject(root,
                        {
                            'text': qsTr('Are you sure you want to delete this channel? This will purge associated transactions from your wallet history.'),
                            'yesno': true
                        }
                )
                dialog.yesClicked.connect(function() {
                    channeldetails.deleteChannel()
                    app.stack.pop()
                    Daemon.currentWallet.historyModel.init_model() // needed here?
                    Daemon.currentWallet.channelModel.remove_channel(channelid)
                })
                dialog.open()
            }
            icon.source: '../../icons/delete.png'
        }
    }

    ChannelDetails {
        id: channeldetails
        wallet: Daemon.currentWallet
        channelid: root.channelid
    }

    Component {
        id: closechannel
        CloseChannelDialog {}
    }
}
