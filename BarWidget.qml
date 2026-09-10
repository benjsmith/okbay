// Okbay bar widget. Left click: Atlas overlay. Right click: Reviews panel.
// SETUP gate when the daemon has not been installed.
// Uses the Quattro BarWidget host type (same contract as khephri.sia).

import QtQuick
import Quickshell
import Quickshell.Io
import qs.Ui
import "Model.js" as Model

BarWidget {
  id: root
  moduleName: "benjsmith.okbay"

  property var status: null
  property bool statusResolved: false
  property bool stale: true
  property real nowMs: Date.now()

  readonly property string statusPath: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
  readonly property real staleAfterSec: {
    var v = root.setting ? root.setting("staleAfterSec", 240) : 240
    return Number(v)
  }
  readonly property string chipText: Model.label(status, stale)
  readonly property bool setupMode: Model.needsSetup(status)

  FileView {
    id: statusFile
    path: root.statusPath
    watchChanges: true
    printErrors: false
    onLoaded: root.applyStatus()
    onFileChanged: applyTimer.restart()
    onLoadFailed: {
      root.status = null
      root.statusResolved = true
      root.stale = true
    }
  }

  Timer {
    id: applyTimer
    interval: 150
    onTriggered: statusFile.reload()
  }

  Timer {
    interval: 4000
    running: true
    repeat: true
    onTriggered: {
      root.nowMs = Date.now()
      root.stale = Model.isStale(root.status, root.nowMs, root.staleAfterSec)
      statusFile.reload()
    }
  }

  function applyStatus() {
    var parsed = Model.parseStatus(statusFile.text())
    root.status = parsed
    root.statusResolved = true
    root.stale = Model.isStale(parsed, Date.now(), root.staleAfterSec)
  }

  function summonOkbay(payload) {
    var body = payload || "{}"
    if (root.bar && root.bar.shell && root.bar.shell.summon)
      root.bar.shell.summon("benjsmith.okbay", body)
    else
      Quickshell.execDetached(["omarchy-shell", "shell", "summon", "benjsmith.okbay", body])
  }

  function runSetup() {
    Quickshell.execDetached(["sh", "-lc", "command -v okbay >/dev/null && okbay setup || (command -v foot && foot -e bash -lc 'echo Okbay is not on PATH yet. Clone github.com/benjsmith/okbay and run contrib/setup.sh; read')"])
  }

  MouseArea {
    anchors.fill: parent
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: function (mouse) {
      if (root.setupMode) {
        root.runSetup()
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
    text: "\u25c9 " + root.chipText
    color: {
      if (root.setupMode || root.stale)
        return "#d97757"
      if (root.status && root.status.reviews_pending > 0)
        return "#e0af4b"
      return parent.bar && parent.bar.foreground ? parent.bar.foreground : "#eeeeee"
    }
    font.pixelSize: 12
  }
}
