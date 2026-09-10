# okbay shell verbs — source from ~/.config/okbay/okbay.sh
okbay-ask() { okbay ask "$*"; }
okbay-curate() { okbay desk start curate "$*"; }
okbay-work() { okbay desk start work "$*"; }
okbay-code() { okbay desk start code "$*"; }
okbay-ingest() { okbay ingest "${1:-}"; }
okbay-atlas() { okbay ui atlas "$1"; }
/ask()    { okbay ask "$*"; }
/curate() { okbay desk start curate "$*"; }
/work()   { okbay desk start work "$*"; }
/code()   { okbay desk start code "$*"; }
/ingest() { okbay ingest "$@"; }
/atlas()  { okbay ui atlas "$*"; }
