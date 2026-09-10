# Okbay shell verbs. Source from ~/.bashrc.
okbay-rail() {
  local line="$*"
  case "$line" in
    !*) eval "${line#!}" ;;
    /curate*) okbay desk start curate "${line#/curate}" ;;
    /work*)   okbay desk start work "${line#/work}" ;;
    /code*)   okbay desk start code "${line#/code}" ;;
    /deck*)   okbay desk start deck "${line#/deck}" ;;
    /ingest*) okbay ingest ${line#/ingest} ;;
    /atlas*)  omarchy-shell shell summon benjsmith.okbay "{\"q\":\"${line#/atlas}\"}" 2>/dev/null || okbay search ${line#/atlas} --json ;;
    /ask*)    okbay ask ${line#/ask} ;;
    *)        okbay ask "$line" ;;
  esac
}
ask()    { okbay ask "$*"; }
curate() { okbay desk start curate "$*"; }
