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
    const [catalog, review] = await Promise.all([craftGuidanceCatalog(), craftGuidanceReview(projectId, stage, options.force)]);
    if (host.dataset.craftRequest !== requestId) return;
    const traditions = craftGuidanceTraditions(catalog, review, stage);
    const findings = review.findings || [];
    const openFindings = findings.filter(item => !item.resolved);
    const intent = review.compass?.intent?.trim();
    const label = options.label || craftGuidanceLabels[stage] || 'Craft guidance';
    host.innerHTML = `<header class="craft-guidance-head">
      <div><span>CRAFT COMPASS · ${safe(label.toUpperCase())}</span><h3>${intent ? safe(intent) : 'Set the creative intent for this production'}</h3></div>
      <div class="craft-guidance-actions"><em class="${openFindings.length ? 'open' : 'aligned'}">${openFindings.length ? `${openFindings.length} open` : 'Aligned'}</em><button type="button" data-open-craft-compass>${intent ? 'Edit compass' : 'Set compass'}</button></div>
    </header>
    ${traditions.length ? `<div class="craft-guidance-lenses">${traditions.map(item => `<span title="${safe(item.context)}">${safe(item.name)}</span>`).join('')}</div>` : '<p class="craft-guidance-empty">Choose traditions for the questions they help the crew ask—not as a recipe or a purity test.</p>'}
    ${findings.length ? `<div class="craft-guidance-findings">${findings.map(craftFindingMarkup).join('')}</div>` : '<p class="craft-guidance-clear">No open craft tension was found for this desk. Keep making specific, intentional choices.</p>'}
    <footer>Advisory creative guidance · separate from originality, rights, consent, and release compliance</footer>`;
    host.querySelector('[data-open-craft-compass]').onclick = () => openCraftCompass(projectId);
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
  } catch (error) {
    if (host.dataset.craftRequest === requestId) host.innerHTML = `<div class="craft-guidance-error"><b>Craft guidance is unavailable</b><span>${safe(error.message)}</span></div>`;
  }
}
