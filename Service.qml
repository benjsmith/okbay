import QtQuick
import Quickshell
import Quickshell.Io

Item {
  id: root
  visible: false
  readonly property string statusPath: (QuickShell.env ? Quickshell.env("HOME") : "") + "/.local/state/okbay/status.json"
  property var status: null
  FileView {
    id: statusFile
    path: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
    watchChanges: true
    printErrors: false
    onLoaded: {
      try { root.status = JSON.parse(statusFile.text()) } catch (e) { root.status = null }
    }
  }
  Timer { interval: 5000; running: true; repeat: true; onTriggered: statusFile.reload() }
}
