let craftGuidanceCatalogPromise = null;
const craftGuidanceReviewCache = new Map();

const craftGuidanceDepartments = {
  story: ['story', 'performance'],
  characters: ['performance', 'visual', 'motion'],
  worlds: ['world', 'visual'],
  shots: ['motion', 'visual', 'performance'],
  edit: ['edit', 'motion'],
  sound: ['audio', 'performance'],
};

const craftGuidanceLabels = {
  story: 'Story craft',
  characters: 'Character & performance',
  worlds: 'World craft',
  shots: 'Visual storytelling',
  edit: 'Editorial rhythm',
  sound: 'Sound & performance',
};

function craftGuidanceCatalog() {
  if (!craftGuidanceCatalogPromise) craftGuidanceCatalogPromise = api('/api/anime-craft/catalog');
  return craftGuidanceCatalogPromise;
}

function sourceNoteLink(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : '';
  } catch (_) {
    return '';
  }
}

function sourceNotesMarkup(data) {
  const notes = data.notes || [];
  const types = new Map((data.types || []).map(item => [item.id, item]));
  const cards = notes.map(note => {
    const type = types.get(note.source_type) || {label: note.source_type};
    const link = sourceNoteLink(note.source_url);
    return `<article class="source-note-card"><header><span>${safe(type.label)}</span><button type="button" data-edit-source-note="${note.id}">Edit</button></header><b>${safe(note.title)}</b><p>${safe(note.note)}</p><small><strong>How it became Kizuna work</strong>${safe(note.application)}</small>${link ? `<a href="${safe(link)}" target="_blank" rel="noopener noreferrer">Open source</a>` : ''}${(note.evidence_refs || []).length ? `<em>${note.evidence_refs.map(safe).join(' · ')}</em>` : ''}</article>`;
  }).join('');
  const options = (data.types || []).map(item => `<option value="${safe(item.id)}">${safe(item.label)}</option>`).join('');
  return `<details class="craft-source-notes"><summary><span>Sources &amp; invention</span><b>${notes.length} note${notes.length === 1 ? '' : 's'}</b><i aria-hidden="true">+</i></summary><div class="craft-source-body"><p>Record what informed the work and how the crew transformed it into an original production choice.</p><div class="source-note-list">${cards || '<div class="source-note-empty">No source notes on this desk yet.</div>'}</div><button type="button" data-add-source-note>Add source note</button><div class="source-note-editor" data-source-note-editor hidden><input type="hidden" data-source-note-id><label>What kind of source?<select data-source-note-type>${options}</select><small data-source-note-description></small></label><label>Source, experience, or invented idea<input data-source-note-title maxlength="160" placeholder="Interview, archive, field observation, or original idea"></label><label>What did it contribute?<textarea data-source-note-copy rows="2" maxlength="4000" placeholder="The useful fact, observation, question, or craft principle"></textarea></label><label>How did you transform it?<textarea data-source-note-application rows="2" maxlength="4000" placeholder="Describe the new story, design, staging, edit, or sound choice Kizuna made from it"></textarea></label><div class="source-note-fields"><label>Link, if available<input data-source-note-url type="url" maxlength="2000" placeholder="https://..."></label><label>Research log or evidence IDs<input data-source-note-evidence placeholder="research-log:12, interview:4"></label></div><small class="source-note-notice">${safe(data.notice || '')}</small><div class="source-note-actions"><button type="button" data-cancel-source-note>Cancel</button><button type="button" class="primary" data-save-source-note>Save source note</button></div></div></div></details>`;
}

function openCraftCompass(projectId) {
  return openStyleLab(projectId).then(() => {
    if (typeof setStyleV2Step === 'function') setStyleV2Step('craft');
  });
}

async function craftGuidanceReview(projectId, stage, force = false) {
  const key = `${projectId}:${stage}`;
  const saved = craftGuidanceReviewCache.get(key);
  if (!force && saved && Date.now() - saved.savedAt < 15000) return saved.value;
  if (saved?.promise) return saved.promise;
  const promise = api(`/api/projects/${projectId}/craft-review`, {
    method: 'POST',
    body: JSON.stringify({stage}),
  });
  craftGuidanceReviewCache.set(key, {savedAt: 0, value: null, promise});
  try {
    const value = await promise;
    craftGuidanceReviewCache.set(key, {savedAt: Date.now(), value, promise: null});
    return value;
  } catch (error) {
    craftGuidanceReviewCache.delete(key);
    throw error;
  }
}

function craftGuidanceTraditions(catalog, review, stage) {
  const selected = new Set(review.compass?.tradition_ids || []);
  const departments = new Set(craftGuidanceDepartments[stage] || []);
  const all = (catalog.traditions || []).filter(item => selected.has(item.id));
  const relevant = all.filter(item => item.department === 'cross-craft' || departments.has(item.department));
  return relevant.length ? relevant : all.slice(0, 3);
}

function craftFindingMarkup(item) {
  const decision = item.decision;
  return `<details class="craft-guidance-finding ${safe(item.level || 'notice')}">
    <summary><span>${decision ? 'DECIDED' : 'CONVERSATION'}</span><b>${safe(item.title)}</b><i aria-hidden="true">+</i></summary>
    <div class="craft-guidance-finding-body">
      <p>${safe(item.why)}</p>
      ${(item.evidence || []).length ? `<div class="craft-guidance-evidence"><b>What Kizuna found</b>${item.evidence.map(line => `<span>${safe(line)}</span>`).join('')}</div>` : ''}
      ${!decision && item.choices?.realign ? `<p class="craft-guidance-suggestion"><b>One way to realign:</b> ${safe(item.choices.realign)}</p>` : ''}
      ${decision ? `<small>Current choice: ${safe(decision.decision)} · ${safe(decision.rationale)}</small>` : `<div class="craft-guidance-choices">
        <button type="button" data-craft-choice="continue" data-craft-finding="${safe(item.id)}">Continue intentionally</button>
        <button type="button" data-craft-choice="realign" data-craft-finding="${safe(item.id)}">Plan to realign</button>
        <button type="button" data-craft-choice="revise_compass" data-craft-finding="${safe(item.id)}">Revise compass</button>
      </div><div class="craft-guidance-rationale" data-craft-rationale="${safe(item.id)}" hidden>
        <label>Why is this the right creative choice?<textarea rows="2" required placeholder="Record the reasoning so the whole production team understands the decision."></textarea></label>
        <div><button type="button" data-craft-cancel>Cancel</button><button type="button" class="primary" data-craft-save>Save decision</button></div>
      </div>`}
    </div>
  </details>`;
}

async function renderCraftGuidance(host, projectId, stage, options = {}) {
  if (typeof host === 'string') host = document.querySelector(host);
  if (!host || !projectId) return;
  const requestId = `${projectId}:${stage}:${Date.now()}`;
  host.dataset.craftRequest = requestId;
  host.classList.add('craft-guidance');
  host.innerHTML = '<div class="craft-guidance-loading">Reading the production Craft Compass…</div>';
  try {
    const [catalog, review, sourceNotes] = await Promise.all([craftGuidanceCatalog(), craftGuidanceReview(projectId, stage, options.force), api(`/api/projects/${projectId}/source-notes?stage=${encodeURIComponent(stage)}`)]);
    if (host.dataset.craftRequest !== requestId) return;
    const traditions = craftGuidanceTraditions(catalog, review, stage);
    const findings = review.findings || [];
    const openFindings = findings.filter(item => !item.resolved);
    const intent = review.compass?.intent?.trim();
    const label = options.label || craftGuidanceLabels[stage] || 'Craft guidance';
    host.innerHTML = `<header class="craft-guidance-head">
      <div><span>CRAFT COMPASS · ${safe(label.toUpperCase())}</span><h3>${intent ? safe(intent) : 'Set the creative intent for this production'}</h3></div>
      <div class="craft-guidance-actions"><small>Catalog ${safe(review.catalog?.pinned_version||review.catalog?.current_version||'not set')}</small><em class="${openFindings.length ? 'open' : 'aligned'}">${openFindings.length ? `${openFindings.length} open` : 'Aligned'}</em><button type="button" class="craft-guidance-toggle" data-craft-guidance-toggle>Open guidance</button><button type="button" data-open-craft-compass>${intent ? 'Edit compass' : 'Set compass'}</button></div>
    </header>
    ${traditions.length ? `<div class="craft-guidance-lenses">${traditions.map(item => `<span title="${safe(item.context)}">${item.japanese ? `<b lang="ja">${safe(item.japanese)}</b> ` : ''}${safe(item.reading || item.name)}</span>`).join('')}</div>` : '<p class="craft-guidance-empty">Choose traditions for the questions they help the crew ask—not as a recipe or a purity test.</p>'}
    ${findings.length ? `<div class="craft-guidance-findings">${findings.map(craftFindingMarkup).join('')}</div>` : '<p class="craft-guidance-clear">No open craft tension was found for this desk. Keep making specific, intentional choices.</p>'}
    ${sourceNotesMarkup(sourceNotes)}
    <footer>Advisory creative guidance · separate from originality, rights, consent, and release compliance</footer>`;
    host.querySelector('[data-open-craft-compass]').onclick = () => openCraftCompass(projectId);
    host.querySelector('[data-craft-guidance-toggle]').onclick = event => {
      const open = host.classList.toggle('expanded');
      event.currentTarget.textContent = open ? 'Hide guidance' : 'Open guidance';
    };
    host.querySelectorAll('[data-craft-choice]').forEach(button => button.onclick = () => {
      const form = host.querySelector(`[data-craft-rationale="${CSS.escape(button.dataset.craftFinding)}"]`);
      if (!form) return;
      form.hidden = false;
      form.dataset.decision = button.dataset.craftChoice;
      form.querySelector('textarea').focus();
    });
    host.querySelectorAll('[data-craft-cancel]').forEach(button => button.onclick = () => { button.closest('[data-craft-rationale]').hidden = true; });
    host.querySelectorAll('[data-craft-rationale]').forEach(panel => panel.querySelector('[data-craft-save]').onclick = async () => {
      const rationale = panel.querySelector('textarea').value.trim();
      if (!rationale) return;
      const saveButton = panel.querySelector('[data-craft-save]');
      saveButton.disabled = true;
      saveButton.textContent = 'Saving…';
      try {
        await api(`/api/projects/${projectId}/craft-decisions`, {method: 'POST', body: JSON.stringify({finding_id: panel.dataset.craftRationale, decision: panel.dataset.decision, rationale})});
        craftGuidanceReviewCache.delete(`${projectId}:${stage}`);
        await renderCraftGuidance(host, projectId, stage, {label, force: true});
        if (typeof loadProjects === 'function') await loadProjects();
      } catch (error) {
        saveButton.disabled = false;
        saveButton.textContent = 'Save decision';
        panel.insertAdjacentHTML('beforeend', `<div class="job-error">${safe(error.message)}</div>`);
      }
    });
    const sourceEditor = host.querySelector('[data-source-note-editor]');
    const typeSelect = host.querySelector('[data-source-note-type]');
    const sourceTypeMap = new Map((sourceNotes.types || []).map(item => [item.id, item]));
    const describeSourceType = () => { host.querySelector('[data-source-note-description]').textContent = sourceTypeMap.get(typeSelect.value)?.description || ''; };
    const openSourceEditor = note => {
      sourceEditor.hidden = false;
      sourceEditor.querySelector('[data-source-note-id]').value = note?.id || '';
      typeSelect.value = note?.source_type || 'research';
      sourceEditor.querySelector('[data-source-note-title]').value = note?.title || '';
      sourceEditor.querySelector('[data-source-note-copy]').value = note?.note || '';
      sourceEditor.querySelector('[data-source-note-application]').value = note?.application || '';
      sourceEditor.querySelector('[data-source-note-url]').value = note?.source_url || '';
      sourceEditor.querySelector('[data-source-note-evidence]').value = (note?.evidence_refs || []).join(', ');
      describeSourceType();
      sourceEditor.querySelector('[data-source-note-title]').focus();
    };
    typeSelect.onchange = describeSourceType;
    host.querySelector('[data-add-source-note]').onclick = () => openSourceEditor(null);
    host.querySelectorAll('[data-edit-source-note]').forEach(button => button.onclick = () => openSourceEditor((sourceNotes.notes || []).find(note => note.id === Number(button.dataset.editSourceNote))));
    host.querySelector('[data-cancel-source-note]').onclick = () => { sourceEditor.hidden = true; };
    host.querySelector('[data-save-source-note]').onclick = async () => {
      const saveButton = host.querySelector('[data-save-source-note]');
      const noteId = Number(sourceEditor.querySelector('[data-source-note-id]').value) || null;
      const payload = {stage, source_type: typeSelect.value, title: sourceEditor.querySelector('[data-source-note-title]').value.trim(), note: sourceEditor.querySelector('[data-source-note-copy]').value.trim(), application: sourceEditor.querySelector('[data-source-note-application]').value.trim(), source_url: sourceEditor.querySelector('[data-source-note-url]').value.trim(), evidence_refs: sourceEditor.querySelector('[data-source-note-evidence]').value.split(',').map(item => item.trim()).filter(Boolean)};
      if (!payload.title || !payload.note || !payload.application) return;
      saveButton.disabled = true;
      saveButton.textContent = 'Saving…';
      try {
        await api(noteId ? `/api/projects/${projectId}/source-notes/${noteId}` : `/api/projects/${projectId}/source-notes`, {method: noteId ? 'PUT' : 'POST', body: JSON.stringify(payload)});
        await renderCraftGuidance(host, projectId, stage, {label, force: true});
      } catch (error) {
        saveButton.disabled = false;
        saveButton.textContent = 'Save source note';
        sourceEditor.insertAdjacentHTML('beforeend', `<div class="job-error">${safe(error.message)}</div>`);
      }
    };
  } catch (error) {
    if (host.dataset.craftRequest === requestId) host.innerHTML = `<div class="craft-guidance-error"><b>Craft guidance is unavailable</b><span>${safe(error.message)}</span></div>`;
  }
}
