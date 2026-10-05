// Okbay bar widget.
// Left-click: open Atlas (okbay-open-atlas.sh / frameless Chromium).
// Right-click: open Library view (Atlas host #view=library via OKBAY_ATLAS_URL).
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
  readonly property string apiUrl: (status && status.api_url) ? status.api_url : "http://127.0.0.1:8766"
  readonly property string atlasUrl: (status && status.atlas_url) ? status.atlas_url : (apiUrl + "/atlas")
  readonly property bool htmlUiEnabled: !(status && status.html_ui_enabled === false)

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

  function runAtlasLauncher(urlOverride) {
    // Charter Phase 5a: skip Chromium when QML viewer owns the surface.
    if (!root.htmlUiEnabled) {
      console.log("okbay: viewer_mode=qml — HTML atlas launcher suppressed")
      root.summonOkbay('{"surface":"panel"}')
      return
    }
    // Prefer contrib/okbay-open-atlas.sh (focus-or-launch Chromium --class=OkbayAtlas).
    // OKBAY_ATLAS_URL overrides the default /atlas (e.g. #view=library).
    var url = urlOverride || root.atlasUrl
    Quickshell.execDetached([
      "sh", "-lc",
      "export OKBAY_SKIP_SUMMON=1 OKBAY_ATLAS_URL='" + url + "'; " +
      "for s in \"$HOME/.config/omarchy/plugins/benjsmith.okbay/contrib/okbay-open-atlas.sh\" " +
      "\"$HOME/src/okbay/contrib/okbay-open-atlas.sh\"; do " +
      "[ -x \"$s\" ] && exec \"$s\"; done; " +
      "if command -v uwsm-app >/dev/null 2>&1; then " +
      "nohup uwsm-app -- chromium --ozone-platform=wayland --class=OkbayAtlas --app='" + url + "' --start-fullscreen >/tmp/okbay-atlas-chrome.log 2>&1 & " +
      "else " +
      "nohup chromium --ozone-platform=wayland --class=OkbayAtlas --app='" + url + "' --start-fullscreen >/tmp/okbay-atlas-chrome.log 2>&1 & " +
      "fi"
    ])
  }

  function openAtlas() {
    root.runAtlasLauncher(root.atlasUrl)
  }

  function openLibrary() {
    // Library view on the Atlas host (views shell hash routing).
    var base = root.atlasUrl.split("#")[0]
    root.runAtlasLauncher(base + "#view=library")
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
        root.openLibrary()
      else
        root.openAtlas()
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
