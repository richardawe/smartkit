(function () {
  "use strict";

  // Data is injected by ../data/latest.js as window.SMARTKIT_DATA.
  // Script tags work with file:// (double-click open) and GitHub Pages alike —
  // no server required.

  var allItems = [];

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function scoreClass(score) {
    if (score >= 3) return "score-high";
    if (score >= 1.5) return "score-mid";
    return "score-low";
  }

  function fmtDate(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString(undefined, {
        year: "numeric", month: "short", day: "numeric"
      });
    } catch (e) { return iso; }
  }

  function renderCard(item) {
    var sc = scoreClass(item.score);
    var titleHtml = item.url
      ? '<a href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener">'
          + escapeHtml(item.title || "(no title)") + "</a>"
      : escapeHtml(item.title || "(no title)");

    var tags = (item.key_terms || []).slice(0, 4)
      .map(function (t) { return '<span class="tag">' + escapeHtml(t) + "</span>"; })
      .join(" ");

    var actionTag = (item.action_type && item.action_type !== "other")
      ? '<span class="tag action-tag">' + escapeHtml(item.action_type) + "</span>"
      : "";

    return [
      '<div class="card">',
      '  <div class="card-header">',
      '    <div class="card-title">' + titleHtml + "</div>",
      '    <span class="score-badge ' + sc + '">score ' + item.score + "</span>",
      "  </div>",
      item.summary
        ? '  <div class="card-summary">' + escapeHtml(item.summary) + "</div>"
        : "",
      '  <div class="card-meta">',
      "    " + escapeHtml(item.source || ""),
      item.published ? "    <span>" + fmtDate(item.published) + "</span>" : "",
      actionTag,
      tags,
      "  </div>",
      "</div>",
    ].join("\n");
  }

  function applyFilters() {
    var query = document.getElementById("search").value.toLowerCase();
    var typeFilter = document.getElementById("type-filter").value;
    var sourceFilter = document.getElementById("source-filter").value;

    var filtered = allItems.filter(function (item) {
      var text = [item.title, item.summary, item.source]
        .concat(item.key_terms || [])
        .join(" ")
        .toLowerCase();
      if (query && text.indexOf(query) === -1) return false;
      if (typeFilter && item.action_type !== typeFilter) return false;
      if (sourceFilter && item.source !== sourceFilter) return false;
      return true;
    });

    document.getElementById("count").textContent =
      "Showing " + filtered.length + " of " + allItems.length + " items";

    document.getElementById("cards").innerHTML = filtered.length
      ? filtered.map(renderCard).join("")
      : '<div class="empty">No items match the current filter.</div>';
  }

  function populateSources(items) {
    var seen = {};
    var sel = document.getElementById("source-filter");
    items.forEach(function (i) {
      if (i.source && !seen[i.source]) {
        seen[i.source] = true;
        var opt = document.createElement("option");
        opt.value = i.source;
        opt.textContent = i.source;
        sel.appendChild(opt);
      }
    });
  }

  // Read data injected by data/latest.js
  var data = window.SMARTKIT_DATA;
  if (!data) {
    document.getElementById("cards").innerHTML =
      '<div class="empty">'
      + "No data yet.<br>"
      + "Run <code>python pipeline/main.py</code> to generate data, then reload."
      + "</div>";
  } else {
    document.getElementById("dash-title").textContent = data.title || "SmartKit Dashboard";
    document.getElementById("dash-subtitle").textContent = data.subtitle || "";
    document.getElementById("generated-at").textContent = data.generated_at
      ? new Date(data.generated_at).toLocaleString()
      : "—";
    document.getElementById("item-count").textContent =
      data.item_count != null ? data.item_count : "—";
    if (data.schedule_note) {
      document.getElementById("schedule-note").textContent = data.schedule_note;
    }
    document.title = data.title || "SmartKit Dashboard";

    allItems = data.items || [];
    populateSources(allItems);
    applyFilters();
  }

  document.getElementById("search").addEventListener("input", applyFilters);
  document.getElementById("type-filter").addEventListener("change", applyFilters);
  document.getElementById("source-filter").addEventListener("change", applyFilters);
}());
