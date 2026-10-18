/* assets/fork/update.js */
/* CrossWatch - "Update now" for the native LXC installation (fork addition) */
/* Turns the release notice in the notification menu into an update action. The
   update itself runs outside the app (systemd unit), see fork_update.py. */
(() => {
  "use strict";
  if (window.__cwForkUpdate) return;
  window.__cwForkUpdate = true;

  const HREF = "#cw-fork-update";
  const t = (s) => window.cwI18n?.t?.(s) ?? s;
  let info = { supported: false, admin: false };
  let latest = "";

  async function loadInfo() {
    try {
      const r = await fetch("/api/fork/update", { credentials: "same-origin", cache: "no-store" });
      if (r.ok) info = await r.json();
    } catch {}
    return info;
  }

  function rewrite(items) {
    return (items || []).map((item) => {
      if (item?.icon !== "system_update_alt") return item;
      latest = String(item.id || "");
      return { ...item, href: HREF, action: info.supported && info.admin ? "Update now" : "How to update" };
    });
  }

  function hookNotifications() {
    const n = window.CW?.Notifications;
    if (!n || n.__cwForkUpdate) return !!n;
    const orig = n.setSource.bind(n);
    n.setSource = (name, source) => orig(name, name === "updates" && source ? { ...source, items: rewrite(source.items) } : source);
    n.__cwForkUpdate = true;
    window.dispatchEvent(new Event("cw:notifications-refresh"));
    return true;
  }

  function overlay(text) {
    let el = document.getElementById("cw-fork-update-overlay");
    if (!el) {
      el = document.createElement("div");
      el.id = "cw-fork-update-overlay";
      el.style.cssText = "position:fixed;inset:0;z-index:99999;display:grid;place-items:center;background:rgba(5,8,14,.78);color:#eef5ff;font:600 16px system-ui,sans-serif;text-align:center;padding:24px";
      document.body.appendChild(el);
    }
    el.textContent = text;
  }

  async function poll(startedAt) {
    for (let i = 0; i < 200; i++) {
      await new Promise((res) => setTimeout(res, 3000));
      try {
        const r = await fetch("/api/fork/update", { credentials: "same-origin", cache: "no-store" });
        if (!r.ok) continue;
        const s = (await r.json()).status || {};
        if ((s.finished_at || 0) < startedAt) continue;
        if (s.state === "done") {
          overlay(t("Update installed. Reloading…"));
          setTimeout(() => location.reload(), 1500);
          return;
        }
        if (s.state === "failed") {
          document.getElementById("cw-fork-update-overlay")?.remove();
          alert(t("The update failed:") + "\n" + (s.message || ""));
          return;
        }
      } catch {
        overlay(t("CrossWatch is restarting…"));
      }
    }
  }

  async function runUpdate() {
    await loadInfo();
    if (!info.supported) {
      alert(t("Updates from the web interface are not set up on this installation. Run 'update' in the container console instead."));
      return;
    }
    if (!info.admin) {
      alert(t("Administrator access required."));
      return;
    }
    if (!confirm(t("Install the update now? CrossWatch restarts and is unavailable for about a minute."))) return;
    const startedAt = Math.floor(Date.now() / 1000);
    const r = await fetch("/api/fork/update", { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" }, body: "{}" });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || !data.ok) {
      alert(data.error ? t(data.error) : t("Update could not be started."));
      return;
    }
    overlay(t("Installing update… This takes about a minute."));
    poll(startedAt);
  }

  document.addEventListener("click", (e) => {
    const a = e.target?.closest?.(`a[href$="${HREF}"]`);
    if (!a) return;
    e.preventDefault();
    e.stopPropagation();
    runUpdate();
  }, true);

  loadInfo().then(() => {
    if (!hookNotifications()) {
      const timer = setInterval(() => { if (hookNotifications()) clearInterval(timer); }, 500);
      setTimeout(() => clearInterval(timer), 20000);
    }
  });
})();
