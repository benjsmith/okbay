// Okbay Atlas overlay. Search the graph, halo hits, locate the file.
// Summoned by the bar widget or `omarchy-shell shell summon benjsmith.okbay`.
// The force-directed canvas is the daemon's /atlas page; this QML is chrome.

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
  property int selectedIndex: 0
  property var status: null
  readonly property string statusPath: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
  readonly property string apiUrl: (status && status.api_url) ? status.api_url : "http://127.0.0.1:8766"
  readonly property color themeBg: (typeof Color !== "undefined" && Color.popups && Color.popups.background) ? Color.popups.background : "#e6111111"
  readonly property color themeBorder: (typeof Color !== "undefined" && Color.popups && Color.popups.border) ? Color.popups.border : "#44ffffff"
  readonly property color themeFg: (typeof Color !== "undefined" && Color.foreground) ? Color.foreground : "#f2f2f2"
  readonly property color themeMuted: (typeof Color !== "undefined" && Color.dark_foreground) ? Color.dark_foreground : "#888888"
  readonly property color themeAccent: (typeof Color !== "undefined" && Color.accent) ? Color.accent : "#6be8b3"
  readonly property string atlasUrl: {
    var base = (status && status.atlas_url) ? status.atlas_url : (apiUrl + "/atlas")
    if (filterText && filterText.trim().length)
      return base + "?q=" + encodeURIComponent(filterText.trim())
    return base
  }

  function open(payloadJson) {
    opened = true
    try {
      var payload = payloadJson ? JSON.parse(payloadJson) : {}
      if (payload && payload.q)
        filterText = String(payload.q)
    } catch (e) {}
    statusFile.reload()
    searchField.forceActiveFocus()
    if (filterText.length)
      runSearch()
  }

  function close() {
    opened = false
    filterText = ""
    results = []
  }

  function toggle(payloadJson) {
    if (opened) close()
    else open(payloadJson)
  }

  function runSearch() {
    var q = filterText.trim()
    Model.getJson(root.apiUrl + "/api/search?q=" + encodeURIComponent(q), function (parsed) {
      if (!parsed) { root.results = []; return }
      root.results = parsed.hits || parsed.results || []
      root.selectedIndex = 0
    })
  }

  function locateSelected() {
    if (!results.length) return
    var item = results[Math.max(0, Math.min(selectedIndex, results.length - 1))]
    var stem = item.stem || item.path || item.id || ""
    if (!stem) return
    Model.getJson(root.apiUrl + "/api/locate?stem=" + encodeURIComponent(stem), function () {})
  }

  function openPage() {
    if (!results.length) return
    var item = results[Math.max(0, Math.min(selectedIndex, results.length - 1))]
    var stem = item.stem || item.path || ""
    if (stem)
      Quickshell.execDetached(["okbay", "open", stem])
  }

  FileView {
    id: statusFile
    path: root.statusPath
    watchChanges: true
    printErrors: false
    onLoaded: {
      var parsed = Model.parseStatus(statusFile.text())
      if (parsed) root.status = parsed
    }
  }

  PanelWindow {
    visible: root.opened
    color: "transparent"
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
    anchors.top: true
    anchors.bottom: true
    anchors.left: true
    anchors.right: true

    MouseArea { anchors.fill: parent; onClicked: root.close() }

    Rectangle {
      id: card
      anchors.centerIn: parent
      width: Math.min(parent.width - 80, 1100)
      height: Math.min(parent.height - 80, 720)
      radius: 12
      color: root.themeBg
      border.color: root.themeBorder
      border.width: 1
      MouseArea { anchors.fill: parent; onClicked: {} }

      Column {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 10

        Row {
          width: parent.width
          spacing: 10
          Text {
            text: "Okbay Atlas"
            color: root.themeFg
            font.pixelSize: 18
            font.bold: true
            anchors.verticalCenter: parent.verticalCenter
          }
          TextField {
            id: searchField
            width: 420
            placeholderText: "search the graph"
            text: root.filterText
            onTextChanged: root.filterText = text
            onAccepted: root.runSearch()
            Keys.onEscapePressed: root.close()
            Keys.onDownPressed: root.selectedIndex = Math.min(root.selectedIndex + 1, Math.max(0, root.results.length - 1))
            Keys.onUpPressed: root.selectedIndex = Math.max(0, root.selectedIndex - 1)
            Keys.onReturnPressed: root.locateSelected()
          }
          Button { text: "Search"; onClicked: root.runSearch() }
          Button { text: "Locate"; onClicked: root.locateSelected() }
          Button { text: "Open"; onClicked: root.openPage() }
          Item { width: 8; height: 1 }
          Text {
            text: root.status && root.status.pages ? (root.status.pages + " pages") : "no daemon"
            color: root.themeMuted
            anchors.verticalCenter: parent.verticalCenter
          }
        }

        Row {
          width: parent.width
          height: parent.height - 56
          spacing: 12
          Rectangle {
            width: 280
            height: parent.height
            color: "#22000000"
            radius: 8
            border.color: "#22ffffff"
            ListView {
              id: hits
              anchors.fill: parent
              anchors.margins: 8
              model: root.results
              clip: true
              delegate: Rectangle {
                width: hits.width
                height: 48
                color: index === root.selectedIndex ? "#33409eff" : "transparent"
                MouseArea {
                  anchors.fill: parent
                  onClicked: root.selectedIndex = index
                  onDoubleClicked: root.locateSelected()
                }
                Column {
                  anchors.verticalCenter: parent.verticalCenter
                  anchors.left: parent.left
                  anchors.leftMargin: 8
                  Text {
                    text: (modelData.title || modelData.stem || modelData.id || "untitled")
                    color: root.themeFg
                    font.pixelSize: 13
                  }
                  Text {
                    text: (modelData.kind || "") + (modelData.path ? "  " + modelData.path : "")
                    color: root.themeMuted
                    font.pixelSize: 10
                  }
                }
              }
            }
          }
          Rectangle {
            width: parent.width - 292
            height: parent.height
            color: "#11000000"
            radius: 8
            Text {
              anchors.centerIn: parent
              visible: !root.status || Model.needsSetup(root.status)
              text: "Run  okbay setup  then drop files into ~/Work/okbay/vault"
              color: root.themeFg
              font.pixelSize: 16
            }
            Text {
              anchors.bottom: parent.bottom
              anchors.horizontalCenter: parent.horizontalCenter
              anchors.bottomMargin: 12
              visible: !!(root.status && !Model.needsSetup(root.status))
              text: "Canvas: " + root.atlasUrl + "   (open in browser if WebView is unavailable)"
              color: root.themeMuted
              font.pixelSize: 11
            }
            MouseArea {
              anchors.fill: parent
              onDoubleClicked: Quickshell.execDetached(["xdg-open", root.atlasUrl])
            }
          }
        }
      }
    }
  }
}
