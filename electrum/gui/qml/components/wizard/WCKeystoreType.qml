import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.1

WizardComponent {
    valid: keystoregroup.checkedButton !== null

    function apply() {
        wizard_data['keystore_type'] = keystoregroup.checkedButton.keystoretype
    }

    ButtonGroup {
        id: keystoregroup
    }

    ColumnLayout {
        width: parent.width

        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: qsTr('Do you want to create a new seed, restore using an existing seed, or restore from master key?')
        }
        RadioButton {
            ButtonGroup.group: keystoregroup
            property string keystoretype: 'createseed'
            checked: true
            text: qsTr('Create a new seed')
        }
        RadioButton {
            ButtonGroup.group: keystoregroup
            property string keystoretype: 'haveseed'
            text: qsTr('I already have a seed')
        }
        RadioButton {
            ButtonGroup.group: keystoregroup
            property string keystoretype: 'masterkey'
            text: qsTr('Use a master key')
        }
        RadioButton {
            enabled: false
            visible: false
            ButtonGroup.group: keystoregroup
            property string keystoretype: 'hardware'
            text: qsTr('Use a hardware device')
        }
    }
}

