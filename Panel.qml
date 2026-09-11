// Okbay panel: Reviews inbox + standing desks + ingest hint.
// Note: Omarchy loads this entry (panel kind) instead of Overlay.qml when both exist.
// Atlas opens a frameless Chromium app window for now — Qt WebEngine inside Quickshell
// crashes on this Omarchy/TCG guest (Chromium CommandLine/argv init).

import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import "Model.js" as Model

Item {
  id: root
  property bool opened: false
  property var status: null
  property var reviews: []
  readonly property string statusPath: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
  readonly property color themeBg: (typeof Color !== "undefined" && Color.popups && Color.popups.background) ? Color.popups.background : "#f2111111"
  readonly property color themeBorder: (typeof Color !== "undefined" && Color.popups && Color.popups.border) ? Color.popups.border : "#44ffffff"
  readonly property color themeFg: (typeof Color !== "undefined" && Color.foreground) ? Color.foreground : "#f2f2f2"
  readonly property color themeMuted: (typeof Color !== "undefined" && Color.dark_foreground) ? Color.dark_foreground : "#888888"
  readonly property color themeAccent: (typeof Color !== "undefined" && Color.accent) ? Color.accent : "#6be8b3"
  readonly property string apiUrl: (status && status.api_url) ? status.api_url : "http://127.0.0.1:8766"
  readonly property string atlasUrl: (status && status.atlas_url) ? status.atlas_url : (apiUrl + "/atlas")

  function open(payloadJson) {
    var surface = "panel"
    try {
      var payload = payloadJson ? JSON.parse(payloadJson) : {}
      if (payload && payload.surface)
        surface = String(payload.surface)
    } catch (e) {}
    if (surface === "atlas") {
      openAtlasWindow()
      return
    }
    opened = true
    statusFile.reload()
    Model.getJson(root.apiUrl + "/api/reviews?state=pending", function (parsed) {
      root.reviews = (parsed && (parsed.reviews || parsed)) || []
    })
  }
  function close() { opened = false }
  function toggle(payloadJson) { opened ? close() : open(payloadJson) }

  function openAtlasWindow() {
    // Frameless app-mode Chromium — no browser chrome; closest working fullscreen path
    // until Qt WebEngine can initialize under Quickshell.
    Quickshell.execDetached([
      "sh", "-lc",
      "pkill -f 'chromium.*8766/atlas' 2>/dev/null || true; " +
      "chromium --ozone-platform=wayland --disable-gpu --app=" + root.atlasUrl + " --start-fullscreen >/tmp/okbay-atlas-chrome.log 2>&1 &"
    ])
  }

  function seat(kind) {
    Model.postJson(root.apiUrl + "/api/desk/start", {"kind": kind}, function () { statusFile.reload() })
  }
  function resolveReview(id, action) {
    Model.postJson(root.apiUrl + "/api/review", {"id": id, "action": action}, function () {
      Model.getJson(root.apiUrl + "/api/reviews?state=pending", function (parsed) {
        root.reviews = (parsed && (parsed.reviews || parsed)) || []
      })
    })
  }
  function ingestClipboardPath() {
    Model.postJson(root.apiUrl + "/api/ingest", {"path": ""}, function () { statusFile.reload() })
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
    WlrLayershell.keyboardFocus: WlrKeyboardFocus.OnDemand
    WlrLayershell.namespace: "okbay-panel"
    anchors.top: true
    anchors.right: true
    margins.top: 42
    margins.right: 12
    implicitWidth: 380
    implicitHeight: 520
    Rectangle {
      anchors.fill: parent
      radius: 12
      color: root.themeBg
      border.color: root.themeBorder
      border.width: 1
      Column {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10
        Text { text: "Okbay"; color: root.themeFg; font.pixelSize: 16; font.bold: true }
        Text { text: root.status && root.status.workspace ? root.status.workspace : "~/Work/okbay"; color: root.themeMuted; font.pixelSize: 11 }
        Row {
          spacing: 6
          Button { text: "Ask"; onClicked: Quickshell.execDetached(["okbay", "ask", "--prompt"]) }
          Button { text: "Atlas"; onClicked: root.openAtlasWindow() }
          Button { text: "Ingest"; onClicked: root.ingestClipboardPath() }
        }
        Text { text: "Desks"; color: root.themeMuted; font.pixelSize: 12 }
        Row {
          spacing: 6
          Button { text: "Curate"; onClicked: root.seat("curate") }
          Button { text: "Work"; onClicked: root.seat("work") }
          Button { text: "Code"; onClicked: root.seat("code") }
          Button { text: "Deck"; onClicked: root.seat("deck") }
        }
        Text { text: root.status && root.status.desk ? (root.status.desk.id + " · " + root.status.desk.state) : "no desk seated"; color: root.themeMuted; font.pixelSize: 11 }
        Text { text: "Reviews (" + root.reviews.length + ")"; color: root.themeMuted; font.pixelSize: 12 }
        ListView {
          width: parent.width; height: 280; clip: true; model: root.reviews
          delegate: Rectangle {
            width: parent.width; height: 72; color: "transparent"
            Column {
              anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
              Text { text: (modelData.title || modelData.stem || modelData.id || "review"); color: root.themeFg; font.pixelSize: 13 }
              Text { text: (modelData.kind || modelData.state || ""); color: root.themeMuted; font.pixelSize: 10 }
              Row {
                spacing: 6
                Button { text: "Accept"; onClicked: root.resolveReview(modelData.id, "accept") }
                Button { text: "Reject"; onClicked: root.resolveReview(modelData.id, "reject") }
              }
            }
          }
        }
        Button { text: "Close"; onClicked: root.close() }
      }
    }
  }
}
