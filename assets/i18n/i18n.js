/* assets/i18n/i18n.js */
/* CrossWatch - runtime UI translation (fork addition) */
/* Translates English UI text in the DOM using window.CW_I18N_DICT. Loaded
   synchronously in <head> so text is replaced before the first paint. */
(() => {
  "use strict";
  if (window.cwI18n) return;

  const COOKIE = "cw_lang";
  const LANGS = { en: "English", de: "Deutsch" };
  const ATTRS = ["title", "placeholder", "aria-label", "alt", "data-tip", "data-tooltip", "data-title", "label"];
  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "CODE", "PRE", "NOSCRIPT", "svg", "SVG", "math"]);

  const readCookie = () => {
    const m = document.cookie.match(/(?:^|;\s*)cw_lang=([a-z]{2})/);
    return m ? m[1] : "";
  };
  const lang = (document.documentElement.getAttribute("data-cw-lang") || readCookie() || "en").toLowerCase();
  const dict = (window.CW_I18N_DICT && window.CW_I18N_DICT.lang === lang) ? window.CW_I18N_DICT : null;
  const strings = dict?.strings || {};
  const active = !!dict && lang !== "en";

  // ---- lookup -----------------------------------------------------------
  const norm = (s) => s.replace(/\s+/g, " ").trim();
  const exact = new Map();
  const patterns = [];   // {re, out, words}
  const byWord = new Map();
  const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Separators in meta lines such as "Movie - 2026 - 2h ago"
  const SEP = / [-·•|–] /;

  const values = new Set();
  for (const [k, v] of Object.entries(strings)) {
    if (!v) continue;
    values.add(norm(v));
    if (/\{\d+\}/.test(k)) {
      // A pattern made of two or more placeholders around a single word is too
      // loose: it would also rewrite user data such as "openid profile email".
      const literalWords = (k.replace(/\{\d+\}/g, " ").match(/[A-Za-z]{2,}/g) || []).length;
      if ((k.match(/\{\d+\}/g) || []).length >= 2 && literalWords < 2) continue;
      const order = [];
      const src = k.split(/(\{\d+\})/).map((part) => {
        const m = part.match(/^\{(\d+)\}$/);
        if (m) { order.push(+m[1]); return "([\\s\\S]*?)"; }
        return reEsc(part);
      }).join("");
      const words = (k.replace(/\{\d+\}/g, " ").match(/[A-Za-z]{3,}/g) || []);
      const entry = { re: new RegExp("^" + src + "$"), out: v, order, len: k.replace(/\{\d+\}/g, "").length, sep: SEP.test(k) };
      patterns.push(entry);
      const key = (words.sort((a, b) => b.length - a.length)[0] || "").toLowerCase();
      if (!byWord.has(key)) byWord.set(key, []);
      byWord.get(key).push(entry);
    } else {
      exact.set(k, v);
    }
  }

  // Rules for text built from numbers, e.g. "30s ago" -> "vor 30 s": [regex, replacement]
  const rules = (dict?.rules || []).map(([re, out]) => [new RegExp("^" + re + "$"), out]);

  const cache = new Map();
  const missing = new Set();
  const debug = (() => { try { return localStorage.getItem("cw_i18n_debug") === "1"; } catch { return false; } })();

  function translate(text, depth = 0) {
    const key = norm(text);
    if (!key || !/[A-Za-z]/.test(key)) return null;
    if (cache.has(key)) return cache.get(key);
    let out = exact.get(key) ?? null;
    if (out == null) {
      for (const [re, rep] of rules) {
        if (re.test(key)) { out = key.replace(re, rep); break; }
      }
    }
    if (out == null && !values.has(key)) {
      // collect candidates from every word, most specific pattern first
      const cands = new Set(byWord.get("") || []);
      for (const w of new Set((key.match(/[A-Za-z]{3,}/g) || []).map((x) => x.toLowerCase()))) {
        for (const p of byWord.get(w) || []) cands.add(p);
      }
      for (const p of [...cands].sort((a, b) => b.len - a.len)) {
        const m = key.match(p.re);
        if (!m) continue;
        const vals = p.order.map((_, i) => m[i + 1]);
        // "{0} ago" must not swallow a whole "Movie - 2026 - 2h ago" line
        if (!p.sep && vals.some((v) => SEP.test(` ${v ?? ""} `))) continue;
        out = p.out.replace(/\{(\d+)\}/g, (_, n) => {
          const v = vals[p.order.indexOf(+n)] ?? "";
          return (depth < 2 ? translate(v, depth + 1) : exact.get(norm(v))) ?? v;
        });
        break;
      }
    }
    if (out == null && depth < 2 && SEP.test(key)) {
      // translate each part of a separated line on its own
      const parts = key.split(/( [-·•|–] )/);
      let changed = false;
      const tr = parts.map((part, i) => {
        if (i % 2) return part;
        const t = translate(part, depth + 1);
        if (t != null && t !== part) changed = true;
        return t ?? part;
      });
      if (changed) out = tr.join("");
    }
    if (out != null) values.add(norm(out));
    else if (debug && active && key.length > 1 && !values.has(key) && /[A-Z ]/.test(key)) missing.add(key);
    if (cache.size > 20000) cache.clear();
    cache.set(key, out);
    return out;
  }

  function withSpace(orig, tr) {
    const lead = orig.match(/^\s*/)[0];
    const trail = orig.match(/\s*$/)[0];
    return lead + tr + trail;
  }

  // ---- DOM walking ------------------------------------------------------
  const done = new WeakMap(); // node -> translated value we wrote

  const isIcon = (el) => {
    const c = el.className;
    return typeof c === "string" && (c.includes("material-symbol") || c.includes("material-icons"));
  };

  // Icon elements: their text is a glyph name ("help"), but their title/aria-label is real text.
  function skipped(el, attrs = false) {
    for (let n = el; n && n.nodeType === 1; n = n.parentNode) {
      if (SKIP.has(n.nodeName)) return true;
      if (n.isContentEditable) return true;
      if (n.hasAttribute("data-no-i18n") || n.getAttribute("translate") === "no") return true;
      if (!attrs && isIcon(n)) return true;
    }
    return false;
  }

  function doText(node) {
    const v = node.data;
    if (done.get(node) === v) return;
    if (!v || v.length > 2000 || !/[A-Za-z]/.test(v)) return;
    const parent = node.parentNode;
    if (!parent || parent.nodeType !== 1 || skipped(parent)) return;
    const tr = translate(v);
    if (tr != null) {
      const nv = withSpace(v, tr);
      done.set(node, nv);
      if (nv !== v) node.data = nv;
    }
  }

  function doAttrs(el) {
    if (skipped(el, true)) return;
    for (const a of ATTRS) {
      const v = el.getAttribute(a);
      if (!v) continue;
      const tr = translate(v);
      if (tr != null && tr !== v) el.setAttribute(a, tr);
    }
    if (el.nodeName === "INPUT" && /^(button|submit|reset)$/i.test(el.type) && el.value) {
      const tr = translate(el.value);
      if (tr != null && tr !== el.value) el.value = tr;
    }
  }

  function walk(root) {
    if (root.nodeType === 3) return doText(root);
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1) {
      if (SKIP.has(root.nodeName)) return;
      doAttrs(root);
      if (isIcon(root)) return;
    }
    const tw = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        if (n.nodeType === 1 && isIcon(n)) { doAttrs(n); return NodeFilter.FILTER_REJECT; }
        if (n.nodeType === 1 && (SKIP.has(n.nodeName) || n.hasAttribute("data-no-i18n"))) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    let n;
    while ((n = tw.nextNode())) {
      if (n.nodeType === 3) doText(n);
      else doAttrs(n);
    }
  }

  // ---- dialogs ----------------------------------------------------------
  function wrapDialogs() {
    for (const name of ["alert", "confirm", "prompt"]) {
      const orig = window[name];
      if (typeof orig !== "function" || orig.__cwI18n) continue;
      const wrapped = function (msg, ...rest) {
        if (typeof msg === "string") {
          const tr = msg.split("\n").map((line) => (line.trim() ? (translate(line) ?? line) : line)).join("\n");
          return orig.call(window, tr, ...rest);
        }
        return orig.call(window, msg, ...rest);
      };
      wrapped.__cwI18n = true;
      window[name] = wrapped;
    }
  }

  // ---- language switch --------------------------------------------------
  function setLang(next) {
    const l = LANGS[next] ? next : "en";
    document.cookie = `${COOKIE}=${l}; path=/; max-age=31536000; SameSite=Lax`;
    location.reload();
  }

  function mountSwitch() {
    const host = document.getElementById("settings-interface");
    if (!host || document.getElementById("profile-pref-language")) return;
    const row = document.createElement("div");
    row.className = "cw-set-row";
    row.innerHTML =
      '<label class="cw-set-copy" for="profile-pref-language"><strong>Language</strong>' +
      "<small>Language of the CrossWatch interface in this browser.</small></label>" +
      '<span class="cw-set-inline"><select id="profile-pref-language" class="cw-set-input" data-cw-native-select="true"></select></span>';
    const sel = row.querySelector("select");
    for (const [code, label] of Object.entries(LANGS)) {
      const o = document.createElement("option");
      o.value = code;
      o.textContent = label;
      o.setAttribute("data-no-i18n", "");
      if (code === lang) o.selected = true;
      sel.appendChild(o);
    }
    sel.addEventListener("change", () => setLang(sel.value));
    const head = host.querySelector(".cw-set-head");
    if (head && head.nextSibling) host.insertBefore(row, head.nextSibling);
    else host.appendChild(row);
    if (active) walk(row);
  }

  // ---- start ------------------------------------------------------------
  const api = {
    lang,
    languages: { ...LANGS },
    t: (s) => (active ? translate(s) ?? s : s),
    setLang,
    missing: () => [...missing].sort(),
    retranslate: () => active && walk(document.documentElement),
  };
  window.cwI18n = api;

  if (active) {
    document.documentElement.lang = lang;
    wrapDialogs();
    const queue = new Set();
    let scheduled = false;
    const flush = () => {
      scheduled = false;
      for (const n of queue) if (n.isConnected) walk(n);
      queue.clear();
    };
    const mo = new MutationObserver((records) => {
      for (const r of records) {
        if (r.type === "childList") r.addedNodes.forEach((n) => queue.add(n));
        else if (r.type === "characterData") queue.add(r.target);
        else if (r.type === "attributes") queue.add(r.target.nodeType === 1 ? r.target : r.target.parentNode);
      }
      // translate in the same microtask turn to avoid an English flash
      if (!scheduled) { scheduled = true; flush(); }
    });
    mo.observe(document.documentElement, {
      childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ATTRS.concat(["value"]),
    });
    walk(document.documentElement);
    document.addEventListener("DOMContentLoaded", () => { wrapDialogs(); walk(document.documentElement); }, { once: true });
  }

  const tryMount = () => mountSwitch();
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", tryMount, { once: true });
  else tryMount();
  new MutationObserver(() => { if (document.getElementById("settings-interface") && !document.getElementById("profile-pref-language")) mountSwitch(); })
    .observe(document.documentElement, { childList: true, subtree: true });
})();
