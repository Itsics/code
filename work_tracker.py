"""
Work Hours Tracker
Run:  python work_tracker.py
Open: http://127.0.0.1:5002
"""

import sqlite3
import json
import csv
import io
from datetime import datetime, date, timedelta
from flask import Flask, request, jsonify, Response

app = Flask(__name__)
DB = "work_hours.db"


# ─── DB helpers ──────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT NOT NULL,          -- YYYY-MM-DD
                start     TEXT NOT NULL,          -- HH:MM
                end       TEXT,                   -- HH:MM  (NULL = clocked in, not yet out)
                minutes   INTEGER,                -- computed on clock-out / manual save
                note      TEXT DEFAULT ''
            )
        """)
        conn.commit()


def row_to_dict(row):
    d = dict(row)
    # compute duration label
    if d["minutes"] is not None:
        h, m = divmod(d["minutes"], 60)
        d["duration"] = f"{h}h {m:02d}m"
    else:
        d["duration"] = "In progress…"
    return d


def calc_minutes(start_str, end_str):
    fmt = "%H:%M"
    s = datetime.strptime(start_str, fmt)
    e = datetime.strptime(end_str, fmt)
    delta = (e - s).total_seconds() / 60
    return int(delta) if delta > 0 else 0


# ─── API routes ───────────────────────────────────────────────────────────────

@app.route("/api/clock_in", methods=["POST"])
def clock_in():
    """Start a new session right now."""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    note = request.json.get("note", "") if request.json else ""
    with get_db() as conn:
        # check if already clocked in
        open_row = conn.execute(
            "SELECT id FROM sessions WHERE end IS NULL"
        ).fetchone()
        if open_row:
            return jsonify({"error": "Already clocked in. Clock out first."}), 400
        cur = conn.execute(
            "INSERT INTO sessions (date, start, note) VALUES (?,?,?)",
            (date_str, time_str, note),
        )
        conn.commit()
        session_id = cur.lastrowid
    return jsonify({"id": session_id, "date": date_str, "start": time_str})


@app.route("/api/clock_out", methods=["POST"])
def clock_out():
    """End the currently open session."""
    now = datetime.now()
    time_str = now.strftime("%H:%M")
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, start FROM sessions WHERE end IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return jsonify({"error": "Not clocked in."}), 400
        minutes = calc_minutes(row["start"], time_str)
        conn.execute(
            "UPDATE sessions SET end=?, minutes=? WHERE id=?",
            (time_str, minutes, row["id"]),
        )
        conn.commit()
    return jsonify({"id": row["id"], "end": time_str, "minutes": minutes})


@app.route("/api/status")
def status():
    """Return the currently open session (if any)."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE end IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        return jsonify({"clocked_in": True, "session": row_to_dict(row)})
    return jsonify({"clocked_in": False})


@app.route("/api/sessions", methods=["GET"])
def list_sessions():
    """Return sessions filtered by optional ?from=YYYY-MM-DD&to=YYYY-MM-DD."""
    from_date = request.args.get("from", "2000-01-01")
    to_date = request.args.get("to", "2099-12-31")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE date BETWEEN ? AND ? ORDER BY date DESC, start DESC",
            (from_date, to_date),
        ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


@app.route("/api/sessions", methods=["POST"])
def add_session():
    """Manually add a completed session."""
    data = request.json
    date_str = data.get("date")
    start_str = data.get("start")
    end_str = data.get("end")
    note = data.get("note", "")
    if not (date_str and start_str and end_str):
        return jsonify({"error": "date, start, end are required"}), 400
    minutes = calc_minutes(start_str, end_str)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO sessions (date, start, end, minutes, note) VALUES (?,?,?,?,?)",
            (date_str, start_str, end_str, minutes, note),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (new_id,)).fetchone()
    return jsonify(row_to_dict(row)), 201


@app.route("/api/sessions/<int:session_id>", methods=["PUT"])
def update_session(session_id):
    data = request.json
    start_str = data.get("start")
    end_str = data.get("end")
    note = data.get("note", "")
    date_str = data.get("date")
    minutes = calc_minutes(start_str, end_str) if start_str and end_str else None
    with get_db() as conn:
        conn.execute(
            "UPDATE sessions SET date=?, start=?, end=?, minutes=?, note=? WHERE id=?",
            (date_str, start_str, end_str, minutes, note, session_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
    return jsonify(row_to_dict(row))


@app.route("/api/sessions/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    with get_db() as conn:
        conn.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        conn.commit()
    return jsonify({"deleted": session_id})


@app.route("/api/summary")
def summary():
    """Aggregate totals: by day, week, month."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date, SUM(minutes) as total FROM sessions WHERE minutes IS NOT NULL GROUP BY date ORDER BY date DESC"
        ).fetchall()

    by_day = [{"date": r["date"], "minutes": r["total"]} for r in rows]

    # weekly: group by ISO week
    week_map = {}
    for r in rows:
        d = datetime.strptime(r["date"], "%Y-%m-%d")
        week_key = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        week_map[week_key] = week_map.get(week_key, 0) + r["total"]
    by_week = sorted(
        [{"week": k, "minutes": v} for k, v in week_map.items()],
        key=lambda x: x["week"], reverse=True
    )

    # monthly
    month_map = {}
    for r in rows:
        month_key = r["date"][:7]  # YYYY-MM
        month_map[month_key] = month_map.get(month_key, 0) + r["total"]
    by_month = sorted(
        [{"month": k, "minutes": v} for k, v in month_map.items()],
        key=lambda x: x["month"], reverse=True
    )

    return jsonify({"by_day": by_day, "by_week": by_week, "by_month": by_month})


@app.route("/api/export")
def export_csv():
    """Download all sessions as CSV."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT date, start, end, minutes, note FROM sessions ORDER BY date, start"
        ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Start", "End", "Minutes", "Hours", "Note"])
    for r in rows:
        hours = round(r["minutes"] / 60, 2) if r["minutes"] else ""
        writer.writerow([r["date"], r["start"], r["end"] or "", r["minutes"] or "", hours, r["note"]])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=work_hours.csv"},
    )


# ─── Frontend ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return HTML


HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Work Hours Tracker</title>
<style>
  :root {
    --bg: #0f1419; --surface: #16181c; --surface2: #1d2127;
    --border: #2f3336; --text: #e7e9ea; --muted: #71767b;
    --accent: #1d9bf0; --green: #00ba7c; --red: #f4212e;
    --yellow: #ffd400;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: "Segoe UI", system-ui, sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; padding: 1.5rem; }

  header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem; }
  header h1 { font-size: 1.4rem; font-weight: 700; }
  header .sub { color: var(--muted); font-size: .85rem; margin-top: .15rem; }

  nav { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
  nav button { padding: .45rem 1rem; border-radius: 20px; border: 1px solid var(--border); background: var(--surface2); color: var(--text); cursor: pointer; font-size: .85rem; transition: all .15s; }
  nav button:hover { border-color: var(--accent); color: var(--accent); }
  nav button.active { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }

  .page { display: none; }
  .page.active { display: block; }

  /* Clock card */
  .clock-card { background: var(--surface); border-radius: 14px; padding: 2rem; max-width: 480px; margin-bottom: 1.5rem; border: 1px solid var(--border); }
  .clock-card .current-time { font-size: 2.8rem; font-weight: 700; letter-spacing: -1px; margin-bottom: .25rem; }
  .clock-card .current-date { color: var(--muted); margin-bottom: 1.5rem; }
  .clock-card .status-badge { display: inline-flex; align-items: center; gap: .4rem; padding: .3rem .8rem; border-radius: 20px; font-size: .8rem; font-weight: 600; margin-bottom: 1.2rem; }
  .badge-in  { background: #00ba7c22; color: var(--green); border: 1px solid #00ba7c44; }
  .badge-out { background: #f4212e22; color: var(--red);   border: 1px solid #f4212e44; }
  .badge-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; animation: pulse 1.5s infinite; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
  .note-field { width: 100%; background: var(--surface2); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: .6rem .9rem; font-size: .9rem; margin-bottom: 1rem; outline: none; }
  .note-field:focus { border-color: var(--accent); }
  .btn { padding: .7rem 1.4rem; border-radius: 8px; border: none; cursor: pointer; font-size: .95rem; font-weight: 600; transition: opacity .15s; }
  .btn:hover { opacity: .85; }
  .btn-green  { background: var(--green); color: #000; }
  .btn-red    { background: var(--red);   color: #fff; }
  .btn-accent { background: var(--accent); color: #fff; }
  .btn-ghost  { background: var(--surface2); color: var(--text); border: 1px solid var(--border); }
  .session-info { background: var(--surface2); border-radius: 8px; padding: .8rem 1rem; font-size: .85rem; color: var(--muted); margin-top: 1rem; }
  .session-info span { color: var(--text); font-weight: 600; }

  /* Manual entry */
  .form-card { background: var(--surface); border-radius: 14px; padding: 1.5rem; max-width: 520px; border: 1px solid var(--border); margin-bottom: 1.5rem; }
  .form-card h3 { margin-bottom: 1rem; font-size: 1rem; }
  .form-row { display: flex; gap: .75rem; flex-wrap: wrap; margin-bottom: .75rem; }
  .form-group { display: flex; flex-direction: column; gap: .3rem; flex: 1; min-width: 120px; }
  .form-group label { font-size: .78rem; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }
  .form-group input { background: var(--surface2); border: 1px solid var(--border); color: var(--text); border-radius: 8px; padding: .55rem .8rem; font-size: .9rem; outline: none; }
  .form-group input:focus { border-color: var(--accent); }
  .msg { font-size: .83rem; padding: .4rem .8rem; border-radius: 6px; margin-top: .5rem; }
  .msg-ok  { background: #00ba7c22; color: var(--green); }
  .msg-err { background: #f4212e22; color: var(--red); }

  /* History / table */
  .filter-bar { display: flex; gap: .75rem; flex-wrap: wrap; align-items: flex-end; margin-bottom: 1rem; }
  .filter-bar .form-group { flex: 0 0 auto; }
  table { width: 100%; border-collapse: collapse; background: var(--surface); border-radius: 12px; overflow: hidden; font-size: .88rem; }
  th { background: var(--surface2); padding: .6rem .9rem; text-align: left; font-size: .72rem; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); font-weight: 600; }
  td { padding: .6rem .9rem; border-top: 1px solid var(--border); vertical-align: middle; }
  tr:hover td { background: var(--surface2); }
  .chip { display: inline-block; padding: .15rem .5rem; border-radius: 4px; font-size: .75rem; font-weight: 600; }
  .chip-done { background: #00ba7c22; color: var(--green); }
  .chip-open { background: #ffd40022; color: var(--yellow); }
  .icon-btn { background: none; border: none; cursor: pointer; color: var(--muted); font-size: 1rem; padding: .2rem .35rem; border-radius: 4px; transition: color .15s; }
  .icon-btn:hover { color: var(--text); background: var(--border); }
  .total-row td { font-weight: 700; color: var(--accent); background: var(--surface2); }

  /* Summary */
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.2rem; margin-bottom: 1.5rem; }
  .summary-card { background: var(--surface); border-radius: 14px; border: 1px solid var(--border); overflow: hidden; }
  .summary-card h3 { padding: .9rem 1rem; background: var(--surface2); font-size: .85rem; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
  .summary-card table { border-radius: 0; }
  .summary-card th { background: transparent; }
  .bar-cell { position: relative; }
  .bar { height: 6px; border-radius: 3px; background: var(--accent); margin-top: 4px; transition: width .4s; }

  .empty { color: var(--muted); text-align: center; padding: 2rem; font-size: .9rem; }

  /* Modal */
  .modal-overlay { display: none; position: fixed; inset: 0; background: #000a; z-index: 100; align-items: center; justify-content: center; }
  .modal-overlay.open { display: flex; }
  .modal { background: var(--surface); border-radius: 14px; border: 1px solid var(--border); padding: 1.5rem; width: 90%; max-width: 440px; }
  .modal h3 { margin-bottom: 1rem; }
  .modal-actions { display: flex; gap: .5rem; justify-content: flex-end; margin-top: 1rem; }

  @media (max-width: 500px) {
    body { padding: 1rem; }
    .clock-card .current-time { font-size: 2rem; }
  }
</style>
</head>
<body>

<header>
  <div>
    <h1>⏱ Work Hours Tracker</h1>
    <div class="sub">Track, calculate, and export your working time</div>
  </div>
  <a class="btn btn-ghost" href="/api/export" style="text-decoration:none;font-size:.82rem;padding:.4rem .85rem;">⬇ Export CSV</a>
</header>

<nav>
  <button class="active" onclick="showPage('clock')">Clock</button>
  <button onclick="showPage('manual')">Manual Entry</button>
  <button onclick="showPage('history')">History</button>
  <button onclick="showPage('summary')">Summary</button>
</nav>

<!-- ═══ CLOCK PAGE ═══ -->
<div id="page-clock" class="page active">
  <div class="clock-card">
    <div class="current-time" id="liveClock">00:00:00</div>
    <div class="current-date" id="liveDate"></div>
    <div class="status-badge badge-out" id="statusBadge">
      <span class="badge-dot"></span>
      <span id="statusText">Not clocked in</span>
    </div>
    <input id="clockNote" class="note-field" placeholder="What are you working on? (optional)" />
    <div style="display:flex;gap:.6rem;flex-wrap:wrap">
      <button class="btn btn-green" id="btnClockIn"  onclick="clockIn()">Clock In</button>
      <button class="btn btn-red"   id="btnClockOut" onclick="clockOut()" disabled>Clock Out</button>
    </div>
    <div id="openSessionInfo" class="session-info" style="display:none"></div>
  </div>
</div>

<!-- ═══ MANUAL ENTRY PAGE ═══ -->
<div id="page-manual" class="page">
  <div class="form-card">
    <h3>Add Work Session Manually</h3>
    <div class="form-row">
      <div class="form-group" style="flex:2;min-width:140px">
        <label>Date</label>
        <input type="date" id="manDate" />
      </div>
      <div class="form-group">
        <label>Start</label>
        <input type="time" id="manStart" />
      </div>
      <div class="form-group">
        <label>End</label>
        <input type="time" id="manEnd" />
      </div>
    </div>
    <div class="form-row">
      <div class="form-group" style="flex:1">
        <label>Note (optional)</label>
        <input type="text" id="manNote" placeholder="Project / task description" />
      </div>
    </div>
    <button class="btn btn-accent" onclick="addManual()">Add Session</button>
    <div id="manMsg"></div>
  </div>
</div>

<!-- ═══ HISTORY PAGE ═══ -->
<div id="page-history" class="page">
  <div class="filter-bar">
    <div class="form-group">
      <label>From</label>
      <input type="date" id="hFrom" oninput="loadHistory()" />
    </div>
    <div class="form-group">
      <label>To</label>
      <input type="date" id="hTo" oninput="loadHistory()" />
    </div>
    <button class="btn btn-ghost" style="margin-bottom:0" onclick="clearFilter()">Clear filter</button>
  </div>
  <div id="historyTable"><p class="empty">Loading…</p></div>
</div>

<!-- ═══ SUMMARY PAGE ═══ -->
<div id="page-summary" class="page">
  <div class="summary-grid">
    <div class="summary-card">
      <h3>By Day</h3>
      <div id="sumDay"><p class="empty">Loading…</p></div>
    </div>
    <div class="summary-card">
      <h3>By Week</h3>
      <div id="sumWeek"><p class="empty">Loading…</p></div>
    </div>
    <div class="summary-card">
      <h3>By Month</h3>
      <div id="sumMonth"><p class="empty">Loading…</p></div>
    </div>
  </div>
</div>

<!-- Edit Modal -->
<div class="modal-overlay" id="editModal">
  <div class="modal">
    <h3>Edit Session</h3>
    <input type="hidden" id="editId" />
    <div class="form-row">
      <div class="form-group" style="flex:2">
        <label>Date</label>
        <input type="date" id="editDate" />
      </div>
      <div class="form-group">
        <label>Start</label>
        <input type="time" id="editStart" />
      </div>
      <div class="form-group">
        <label>End</label>
        <input type="time" id="editEnd" />
      </div>
    </div>
    <div class="form-group" style="margin-bottom:.5rem">
      <label>Note</label>
      <input type="text" id="editNote" placeholder="Project / task" />
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-accent" onclick="saveEdit()">Save</button>
    </div>
  </div>
</div>

<script>
// ── helpers ──────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);

function fmt(minutes) {
  if (minutes == null) return '—';
  const h = Math.floor(minutes / 60), m = minutes % 60;
  return `${h}h ${String(m).padStart(2,'0')}m`;
}
function fmtHrs(minutes) {
  return (minutes / 60).toFixed(2) + ' hrs';
}

async function api(url, method='GET', body=null) {
  const opts = { method, headers: {'Content-Type':'application/json'} };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  return r.json();
}

// ── live clock ───────────────────────────────────────────────────────────────
function tickClock() {
  const now = new Date();
  $('liveClock').textContent = now.toLocaleTimeString();
  $('liveDate').textContent  = now.toLocaleDateString(undefined, {weekday:'long', year:'numeric', month:'long', day:'numeric'});
}
setInterval(tickClock, 1000);
tickClock();

// ── clock status ─────────────────────────────────────────────────────────────
let clockedIn = false;

async function refreshStatus() {
  const data = await api('/api/status');
  clockedIn = data.clocked_in;
  const badge = $('statusBadge');
  const info  = $('openSessionInfo');
  if (clockedIn) {
    badge.className = 'status-badge badge-in';
    $('statusText').textContent = 'Clocked in';
    $('btnClockIn').disabled  = true;
    $('btnClockOut').disabled = false;
    const s = data.session;
    info.style.display = 'block';
    info.innerHTML = `Clocked in since <span>${s.start}</span> on <span>${s.date}</span>${s.note ? ' · ' + s.note : ''}`;
  } else {
    badge.className = 'status-badge badge-out';
    $('statusText').textContent = 'Not clocked in';
    $('btnClockIn').disabled  = false;
    $('btnClockOut').disabled = true;
    info.style.display = 'none';
  }
}
refreshStatus();

async function clockIn() {
  const note = $('clockNote').value.trim();
  const res = await api('/api/clock_in', 'POST', { note });
  if (res.error) { alert(res.error); return; }
  $('clockNote').value = '';
  refreshStatus();
}

async function clockOut() {
  const res = await api('/api/clock_out', 'POST');
  if (res.error) { alert(res.error); return; }
  alert(`Clocked out. Session: ${fmt(res.minutes)}`);
  refreshStatus();
  if ($('page-history').classList.contains('active')) loadHistory();
  if ($('page-summary').classList.contains('active')) loadSummary();
}

// ── nav ───────────────────────────────────────────────────────────────────────
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));
  $('page-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
  if (name === 'history') loadHistory();
  if (name === 'summary') loadSummary();
}

// ── manual entry ──────────────────────────────────────────────────────────────
// default date to today
$('manDate').value = new Date().toISOString().slice(0,10);

async function addManual() {
  const body = {
    date:  $('manDate').value,
    start: $('manStart').value,
    end:   $('manEnd').value,
    note:  $('manNote').value.trim(),
  };
  if (!body.date || !body.start || !body.end) {
    showMsg('manMsg', 'Please fill date, start and end.', false);
    return;
  }
  const res = await api('/api/sessions', 'POST', body);
  if (res.error) { showMsg('manMsg', res.error, false); return; }
  showMsg('manMsg', `Added: ${body.date} ${body.start}–${body.end} (${fmt(res.minutes)})`, true);
  $('manNote').value = $('manStart').value = $('manEnd').value = '';
}

function showMsg(id, text, ok) {
  const el = $(id);
  el.className = 'msg ' + (ok ? 'msg-ok' : 'msg-err');
  el.textContent = text;
  setTimeout(() => el.textContent = '', 4000);
}

// ── history ───────────────────────────────────────────────────────────────────
// default: last 30 days
const today = new Date();
$('hTo').value   = today.toISOString().slice(0,10);
const month_ago  = new Date(today); month_ago.setDate(today.getDate()-30);
$('hFrom').value = month_ago.toISOString().slice(0,10);

async function loadHistory() {
  const from = $('hFrom').value;
  const to   = $('hTo').value;
  let url = '/api/sessions';
  if (from || to) url += `?from=${from||'2000-01-01'}&to=${to||'2099-12-31'}`;
  const rows = await api(url);
  renderHistory(rows);
}

function renderHistory(rows) {
  if (!rows.length) {
    $('historyTable').innerHTML = '<p class="empty">No sessions found.</p>';
    return;
  }
  let totalMin = 0;
  let html = `<table>
    <thead><tr>
      <th>Date</th><th>Start</th><th>End</th><th>Duration</th><th>Note</th><th>Status</th><th></th>
    </tr></thead><tbody>`;
  for (const r of rows) {
    if (r.minutes) totalMin += r.minutes;
    const done = r.end != null;
    html += `<tr>
      <td>${r.date}</td>
      <td>${r.start}</td>
      <td>${r.end || '—'}</td>
      <td><strong>${r.duration}</strong></td>
      <td style="color:var(--muted)">${r.note || ''}</td>
      <td><span class="chip ${done?'chip-done':'chip-open'}">${done?'Done':'Open'}</span></td>
      <td style="white-space:nowrap">
        <button class="icon-btn" title="Edit"   onclick="openEdit(${r.id},'${r.date}','${r.start}','${r.end||''}','${(r.note||'').replace(/'/g,"\\'")}')">✏</button>
        <button class="icon-btn" title="Delete" onclick="deleteRow(${r.id})">🗑</button>
      </td>
    </tr>`;
  }
  const h = Math.floor(totalMin/60), m = totalMin%60;
  html += `</tbody><tfoot><tr class="total-row">
    <td colspan="3">Total</td>
    <td>${h}h ${String(m).padStart(2,'0')}m</td>
    <td colspan="3" style="color:var(--muted);font-weight:400;font-size:.82rem">${(totalMin/60).toFixed(2)} hrs</td>
  </tr></tfoot></table>`;
  $('historyTable').innerHTML = html;
}

function clearFilter() {
  $('hFrom').value = ''; $('hTo').value = '';
  loadHistory();
}

async function deleteRow(id) {
  if (!confirm('Delete this session?')) return;
  await api(`/api/sessions/${id}`, 'DELETE');
  loadHistory();
}

// ── edit modal ────────────────────────────────────────────────────────────────
function openEdit(id, date, start, end, note) {
  $('editId').value    = id;
  $('editDate').value  = date;
  $('editStart').value = start;
  $('editEnd').value   = end;
  $('editNote').value  = note;
  $('editModal').classList.add('open');
}
function closeModal() { $('editModal').classList.remove('open'); }

async function saveEdit() {
  const id = $('editId').value;
  const body = {
    date:  $('editDate').value,
    start: $('editStart').value,
    end:   $('editEnd').value,
    note:  $('editNote').value.trim(),
  };
  await api(`/api/sessions/${id}`, 'PUT', body);
  closeModal();
  loadHistory();
}

// close modal on overlay click
$('editModal').addEventListener('click', e => { if (e.target === $('editModal')) closeModal(); });

// ── summary ───────────────────────────────────────────────────────────────────
async function loadSummary() {
  const data = await api('/api/summary');
  renderSummaryTable('sumDay',   data.by_day,   r => r.date,  r => r.minutes);
  renderSummaryTable('sumWeek',  data.by_week,  r => r.week,  r => r.minutes);
  renderSummaryTable('sumMonth', data.by_month, r => r.month, r => r.minutes);
}

function renderSummaryTable(containerId, rows, labelFn, minFn) {
  const el = $(containerId);
  if (!rows.length) { el.innerHTML = '<p class="empty">No data yet.</p>'; return; }
  const max = Math.max(...rows.map(minFn));
  let html = `<table><thead><tr><th>Period</th><th>Time</th><th>Hours</th></tr></thead><tbody>`;
  for (const r of rows) {
    const mins = minFn(r);
    const pct  = max ? Math.round(mins/max*100) : 0;
    html += `<tr>
      <td>${labelFn(r)}</td>
      <td class="bar-cell">${fmt(mins)}<div class="bar" style="width:${pct}%"></div></td>
      <td style="color:var(--muted);font-size:.82rem">${fmtHrs(mins)}</td>
    </tr>`;
  }
  const total = rows.reduce((s,r) => s+minFn(r), 0);
  html += `</tbody><tfoot><tr class="total-row"><td>Total</td><td>${fmt(total)}</td><td style="font-weight:400;color:var(--muted);font-size:.82rem">${fmtHrs(total)}</td></tr></tfoot></table>`;
  el.innerHTML = html;
}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    init_db()
    print("Work Hours Tracker — open http://127.0.0.1:5002")
    app.run(host="127.0.0.1", port=5002, debug=False)
