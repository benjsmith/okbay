// Okbay bar widget. Left click: Atlas overlay. Right click: Reviews panel.
import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import "Model.js" as Model

BarWidget {
  id: root
  moduleName: "benjsmith.okbay"
  property var status: null
  property bool stale: true
  readonly property string statusPath: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
  readonly property string chipText: Model.label(status, stale)
  readonly property bool setupMode: Model.needsSetup(status)

  FileView {
    id: statusFile
    path: root.statusPath
    watchChanges: true
    printErrors: false
    onLoaded: {
      root.status = Model.parseStatus(statusFile.text())
      root.stale = Model.isStale(root.status, Date.now(), 240)
    }
    onLoadFailed: { root.status = null; root.stale = true }
  }

  Timer {
    interval: 4000; running: true; repeat: true
    onTriggered: statusFile.reload()
  }

  function summonOkbay(payload) {
    var body = payload || "{}"
    if (root.bar && root.bar.shell && root.bar.shell.summon)
      root.bar.shell.summon("benjsmith.okbay", body)
    else
      Quickshell.execDetached(["omarchy-shell", "shell", "summon", "benjsmith.okbay", body])
  }

  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    onClicked: function (mouse) {
      if (root.setupMode) {
        Quickshell.execDetached(["sh", "-lc", "command -v okbay >/dev/null && okbay setup"])
        return
      }
      if (mouse.button === Qt.RightButton)
        root.summonOkbay("{\"surface\":\"panel\"}")
      else
        root.summonOkbay("{\"surface\":\"atlas\"}")
    }
  }

  Text {
    anchors.centerIn: parent
    text: "OKBay " + root.chipText
    color: root.setupMode || root.stale ? "#d97757" : (parent.bar && parent.bar.foreground ? parent.bar.foreground : "#eeeeee")
    font.pixelSize: 12
  }
}
