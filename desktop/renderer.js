const $ = (id) => document.getElementById(id);
const PAGE = 100;
const S = {
  sid: null,
  filename: "",
  state: null,
  profile: null,
  sugg: [],
  compare: null,
  offset: 0,
  tab: "suggestions",
  opName: "fill_nulls",
  pending: null,
  busy: false,
  plan: null,
  cmd: "",
};

// ---------- helpers (all values go in as text nodes: no HTML injection) ----------
function h(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) e.setAttribute(k, v === true ? "" : v);
  }
  for (const k of kids.flat())
    if (k != null)
      e.append(k.nodeType ? k : document.createTextNode(String(k)));
  return e;
}

async function api(method, path, body) {
  const r = await window.cleanai.api(method, path, body);
  if (r.status >= 400) {
    const d = r.data && r.data.detail;
    const e = new Error(
      typeof d === "string"
        ? d
        : d
        ? JSON.stringify(d)
        : `Request failed (${r.status})`
    );
    e.status = r.status;
    throw e;
  }
  return r.data;
}

function setStatus(msg, bad = false) {
  const s = $("status");
  s.textContent = msg;
  s.className = bad ? "bad" : "";
}

async function guard(fn) {
  if (S.busy) return;
  S.busy = true;
  document.body.classList.add("busy");
  try {
    await fn();
  } catch (e) {
    setStatus(e.message, true);
  } finally {
    S.busy = false;
    document.body.classList.remove("busy");
  }
}

function opText(op) {
  const { op: name, ...rest } = op;
  const args = Object.entries(rest)
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join(",") : v}`)
    .join(" ");
  return args ? `${name} ${args}` : name;
}

// ---------- refresh ----------
async function refresh() {
  if (!S.sid) return;
  const b = "/sessions/" + S.sid;
  S.state = await api("GET", b + "/state");
  if (S.offset >= S.state.rows) S.offset = 0;
  const [prev, prof, sg, cmp] = await Promise.all([
    api("GET", `${b}/preview?offset=${S.offset}&limit=${PAGE}`),
    api("GET", b + "/profile"),
    api("GET", b + "/suggestions"),
    api("GET", b + "/compare"),
  ]);
  S.profile = prof;
  S.sugg = sg.suggestions;
  S.compare = cmp;
  renderHeader();
  renderGrid(prev);
  renderPanel();
}

async function loadPage() {
  renderGrid(
    await api(
      "GET",
      `/sessions/${S.sid}/preview?offset=${S.offset}&limit=${PAGE}`
    )
  );
}

// ---------- rendering ----------
function renderHeader() {
  const st = S.state;
  $("undo").disabled = !(st && st.can_undo);
  $("redo").disabled = !(st && st.can_redo);
  $("reset").disabled = !S.sid;
  $("export").disabled = !S.sid;
}

function renderGrid(prev) {
  const g = $("grid");
  g.replaceChildren();
  g.append(
    h(
      "table",
      {},
      h(
        "thead",
        {},
        h(
          "tr",
          {},
          h("th", { class: "idx" }, "#"),
          prev.columns.map((c) => h("th", {}, c))
        )
      ),
      h(
        "tbody",
        {},
        prev.rows.map((r, i) =>
          h(
            "tr",
            {},
            h("td", { class: "idx" }, prev.offset + i + 1),
            r.map((v) =>
              v === null
                ? h("td", { class: "null" }, "null")
                : h("td", {}, String(v))
            )
          )
        )
      )
    )
  );
  const from = prev.total_rows ? prev.offset + 1 : 0;
  $("pageinfo").textContent = `rows ${from}–${
    prev.offset + prev.rows.length
  } of ${prev.total_rows}`;
  $("prev").disabled = prev.offset === 0;
  $("next").disabled = prev.offset + PAGE >= prev.total_rows;
}

const TABS = [
  ["suggestions", "Suggestions"],
  ["ask", "Ask AI"],
  ["step", "Add step"],
  ["profile", "Profile"],
  ["history", "History"],
  ["report", "Report"],
];

function renderPanel() {
  $("tabs").replaceChildren(
    ...TABS.map(([k, l]) =>
      h(
        "button",
        {
          class: S.tab === k ? "tab on" : "tab",
          onclick: () => {
            S.tab = k;
            renderPanel();
          },
        },
        k === "suggestions" && S.sid ? `${l} (${S.sugg.length})` : l
      )
    )
  );
  const p = $("panel");
  p.replaceChildren();
  if (!S.sid) {
    p.append(h("p", { class: "muted" }, "No dataset loaded."));
    return;
  }
  p.append(
    {
      suggestions: suggestionsPanel,
      ask: askPanel,
      step: stepPanel,
      profile: profilePanel,
      history: historyPanel,
      report: reportPanel,
    }[S.tab]()
  );
}

function askPanel() {
  const model = h("input", {
    type: "text",
    value: localStorage.getItem("cleanai_model") || "qwen2.5-coder:3b",
  });
  const cmd = h(
    "textarea",
    {
      rows: 3,
      placeholder: "e.g. remove rows where age is blank",
      style:
        "width:100%;background:#14161a;color:#e6e6e6;border:1px solid #444;border-radius:4px;padding:6px",
    },
    S.cmd
  );
  const status = h("div", { class: "muted" }, "Checking Ollama…");
  const check = async () => {
    try {
      const st = await api(
        "GET",
        "/llm/status?model=" + encodeURIComponent(model.value)
      );
      status.textContent = !st.available
        ? "Ollama is not running. Install it from ollama.com and start it."
        : !st.model_installed
        ? `Model not installed. In a terminal run: ollama pull ${model.value}`
        : "Ready.";
    } catch (e) {
      status.textContent = e.message;
    }
  };
  check();
  model.addEventListener("change", check);
  const ask = h(
    "button",
    {
      onclick: () =>
        guard(async () => {
          S.cmd = cmd.value;
          localStorage.setItem("cleanai_model", model.value);
          setStatus("Thinking… this can take up to a minute on a slow CPU.");
          S.plan = await api("POST", `/sessions/${S.sid}/llm/interpret`, {
            command: S.cmd,
            model: model.value,
          });
          renderPanel();
          setStatus(
            S.plan.ops.length
              ? "Review the plan, then apply it."
              : "No steps proposed."
          );
        }),
    },
    "Ask"
  );
  const plan =
    S.plan &&
    h(
      "div",
      {},
      h("p", {}, S.plan.explanation),
      S.plan.previews.map((p, i) =>
        h(
          "div",
          { class: "card" },
          `${i + 1}. `,
          h("code", {}, opText(p.op)),
          h(
            "div",
            { class: "muted" },
            `${p.message} Rows ${p.rows_before} → ${p.rows_after}.`
          )
        )
      ),
      S.plan.ops.length
        ? h(
            "div",
            { class: "row" },
            h(
              "button",
              { onclick: applyPlan },
              `Apply ${S.plan.ops.length} step(s)`
            ),
            h(
              "button",
              {
                onclick: () => {
                  S.plan = null;
                  renderPanel();
                },
              },
              "Discard"
            )
          )
        : null
    );
  return h(
    "div",
    {},
    h(
      "label",
      { class: "field" },
      h("span", {}, "model (runs locally via Ollama)"),
      model
    ),
    status,
    h("div", { style: "height:8px" }),
    cmd,
    h("div", { style: "height:6px" }),
    ask,
    h("div", { style: "height:10px" }),
    plan
  );
}

async function applyPlan() {
  await guard(async () => {
    const ops = S.plan.ops;
    S.plan = null;
    let n = 0;
    try {
      for (const op of ops) {
        await api("POST", `/sessions/${S.sid}/apply`, { op });
        n++;
      }
    } finally {
      await refresh();
    }
    setStatus(`Applied ${n} AI step(s). Undo reverts them one by one.`);
  });
}

function suggestionsPanel() {
  if (!S.sugg.length) return h("p", { class: "muted" }, "No issues found.");
  const n = S.sugg.filter((s) => s.op).length;
  return h(
    "div",
    {},
    n > 1
      ? h("button", { onclick: applyAll }, `Apply all ${n} fixes in order`)
      : null,
    h("div", { style: "height:8px" }),
    S.sugg.map((s) =>
      h(
        "div",
        { class: "card" },
        h("div", {}, s.message),
        s.op
          ? h(
              "div",
              { class: "row" },
              h("code", {}, opText(s.op)),
              h("button", { onclick: () => applyOp(s.op) }, "Apply")
            )
          : h(
              "div",
              { class: "muted" },
              "Review manually. Never removed automatically."
            )
      )
    )
  );
}

const OPS = {
  fill_nulls: [
    ["column", "col"],
    ["strategy", ["median", "mean", "mode", "constant"]],
    ["value", "text", "for constant only"],
  ],
  drop_nulls: [
    ["columns", "cols", "none selected = all"],
    ["how", ["any", "all"]],
  ],
  drop_duplicates: [
    ["columns", "cols", "none selected = all"],
    ["keep", ["first", "last"]],
  ],
  cast_type: [
    ["column", "col"],
    ["to", ["int", "float", "str", "bool", "datetime"]],
  ],
  trim_text: [["column", "col"]],
  change_case: [
    ["column", "col"],
    ["case", ["lower", "upper", "title"]],
  ],
  filter_rows: [
    ["column", "col"],
    [
      "operator",
      ["eq", "ne", "gt", "gte", "lt", "lte", "contains", "is_null", "not_null"],
    ],
    ["value", "text", "keeps matching rows"],
  ],
  sort: [
    ["column", "col"],
    ["ascending", "bool"],
  ],
  rename_column: [
    ["column", "col"],
    ["new_name", "text"],
  ],
  drop_column: [["column", "col"]],
};

function stepPanel() {
  const cols = S.profile.columns.map((c) => c.name);
  const inputs = {};
  const fields = OPS[S.opName].map(([key, type, hint]) => {
    let el;
    if (type === "col")
      el = h(
        "select",
        {},
        cols.map((c) => h("option", { value: c }, c))
      );
    else if (type === "cols")
      el = h(
        "select",
        { multiple: true, size: Math.min(6, cols.length) },
        cols.map((c) => h("option", { value: c }, c))
      );
    else if (Array.isArray(type))
      el = h(
        "select",
        {},
        type.map((o) => h("option", { value: o }, o))
      );
    else if (type === "bool")
      el = h("input", { type: "checkbox", checked: true });
    else el = h("input", { type: "text" });
    inputs[key] = [el, type];
    return h(
      "label",
      { class: "field" },
      h("span", {}, key + (hint ? ` (${hint})` : "")),
      el
    );
  });
  const opSel = h(
    "select",
    {
      onchange: (e) => {
        S.opName = e.target.value;
        renderPanel();
      },
    },
    Object.keys(OPS).map((o) =>
      h("option", { value: o, selected: o === S.opName }, o)
    )
  );
  const collect = () => {
    const op = { op: S.opName };
    for (const [key, [el, type]] of Object.entries(inputs)) {
      if (type === "cols") {
        const v = [...el.selectedOptions].map((o) => o.value);
        if (v.length) op[key] = v;
      } else if (type === "bool") op[key] = el.checked;
      else if (el.value !== "") op[key] = el.value;
    }
    return op;
  };
  return h(
    "div",
    {},
    h("label", { class: "field" }, h("span", {}, "operation"), opSel),
    fields,
    h("button", { onclick: () => applyOp(collect()) }, "Apply step")
  );
}

function profilePanel() {
  const p = S.profile,
    q = p.quality;
  const bar = (label, v) =>
    h(
      "div",
      { class: "bar" },
      h("div", {}, `${label}: ${(v * 100).toFixed(1)}%`),
      h(
        "div",
        { class: "track" },
        h("div", { class: "fill", style: `width:${Math.round(v * 100)}%` })
      )
    );
  const detail = (c) => {
    if (c.kind === "numeric")
      return (
        `${c.min}…${c.max}` +
        (c.outliers ? `, ${c.outliers} outliers` : "") +
        (c.infinite ? `, ${c.infinite} inf` : "")
      );
    if (c.kind === "text")
      return [
        c.whitespace ? `${c.whitespace} spaced` : "",
        c.case_variants ? "case variants" : "",
        c.numeric_like ? "numbers as text" : "",
      ]
        .filter(Boolean)
        .join(", ");
    return "";
  };
  return h(
    "div",
    {},
    h(
      "div",
      { class: "card" },
      h(
        "div",
        {},
        `${p.rows} rows × ${p.cols} columns · ${p.null_cells} empty cells · ${p.duplicate_rows} duplicate rows`
      ),
      h(
        "div",
        { style: "font-size:20px;margin:6px 0" },
        `Quality score: ${q.score}`
      ),
      bar("Completeness", q.completeness),
      bar("Uniqueness", q.uniqueness),
      bar("Consistency", q.consistency),
      bar("Validity", q.validity),
      h(
        "div",
        { class: "muted" },
        "A diagnostic only. It does not prove the data is correct."
      )
    ),
    h(
      "table",
      { class: "ptable" },
      h(
        "tr",
        {},
        ["column", "type", "nulls", "unique", "notes"].map((t) =>
          h("th", {}, t)
        )
      ),
      p.columns.map((c) =>
        h(
          "tr",
          {},
          h("td", {}, c.name),
          h("td", {}, c.dtype),
          h("td", {}, `${c.nulls} (${c.null_pct}%)`),
          h("td", {}, c.unique),
          h("td", {}, detail(c))
        )
      )
    )
  );
}

function historyPanel() {
  const steps = S.state.steps;
  if (!steps.length) return h("p", { class: "muted" }, "No steps applied yet.");
  return h(
    "div",
    {},
    steps.map((s) =>
      h(
        "div",
        { class: "card" + (s.applied ? "" : " undone") },
        `${s.index + 1}. `,
        h("code", {}, opText(s.op)),
        s.applied ? "" : "  (undone)"
      )
    )
  );
}

function reportPanel() {
  const c = S.compare;
  const row = (k, a, b) =>
    h("tr", {}, h("td", {}, k), h("td", {}, a), h("td", {}, b));
  return h(
    "div",
    {},
    h(
      "table",
      { class: "ptable" },
      h(
        "tr",
        {},
        ["", "before", "after"].map((t) => h("th", {}, t))
      ),
      row("rows", c.rows_before, c.rows_after),
      row("columns", c.cols_before, c.cols_after),
      row("empty cells", c.null_cells_before, c.null_cells_after),
      row("duplicate rows", c.duplicates_before, c.duplicates_after),
      row("quality score", c.score_before, c.score_after)
    ),
    h(
      "p",
      {},
      `Steps applied: ${S.state.steps.filter((s) => s.applied).length}`
    ),
    c.rows_removed > 0
      ? h(
          "p",
          { class: "warn" },
          `${c.rows_removed} rows were removed. Check this before trusting the score.`
        )
      : null
  );
}

// ---------- actions ----------
async function applyOp(op) {
  await guard(async () => {
    const r = await api("POST", `/sessions/${S.sid}/apply`, { op });
    await refresh();
    setStatus(`${r.result.message} (memory ${r.state.process_mb} MB)`);
  });
}

async function applyAll() {
  await guard(async () => {
    const ops = S.sugg.filter((s) => s.op).map((s) => s.op);
    let n = 0;
    try {
      for (const op of ops) {
        await api("POST", `/sessions/${S.sid}/apply`, { op });
        n++;
      }
    } finally {
      await refresh();
    }
    setStatus(`Applied ${n} fixes.`);
  });
}

$("open").onclick = () =>
  guard(async () => {
    const p = await window.cleanai.pickOpen();
    if (!p) return;
    const sel = $("sheet");
    sel.replaceChildren();
    sel.hidden = true;
    if (/\.xls[xm]$/i.test(p)) {
      const { sheets } = await api("POST", "/sheets", { path: p });
      sheets.forEach((n) => sel.append(h("option", { value: n }, n)));
      sel.hidden = sheets.length < 2;
    }
    S.pending = p;
    $("importbox").hidden = false;
    setStatus("Ready to load: " + p.split(/[\\/]/).pop());
  });

$("load").onclick = () =>
  guard(async () => {
    if (!S.pending) return;
    const body = { path: S.pending, all_text: $("alltext").checked };
    const sel = $("sheet");
    if (sel.options.length) body.sheet = sel.value;

    let d;
    try {
      d = await api("POST", "/load", body);
    } catch (e) {
      if (e.status !== 413 || !confirm(e.message + "\n\nLoad anyway?")) throw e;
      d = await api("POST", "/load", { ...body, force: true });
    }

    if (S.sid) {
      try {
        await api("DELETE", "/sessions/" + S.sid);
      } catch {}
    }
    Object.assign(S, {
      sid: d.session_id,
      filename: d.filename,
      state: d.state,
      offset: 0,
      tab: "suggestions",
      pending: null,
      plan: null,
    });
    $("importbox").hidden = true;
    await refresh();
    setStatus(
      `Loaded ${d.filename}: ${d.state.rows} rows, ${d.state.cols} columns.`
    );
  });

$("undo").onclick = () =>
  guard(async () => {
    await api("POST", `/sessions/${S.sid}/undo`);
    await refresh();
    setStatus("Undone.");
  });
$("redo").onclick = () =>
  guard(async () => {
    await api("POST", `/sessions/${S.sid}/redo`);
    await refresh();
    setStatus("Redone.");
  });
$("reset").onclick = () =>
  guard(async () => {
    if (!confirm("Discard all steps and go back to the original data?")) return;
    await api("POST", `/sessions/${S.sid}/reset`);
    await refresh();
    setStatus("Reset to original.");
  });
$("export").onclick = () =>
  guard(async () => {
    const p = await window.cleanai.pickSave(
      S.filename.replace(/\.[^.]+$/, "") + "_clean",
      S.state.rows > 200000
    );
    if (!p) return;
    const r = await api("POST", `/sessions/${S.sid}/export`, { path: p });
    setStatus(`Exported ${r.rows} rows to ${r.path}`);
  });
$("prev").onclick = () =>
  guard(async () => {
    S.offset = Math.max(0, S.offset - PAGE);
    await loadPage();
  });
$("next").onclick = () =>
  guard(async () => {
    if (S.offset + PAGE < S.state.rows) {
      S.offset += PAGE;
      await loadPage();
    }
  });

renderHeader();
renderPanel();
