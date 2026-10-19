/* Fabric Smart Laundry front end (vanilla JS). All dynamic text is inserted with textContent (XSS-safe). */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const csrfMeta = () => $('meta[name="csrf-token"]');

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }
  const fill = (el, items) => { items.flat(Infinity).forEach((n) => el.append(n)); return el; };
  const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };
  const pct = (v) => (v == null ? '–' : (v * 100).toFixed(1) + '%');
  const fmtDate = (s) => new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  const fmtTime = (s) => new Date(s).toLocaleString();

  async function api(path, { method = 'GET', json, form } = {}) {
    const headers = {};
    const opts = { method, credentials: 'same-origin', headers };
    if (method !== 'GET') headers['X-CSRF-Token'] = csrfMeta().content;
    if (json !== undefined) { headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(json); }
    if (form) opts.body = form;
    const res = await fetch(path, opts);
    let data = null;
    try { data = await res.json(); } catch (e) { /* no body */ }
    if (res.status === 401 && !location.pathname.startsWith('/login') && !path.startsWith('/api/auth/login')) {
      location.href = '/login'; throw new Error('Please log in.');
    }
    if (!res.ok) {
      let msg = data && data.detail;
      if (Array.isArray(msg)) msg = msg.map((m) => m.msg).join('; ');
      throw new Error(msg || `Request failed (${res.status})`);
    }
    return data;
  }

  function toast(msg, kind) {
    const t = h('div', { class: 'toast' + (kind === 'error' ? ' error' : '') }, msg);
    $('#toast').append(t);
    setTimeout(() => t.remove(), 4500);
  }
  const fail = (e) => toast(e.message || 'Something went wrong.', 'error');

  const PALETTE = ['#2a6fb8', '#6aaae8', '#1d4a7c', '#9cc9f5', '#4a90a4', '#7aa6c2', '#a7c4dd', '#3c6e9f', '#5b8fb9', '#c3d9ee'];
  const charts = {};
  function chart(id, type, labels, data, label) {
    const c = document.getElementById(id);
    if (!c || !window.Chart) return;
    if (charts[id]) charts[id].destroy();
    const round = type === 'doughnut';
    charts[id] = new Chart(c, {
      type,
      data: { labels, datasets: [{ label, data, backgroundColor: type === 'line' ? 'rgba(42,111,184,.15)' : PALETTE, borderColor: '#2a6fb8', fill: type === 'line', tension: 0.3 }] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: round } },
        scales: round ? {} : { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    });
  }

  const badge = (text, kind) => h('span', { class: 'badge' + (kind ? ' badge-' + kind : '') }, text);
  const confBadge = (a) => badge(pct(a.confidence), a.low_confidence ? 'warn' : 'ok');

  function td(...kids) { return h('td', {}, ...kids); }
  function emptyRow(cols, text) { return h('tr', {}, h('td', { colspan: cols, class: 'muted' }, text)); }

  /* ----------------------------------------------------------- shared result renderer */
  const LEVEL = { high: ['Very likely', 'ok'], medium: ['Probably', 'warn'], low: ['Not sure', 'danger'] };

  function renderRecommendation(box, a) {
    const r = a.recommendation;
    const scan = !!a.id;
    clear(box);
    const [word, kind] = LEVEL[r.confidence_level] || LEVEL.medium;
    box.append(h('div', { class: 'result-head' },
      h('h3', {}, r.fabric_name),
      scan ? badge(`${word} · ${pct(a.confidence)}`, kind) : badge('Care guide'),
      a.is_synthetic ? badge('Synthetic Demo Data', 'synth') : null));
    if (r.warning) {
      box.append(h('p', { class: 'alert alert-warn', role: 'alert' }, r.warning, ' ', r.conservative_advice));
    }
    const tile = (label, value) => h('div', { class: 'tile' }, h('span', { class: 'tile-label' }, label), h('span', { class: 'tile-value' }, value));
    box.append(h('div', { class: 'tiles' },
      tile('Wash', `${r.wash_mode} cycle`), tile('Temperature', r.temperature),
      tile('Dry', r.drying_method), tile('Iron', r.ironing_temperature)));
    box.append(h('p', { class: 'watch' }, h('strong', {}, 'Watch out: '), r.special_care + '.'));

    const more = h('details', { class: 'more' }, h('summary', {}, 'More details'));
    const row = (k, v) => [h('dt', {}, k), h('dd', {}, v)];
    more.append(h('dl', { class: 'kv' }, row('Washing method', r.washing_method), row('Detergent', r.detergent),
      row('Bleaching', r.bleaching), row('Fabric traits', r.properties.join(', '))));
    more.append(h('p', {}, h('strong', {}, 'Why this advice: '), r.explanation));
    if (a.probabilities && Object.keys(a.probabilities).length) {
      more.append(h('p', { class: 'muted small' }, 'Other possibilities the model considered:'));
      for (const [k, v] of Object.entries(a.probabilities).slice(0, 3)) {
        const bar = h('span'); bar.style.width = (v * 100) + '%';
        more.append(h('div', { class: 'prob-row' }, h('span', {}, k), h('div', { class: 'meter' }, bar), h('span', {}, pct(v))));
      }
    }
    box.append(more);
    if (scan) box.append(h('p', {}, h('a', { href: '/analysis/' + a.id }, 'Open full result page')));
    box.append(h('p', { class: 'muted small' }, 'Advice only. Always check the care label on the garment.'));
  }

  /* ----------------------------------------------------------- pages */
  const pages = {};

  pages.login = () => {
    $('#login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const err = $('#form-error'); err.hidden = true;
      try {
        await api('/api/auth/login', { method: 'POST', json: { email: $('#email').value, password: $('#password').value } });
        const next = new URLSearchParams(location.search).get('next') || '/dashboard';
        location.href = next.startsWith('/') && !next.startsWith('//') ? next : '/dashboard';
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    });
  };

  pages.register = () => {
    $('#register-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const err = $('#form-error'); err.hidden = true;
      if ($('#password').value !== $('#confirm').value) { err.textContent = 'Passwords do not match.'; err.hidden = false; return; }
      try {
        await api('/api/auth/register', { method: 'POST', json: { name: $('#name').value, email: $('#email').value, password: $('#password').value } });
        location.href = '/dashboard';
      } catch (ex) { err.textContent = ex.message; err.hidden = false; }
    });
  };

  pages.dashboard = async () => {
    try {
      const s = await api('/api/analytics/summary');
      $('#stat-total').textContent = s.total;
      $('#stat-most').textContent = s.most_detected || '–';
      $('#stat-conf').textContent = pct(s.avg_confidence);
      if (s.synthetic_count) $('#synthetic-note').hidden = false;
      chart('chart-dist', 'doughnut', s.distribution.labels, s.distribution.values, 'Analyses');
      chart('chart-monthly', 'line', s.monthly.labels, s.monthly.values, 'Analyses');
      const body = clear($('#recent-body'));
      if (!s.recent.length) body.append(emptyRow(5, 'No analyses yet. Use Fabric recognition to analyse your first fabric.'));
      s.recent.forEach((a) => body.append(h('tr', {},
        td(h('a', { href: '/analysis/' + a.id }, fmtDate(a.created_at))), td(a.predicted_fabric), td(confBadge(a)),
        td(a.washing_mode), td(a.washing_temperature))));
    } catch (e) { fail(e); }
  };

  pages.recognize = () => {
    const input = $('#file-input'), zone = $('#dropzone'), btn = $('#analyze-btn'), err = $('#file-error');
    let file = null;
    const OK = ['image/jpeg', 'image/png', 'image/webp'];
    function pick(f) {
      err.hidden = true;
      if (!f) return;
      if (!OK.includes(f.type)) { err.textContent = 'Unsupported file type. Use JPG, PNG or WEBP.'; err.hidden = false; return; }
      if (f.size > 5 * 1024 * 1024) { err.textContent = 'File is larger than 5 MB.'; err.hidden = false; return; }
      file = f; btn.disabled = false;
      $('#preview').src = URL.createObjectURL(f);
      $('#preview-name').textContent = `${f.name} (${(f.size / 1024).toFixed(0)} KB)`;
      $('#preview-wrap').hidden = false;
    }
    $('#browse-btn').addEventListener('click', () => input.click());
    zone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    input.addEventListener('change', () => pick(input.files[0]));
    ['dragenter', 'dragover'].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add('drag'); }));
    ['dragleave', 'drop'].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove('drag'); }));
    zone.addEventListener('drop', (e) => pick(e.dataTransfer.files[0]));
    btn.addEventListener('click', async () => {
      if (!file) return;
      btn.disabled = true; btn.textContent = 'Analysing…';
      const fd = new FormData();
      fd.append('file', file);
      fd.append('has_dryer', $('#pref-dryer').checked ? 'true' : 'false');
      fd.append('prefer_gentle', $('#pref-gentle').checked ? 'true' : 'false');
      fd.append('note', $('#note').value);
      try {
        const a = await api('/api/fabric/analyze', { method: 'POST', form: fd });
        renderRecommendation($('#result'), a);
        toast('Analysis saved.');
      } catch (ex) { fail(ex); }
      finally { btn.disabled = false; btn.textContent = 'Analyze fabric'; }
    });
  };

  pages.result = async () => {
    const id = $('#analysis-root').dataset.analysisId;
    try {
      const a = await api('/api/fabric/' + id);
      renderRecommendation($('#result'), a);
      if (a.has_image) $('#image-box').append(h('img', { src: `/api/fabric/${id}/image`, alt: 'Uploaded fabric image' }));
      else $('#image-box').append(h('p', { class: 'muted' }, 'No image stored (synthetic demo record).'));
      if (a.note) $('#note-box').textContent = 'Your note: ' + a.note;
      const sel = $('#mode-select');
      a.recommendation.wash_modes.forEach((m) => sel.append(h('option', { value: m }, m)));
      $('#mode-save').addEventListener('click', async () => {
        try { await api('/api/recommendations/select', { method: 'POST', json: { analysis_id: Number(id), mode: sel.value } }); toast('Washing choice saved.'); }
        catch (e) { fail(e); }
      });
      $('#delete-btn').addEventListener('click', async () => {
        if (!confirm('Delete this analysis and its image?')) return;
        try { await api('/api/fabric/' + id, { method: 'DELETE' }); location.href = '/history'; } catch (e) { fail(e); }
      });
    } catch (e) { clear($('#result')).append(h('p', { class: 'alert alert-danger' }, e.message)); }
  };

  pages.recommendation = async () => {
    const fsel = $('#fabric-select'), asel = $('#analysis-select');
    try {
      (await api('/api/recommendations/fabrics')).forEach((f) => fsel.append(h('option', { value: f.key }, f.name)));
      (await api('/api/history?page_size=20')).items.forEach((a) =>
        asel.append(h('option', { value: a.id }, `${fmtDate(a.created_at)} · ${a.predicted_fabric} (${pct(a.confidence)})`)));
    } catch (e) { fail(e); }
    const q = () => `has_dryer=${$('#rec-dryer').checked}&prefer_gentle=${$('#rec-gentle').checked}`;
    $('#rec-btn').addEventListener('click', async () => {
      try {
        const r = await api(`/api/recommendations/lookup?fabric=${encodeURIComponent(fsel.value)}&${q()}`);
        renderRecommendation($('#result'), { recommendation: r });
      } catch (e) { fail(e); }
    });
    asel.addEventListener('change', async () => {
      if (!asel.value) return;
      try {
        const r = await api(`/api/recommendations/analysis/${asel.value}?${q()}`);
        renderRecommendation($('#result'), { id: Number(asel.value), confidence: r.confidence, low_confidence: r.low_confidence, recommendation: r });
      } catch (e) { fail(e); }
    });
  };

  pages.history = async () => {
    let page = 1;
    const fsel = $('#filter-fabric');
    try { (await api('/api/recommendations/fabrics')).forEach((f) => fsel.append(h('option', { value: f.key }, f.name))); } catch (e) { fail(e); }
    async function load() {
      try {
        const d = await api(`/api/history?page=${page}&fabric=${encodeURIComponent(fsel.value)}`);
        $('#synthetic-note').hidden = !d.items.some((x) => x.is_synthetic);
        const body = clear($('#history-body'));
        if (!d.items.length) body.append(emptyRow(7, 'No analyses match this filter.'));
        d.items.forEach((a) => body.append(h('tr', {},
          td(fmtDate(a.created_at)), td(a.predicted_fabric), td(confBadge(a)),
          td(a.washing_mode), td(a.washing_temperature), td(a.drying_method),
          td(h('a', { href: '/analysis/' + a.id }, 'View'), ' ',
            h('button', { type: 'button', class: 'btn btn-danger', onclick: async () => {
              if (!confirm('Delete this analysis?')) return;
              try { await api('/api/fabric/' + a.id, { method: 'DELETE' }); toast('Deleted.'); load(); } catch (e) { fail(e); }
            } }, 'Delete')))));
        $('#page-info').textContent = `Page ${d.page} of ${d.pages} (${d.total} results)`;
        $('#prev-page').disabled = d.page <= 1; $('#next-page').disabled = d.page >= d.pages;
      } catch (e) { fail(e); }
    }
    fsel.addEventListener('change', () => { page = 1; load(); });
    $('#prev-page').addEventListener('click', () => { page -= 1; load(); });
    $('#next-page').addEventListener('click', () => { page += 1; load(); });
    load();
  };

  pages.analytics = async () => {
    try {
      const c = await api('/api/analytics/charts');
      $('#empty-note').hidden = c.total > 0;
      chart('c-dist', 'doughnut', c.distribution.labels, c.distribution.values, 'Analyses');
      chart('c-temp', 'bar', c.temperature.labels, c.temperature.values, 'Analyses');
      chart('c-freq', 'line', c.frequency.labels.map((d) => d.slice(5)), c.frequency.values, 'Analyses per day');
      chart('c-conf', 'bar', c.confidence.labels, c.confidence.values, 'Analyses');
      const ol = clear($('#common-list'));
      c.most_common.forEach((m, i) => ol.append(h('li', {}, `${i + 1}. ${m.fabric}: ${m.count} analyses`)));
      if (!c.most_common.length) ol.append(h('li', { class: 'muted' }, 'No data yet.'));
    } catch (e) { fail(e); }
  };

  pages.etl = () => {
    const stat = (label, value) => h('div', { class: 'card stat' }, h('span', { class: 'stat-label' }, label), h('span', { class: 'stat-value' }, value));
    function show(r) {
      if (!r.available) { $('#etl-meta').textContent = 'No ETL run yet. Choose a dataset above and run the pipeline.'; return; }
      const pl = clear($('#pipeline'));
      r.steps.forEach((s) => pl.append(h('li', { class: s.status === 'done' ? 'done' : '' }, h('strong', {}, s.name + ' – ' + s.status), h('span', { class: 'small muted' }, s.detail))));
      $('#etl-meta').textContent = `Source: ${r.source} · generated ${fmtTime(r.generated_at)} · status: ${r.status}`;
      const st = clear($('#etl-stats')), rec = r.records;
      [['Records processed', rec.total], ['Valid records', rec.valid], ['Invalid records', rec.invalid], ['Duplicates removed', rec.duplicates],
        ['Missing values (raw)', rec.missing_values_total], ['Values imputed', rec.imputed_values],
        ['Supported categories', r.supported_fabric_categories.length], ['Images scanned', r.images.scanned]].forEach(([l, v]) => st.append(stat(l, v)));
      const cd = r.class_distribution;
      chart('c-etl-dist', 'bar', Object.keys(cd), Object.values(cd), 'Valid records');
      const iss = clear($('#issues')), ic = Object.entries(r.issue_counts);
      if (!ic.length) iss.append(h('p', { class: 'muted' }, 'No issues found.'));
      else iss.append(h('ul', { class: 'plain-list' }, ic.map(([k, v]) => h('li', {}, `${k.replace(/_/g, ' ').replace(':', ': ')} – ${v}`))));
      const im = r.images, info = clear($('#image-info'));
      const rows = [['Scanned', im.scanned], ['Valid', im.valid], ['Corrupted', im.corrupted],
        ['Dimensions', im.dimensions ? `min ${im.dimensions.min}, max ${im.dimensions.max}` : '–']];
      if (im.split) rows.push(['Train / validation / test', `${im.split.train} / ${im.split.validation} / ${im.split.test}`]);
      if (im.normalisation) rows.push(['Preprocessing', `resize ${im.normalisation.target_size}, ${im.normalisation.range}`], ['Channel mean (RGB)', im.normalisation.channel_mean.join(', ')]);
      info.append(h('dl', { class: 'kv' }, rows.map(([k, v]) => [h('dt', {}, k), h('dd', {}, String(v))])));
      const ib = clear($('#invalid-body'));
      if (!r.invalid_samples.length) ib.append(emptyRow(4, 'No rejected records.'));
      r.invalid_samples.forEach((s) => ib.append(h('tr', {}, td(s.record_id), td(s.fabric_type || '(blank)'), td(s.image_filename), td(s.issues.join(', ')))));
    }
    const run = async (src) => { try { show(await api('/api/etl/run?source=' + src, { method: 'POST' })); toast('ETL run completed.'); } catch (e) { fail(e); } };
    $('#run-baseline').addEventListener('click', () => run('baseline'));
    $('#run-messy').addEventListener('click', () => run('messy'));
    api('/api/etl/report').then(show).catch(fail);
  };

  pages.ml = async () => {
    try {
      const m = await api('/api/ml/info');
      const banner = $('#ml-banner');
      if (!m.available) { banner.textContent = m.message; }
      else {
        const synth = m.dataset.source === 'synthetic';
        banner.textContent = synth
          ? 'This model was trained on generated sample textures, not real fabric photos. The scores show the pipeline works, not real-world accuracy.'
          : `Scores were measured on a held-out test set from: ${m.dataset.source}.`;
        const t = m.test, st = clear($('#ml-stats'));
        [['Accuracy', pct(t.accuracy)], ['Precision', pct(t.precision_macro)], ['Recall', pct(t.recall_macro)], ['F1-score', pct(t.f1_macro)]]
          .forEach(([l, v]) => st.append(h('div', { class: 'card stat' }, h('span', { class: 'stat-label' }, l), h('span', { class: 'stat-value' }, v))));
        const names = m.display_names || {};
        fill(clear($('#ml-model')), [
          [h('dt', {}, 'Model'), h('dd', {}, m.model_name)],
          [h('dt', {}, 'Version'), h('dd', {}, m.model_version)],
          [h('dt', {}, 'Test images'), h('dd', {}, String(m.dataset.n_test))]]);
        fill(clear($('#ml-classes')), m.classes.map((c) => h('li', { class: 'chip' }, names[c] || c)));
        const pc = clear($('#ml-per-class'));
        Object.entries(t.per_class).forEach(([c, v]) => pc.append(h('tr', {}, td(names[c] || c), td(pct(v.precision)), td(pct(v.recall)), td(pct(v.f1)))));
        const short = (l) => (names[l] || l).slice(0, 6);
        const tbl = h('table', { class: 'heat' },
          h('thead', {}, h('tr', {}, h('th', {}, ''), t.labels.map((l) => h('th', {}, short(l))))),
          h('tbody', {}, t.confusion_matrix.map((row, i) => h('tr', {}, h('th', {}, short(t.labels[i])),
            row.map((v, k) => { const c = h('td', { class: i === k ? 'diag' : '' }, v); if (v > 0) c.style.background = `rgba(42,111,184,${Math.min(0.75, 0.12 + v / 25)})`; return c; })))));
        clear($('#ml-confusion')).append(tbl);
        fill(clear($('#ml-limits')), m.limitations.map((l) => h('li', {}, l)));
      }
      const preds = (await api('/api/ml/predictions')).slice(0, 8), pb = clear($('#ml-preds'));
      $('#ml-synth').hidden = !preds.some((p) => p.is_synthetic);
      if (!preds.length) pb.append(emptyRow(3, 'No predictions yet.'));
      preds.forEach((p) => pb.append(h('tr', {}, td(fmtDate(p.created_at)), td(p.fabric), td(pct(p.confidence)))));
    } catch (e) { fail(e); }
  };

  pages.assistant = async () => {
    const log = $('#chat-log'), input = $('#chat-input');
    const say = (cls, node) => { log.append(h('div', { class: 'msg ' + cls }, node)); log.scrollTop = log.scrollHeight; };
    say('bot', 'Hello! Ask me about washing, drying or ironing a fabric.');
    async function ask(q) {
      say('user', q);
      try {
        const r = await api('/api/assistant/ask', { method: 'POST', json: { question: q } });
        const titles = [...new Set(r.sources.map((s) => s.title))].slice(0, 2);
        const src = titles.length ? 'Source: ' + titles.join(', ') : 'No matching source found';
        say('bot', [h('div', {}, r.answer), h('div', { class: 'sources' }, src)]);
      } catch (e) { say('bot', e.message); }
    }
    $('#chat-form').addEventListener('submit', (e) => { e.preventDefault(); const q = input.value.trim(); if (q) { input.value = ''; ask(q); } });
    try {
      const s = await api('/api/assistant/suggestions');
      $('#llm-status').textContent = s.llm_configured ? 'External LLM configured (rephrasing only)' : 'Fallback mode: local retrieval, no LLM configured';
      fill($('#suggestions'), s.suggestions.map((q) => h('button', { type: 'button', class: 'chip', onclick: () => ask(q) }, q)));
    } catch (e) { fail(e); }
  };

  pages.security = async () => {
    try {
      const c = await api('/api/security/controls');
      fill($('#controls'), c.controls.map((x) => h('li', {}, h('strong', {}, x.name), ' ', badge(x.status === 'implemented' ? 'Implemented' : 'Future enhancement', x.status === 'implemented' ? 'ok' : 'warn'), h('div', { class: 'muted small' }, x.detail))));
      const a = await api('/api/security/audit'), b = clear($('#audit-body'));
      if (!a.length) b.append(emptyRow(5, 'No events yet.'));
      a.forEach((r) => b.append(h('tr', {}, td(fmtTime(r.timestamp)), td(r.action), td(badge(r.status, r.status === 'success' ? 'ok' : 'danger')), td(r.ip_address || '–'), td(r.detail || ''))));
    } catch (e) { fail(e); }
  };

  pages.settings = async () => {
    try {
      const s = await api('/api/settings');
      $('#s-name').value = s.name; $('#s-email').value = s.email; $('#s-theme').value = s.theme; $('#s-notify').checked = s.notifications_enabled;
      fill($('#features'), s.features.map((f) => h('li', {}, f.name, ' ', badge(f.status === 'implemented' ? 'Implemented' : 'Future enhancement', f.status === 'implemented' ? 'ok' : 'warn'))));
    } catch (e) { fail(e); }
    $('#profile-form').addEventListener('submit', async (e) => { e.preventDefault(); try { await api('/api/settings/profile', { method: 'PUT', json: { name: $('#s-name').value } }); toast('Profile saved.'); } catch (x) { fail(x); } });
    $('#password-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      try { await api('/api/settings/password', { method: 'POST', json: { current_password: $('#s-cur').value, new_password: $('#s-new').value } }); toast('Password changed.'); e.target.reset(); } catch (x) { fail(x); }
    });
    $('#pref-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      try { const r = await api('/api/settings/preferences', { method: 'PUT', json: { theme: $('#s-theme').value, notifications_enabled: $('#s-notify').checked } }); document.documentElement.dataset.theme = r.theme; toast('Preferences saved.'); } catch (x) { fail(x); }
    });
    $('#delete-data').addEventListener('click', async () => {
      if (!confirm('Delete ALL your analyses and uploaded images? This cannot be undone.')) return;
      try { const r = await api('/api/settings/data', { method: 'DELETE' }); toast(`Deleted ${r.deleted} analyses.`); } catch (x) { fail(x); }
    });
    $('#logout-btn-2').addEventListener('click', logout);
  };

  async function logout() { try { await api('/api/auth/logout', { method: 'POST' }); } finally { location.href = '/'; } }

  document.addEventListener('DOMContentLoaded', () => {
    const lb = $('#logout-btn'); if (lb) lb.addEventListener('click', logout);
    const init = pages[document.body.dataset.page];
    if (init) init();
  });
})();
