import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import QtQuick.Controls.Material

import org.electrum 1.0

import "controls"

ElDialog {
    id: dialog

    required property QtObject cpfpfeebumper

    title: qsTr('Bump Fee')
    iconSource: Qt.resolvedUrl('../../icons/rocket.png')

    width: parent.width
    height: parent.height
    padding: 0

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true

            leftMargin: constants.paddingLarge
            rightMargin: constants.paddingLarge

            contentHeight: rootLayout.height
            clip: true
            interactive: height < contentHeight

            GridLayout {
                id: rootLayout
                width: parent.width

                columns: 2

                Label {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    text: qsTr('A CPFP is a transaction that sends an unconfirmed output back to yourself, with a high fee. The goal is to have miners confirm the parent transaction in order to get the fee attached to the child transaction.')
                    wrapMode: Text.Wrap
                }

                Label {
                    Layout.columnSpan: 2
                    Layout.fillWidth: true
                    Layout.bottomMargin: constants.paddingLarge
                    text: qsTr('The proposed fee is computed using your fee/kB settings, applied to the total size of both child and parent transactions. After you broadcast a CPFP transaction, it is normal to see a new unconfirmed transaction in your history.')
                    wrapMode: Text.Wrap
                }

                Label {
                    Layout.preferredWidth: 1
                    Layout.fillWidth: true
                    text: qsTr('Total size')
                    color: Material.accentColor
                }

                Label {
                    Layout.preferredWidth: 1
                    Layout.fillWidth: true
                    text: qsTr('%1 bytes').arg(cpfpfeebumper.totalSize)
                }

                Label {
                    text: qsTr('Input amount')
                    color: Material.accentColor
                }

                FormattedAmount {
                    amount: cpfpfeebumper.inputAmount
                }

                Label {
                    text: qsTr('Output amount')
                    color: Material.accentColor
                }

                FormattedAmount {
                    amount: cpfpfeebumper.outputAmount
                    valid: cpfpfeebumper.valid
                }

                RowLayout {
                    Layout.columnSpan: 2
                    Slider {
                        id: feeslider
                        leftPadding: constants.paddingMedium
                        snapMode: Slider.SnapOnRelease
                        stepSize: 1
                        from: 0
                        to: cpfpfeebumper.sliderSteps
                        onValueChanged: {
                            if (activeFocus)
                                cpfpfeebumper.sliderPos = value
                        }
                        Component.onCompleted: {
                            value = cpfpfeebumper.sliderPos
                        }
                        Connections {
                            target: cpfpfeebumper
                            function onSliderPosChanged() {
                                feeslider.value = cpfpfeebumper.sliderPos
                            }
                        }
                    }

                    FeeMethodComboBox {
                        id: feemethod
                        feeslider: cpfpfeebumper
                    }
                }

                Label {
                    visible: feemethod.currentValue
                    text: qsTr('Target')
                    color: Material.accentColor
                }

                Label {
                    visible: feemethod.currentValue
                    text: cpfpfeebumper.target
                }

                Label {
                    text: qsTr('Fee for child')
                    color: Material.accentColor
                }

                FormattedAmount {
                    amount: cpfpfeebumper.feeForChild
                    valid: cpfpfeebumper.valid
                }

                Label {
                    text: qsTr('Total fee')
                    color: Material.accentColor
                }

                FormattedAmount {
                    amount: cpfpfeebumper.totalFee
                    valid: cpfpfeebumper.valid
                }

                Label {
                    text: qsTr('Total fee rate')
                    color: Material.accentColor
                }

                RowLayout {
                    Label {
                        text: cpfpfeebumper.valid ? cpfpfeebumper.totalFeeRate : ''
                        font.family: FixedFont
                    }

                    Label {
                        visible: cpfpfeebumper.valid
                        text: 'sat/vB'
                        color: Material.accentColor
                    }
                }

                InfoTextArea {
                    Layout.columnSpan: 2
                    Layout.preferredWidth: parent.width * 3/4
                    Layout.alignment: Qt.AlignHCenter
                    Layout.topMargin: constants.paddingLarge
                    visible: cpfpfeebumper.warning != ''
                    text: cpfpfeebumper.warning
                    iconStyle: InfoTextArea.IconStyle.Warn
                }

                ToggleLabel {
                    id: inputs_label
                    Layout.columnSpan: 2
                    Layout.topMargin: constants.paddingMedium

                    visible: cpfpfeebumper.valid
                    labelText: qsTr('Inputs (%1)').arg(cpfpfeebumper.inputs.length)
                    color: Material.accentColor
                }

                Repeater {
                    model: inputs_label.collapsed || !inputs_label.visible
                        ? undefined
                        : cpfpfeebumper.inputs
                    delegate: TxInput {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true

                        idx: index
                        model: modelData
                    }
                }

                ToggleLabel {
                    id: outputs_label
                    Layout.columnSpan: 2
                    Layout.topMargin: constants.paddingMedium

                    visible: cpfpfeebumper.valid
                    labelText: qsTr('Outputs (%1)').arg(cpfpfeebumper.outputs.length)
                    color: Material.accentColor
                }

                Repeater {
                    model: outputs_label.collapsed || !outputs_label.visible
                        ? undefined
                        : cpfpfeebumper.outputs
                    delegate: TxOutput {
                        Layout.columnSpan: 2
                        Layout.fillWidth: true

                        allowShare: false
                        allowClickAddress: false

                        idx: index
                        model: modelData
                    }
                }

            }
        }

        FlatButton {
            id: sendButton
            Layout.fillWidth: true
            text: qsTr('Ok')
            icon.source: '../../icons/confirmed.png'
            enabled: cpfpfeebumper.valid
            onClicked: doAccept()
        }
    }

    Connections {
        target: cpfpfeebumper
        function onTxMined() {
            dialog.doReject()
        }
    }
}
