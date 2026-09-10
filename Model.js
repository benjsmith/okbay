// Shared status helpers for Okbay QML surfaces.
// The daemon publishes ~/.local/state/okbay/status.json. QML never talks
// to Kuzu or the wiki directly.

.pragma library

function homeDir() {
    return ""
}

function statusPath() {
    return ""
}

function defaultStatus() {
    return {
        ts: 0,
        state: "setup",
        pages: 0,
        nodes: 0,
        reviews_pending: 0,
        desk: null,
        atlas_url: "http://127.0.0.1:8766/atlas",
        api_url: "http://127.0.0.1:8766",
        workspace: "",
        message: "Run okbay setup"
    }
}

function parseStatus(text) {
    if (!text || !String(text).trim())
        return null
    try {
        var obj = JSON.parse(text)
        if (!obj || typeof obj !== "object")
            return null
        return obj
    } catch (e) {
        return null
    }
}

function isReady(status) {
    return !!(status && (status.state === "ready" || status.state === "curating" || status.state === "degraded"))
}

function needsSetup(status) {
    return !status || status.state === "setup" || status.state === "missing"
}

function label(status, stale) {
    if (!status || needsSetup(status))
        return "SETUP"
    if (stale)
        return "STALE"
    if (status.state === "curating")
        return "CURATE"
    if (status.state === "degraded")
        return "DEG"
    var desk = status.desk && status.desk.id ? String(status.desk.id) : ""
    if (desk)
        return desk.toUpperCase()
    var n = status.pages || status.nodes || 0
    return String(n)
}

function isStale(status, nowMs, staleAfterSec) {
    if (!status || !status.ts)
        return true
    var tsMs = Number(status.ts) > 1e12 ? Number(status.ts) : Number(status.ts) * 1000
    return (nowMs - tsMs) > (Number(staleAfterSec) * 1000)
}

function apiUrl(status) {
    if (status && status.api_url)
        return String(status.api_url).replace(/\/$/, "")
    return "http://127.0.0.1:8766"
}

function getJson(url, callback) {
    var xhr = new XMLHttpRequest()
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== XMLHttpRequest.DONE)
            return
        var parsed = null
        try { parsed = JSON.parse(xhr.responseText) } catch (e) { parsed = null }
        callback(parsed, xhr.status)
    }
    xhr.open("GET", url)
    xhr.send()
}

function postJson(url, body, callback) {
    var xhr = new XMLHttpRequest()
    xhr.onreadystatechange = function () {
        if (xhr.readyState !== XMLHttpRequest.DONE)
            return
        var parsed = null
        try { parsed = JSON.parse(xhr.responseText) } catch (e) { parsed = null }
        callback(parsed, xhr.status)
    }
    xhr.open("POST", url)
    xhr.setRequestHeader("Content-Type", "application/json")
    xhr.send(JSON.stringify(body || {}))
}

function colorToken(name, fallback) {
    try {
        if (typeof Color !== "undefined" && Color[name])
            return Color[name]
    } catch (e) {}
    return fallback
}
