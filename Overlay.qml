import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "Model.js" as Model

Item {
  id: root
  property bool opened: false
  property string filterText: ""
  property var results: []
  property var status: null
  readonly property string statusPath: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
  readonly property string apiUrl: (status && status.api_url) ? status.api_url : "http://127.0.0.1:8766"
  readonly property string atlasUrl: {
    var base = (status && status.atlas_url) ? status.atlas_url : (apiUrl + "/atlas")
    if (filterText && filterText.trim().length)
      return base + "?q=" + encodeURIComponent(filterText.trim())
    return base
  }
  function open() { opened = true }
  function close() { opened = false }
  function toggle() { opened ? close() : open() }
  function runSearch() {
    Model.getJson(root.apiUrl + "/api/search?q=" + encodeURIComponent(filterText.trim()), function (parsed) {
      root.results = (parsed && (parsed.hits || parsed.results)) || []
    })
  }
  FileView {
    id: statusFile
    path: root.statusPath
    watchChanges: true
    printErrors: false
    onLoaded: { var p = Model.parseStatus(statusFile.text()); if (p) root.status = p }
  }
  PanelWindow {
    visible: root.opened
    color: "transparent"
    WlrLayershell.layer: WlrLayer.Overlay
    anchors.top: true; anchors.bottom: true; anchors.left: true; anchors.right: true
    MouseArea { anchors.fill: parent; onClicked: root.close() }
    Rectangle {
      anchors.centerIn: parent
      width: Math.min(parent.width - 80, 1100)
      height: Math.min(parent.height - 80, 720)
      radius: 12
      color: "#e6111111"
      Column {
        anchors.fill: parent; anchors.margins: 16; spacing: 10
        Text { text: "Okbay Atlas"; color: "#f2f2f2"; font.pixelSize: 18; font.bold: true }
        TextField {
          width: 420
          placeholderText: "search the graph"
          text: root.filterText
          onTextChanged: root.filterText = text
          onAccepted: root.runSearch()
          Keys.onEscapePressed: root.close()
        }
        Button { text: "Search"; onClicked: root.runSearch() }
        Text { text: root.atlasUrl; color: "#888888"; font.pixelSize: 11 }
      }
    }
  }
}
