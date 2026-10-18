// Okbay Atlas overlay entry.
// Prefer Panel.qml on Omarchy (panel kind wins). This file kept for overlay-only installs.
// Qt WebEngine in Quickshell crashes here; Atlas opens frameless Chromium instead.

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
  readonly property string statusPath: (Quickshell.env("HOME") || "") + "/.local/state/okbay/status.json"
  readonly property string apiUrl: (status && status.api_url) ? status.api_url : "http://127.0.0.1:8766"
  readonly property string atlasUrl: (status && status.atlas_url) ? status.atlas_url : (apiUrl + "/atlas")
  readonly property bool htmlUiEnabled: !(status && status.html_ui_enabled === false)
  readonly property color themeFg: (typeof Color !== "undefined" && Color.foreground) ? Color.foreground : "#f2f2f2"
  readonly property color themeMuted: (typeof Color !== "undefined" && Color.dark_foreground) ? Color.dark_foreground : "#888888"
  readonly property color themeBg: (typeof Color !== "undefined" && Color.popups && Color.popups.background) ? Color.popups.background : "#e6111111"
  readonly property color themeBorder: (typeof Color !== "undefined" && Color.popups && Color.popups.border) ? Color.popups.border : "#44ffffff"

  function open(payloadJson) {
    if (!root.htmlUiEnabled) { console.log("okbay: qml mode — HTML atlas off"); return }

    opened = true
    statusFile.reload()
    // Delegate focus-or-launch to helper (skip summon → avoid recursion).
    Quickshell.execDetached([
      "sh", "-lc",
      "export OKBAY_SKIP_SUMMON=1 OKBAY_ATLAS_URL='" + root.atlasUrl + "'; " +
      "for s in \"$HOME/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh\" " +
      "\"$HOME/src/okbay/contrib/okbay-open-atlas.sh\"; do " +
      "[ -x \"$s\" ] && exec \"$s\"; done; " +
      "if command -v uwsm-app >/dev/null 2>&1; then " +
      "nohup uwsm-app -- chromium --ozone-platform=wayland --app='" + root.atlasUrl + "' --start-fullscreen >/tmp/okbay-atlas-chrome.log 2>&1 & " +
      "else " +
      "nohup chromium --ozone-platform=wayland --app='" + root.atlasUrl + "' --start-fullscreen >/tmp/okbay-atlas-chrome.log 2>&1 & " +
      "fi"
    ])
    // brief toast then auto-close overlay chrome
    closeTimer.restart()
  }
  function close() { opened = false }
  function toggle(payloadJson) { opened ? close() : open(payloadJson) }

  Timer { id: closeTimer; interval: 600; onTriggered: root.close() }

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
    exclusiveZone: 0
    anchors.top: true
    anchors.horizontalCenter: true
    margins.top: 48
    implicitWidth: 420
    implicitHeight: 64
    Rectangle {
      anchors.fill: parent
      radius: 10
      color: root.themeBg
      border.color: root.themeBorder
      Text {
        anchors.centerIn: parent
        color: root.themeFg
        font.pixelSize: 14
        text: "Opening Atlas fullscreen…"
      }
    }
  }
}
