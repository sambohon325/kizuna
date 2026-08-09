const projectsEl = document.querySelector('#projects');
const projectDialog = document.querySelector('#project-dialog');
const detailDialog = document.querySelector('#detail-dialog');
const styleDialog = document.querySelector('#style-dialog');
const writerDialog = document.querySelector('#writer-dialog');
const characterDialog = document.querySelector('#character-dialog');
const renderDialog = document.querySelector('#render-dialog');
let projects = [];
let catalog = null;
let activeCharacterId = null;
let generationProviders = [];

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function safe(value = '') {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

async function loadProjects() {
  projects = await api('/api/projects');
  document.querySelector('#project-count').textContent = `${projects.length} production${projects.length === 1 ? '' : 's'}`;
  projectsEl.innerHTML = projects.length ? projects.map(project => `
    <article class="project" data-id="${project.id}"><span class="tag">${safe(project.status)}</span><h3>${safe(project.title)}</h3><p>${safe(project.logline || 'Your story is waiting for its first scene.')}</p><footer><span class="era">${safe(project.style_profile?.era_primary || 'Style open')}</span><span>${project.scenes.length} scenes</span></footer></article>`).join('') : '<div class="empty">No productions yet. Start with a title and logline—everything else can evolve.</div>';
  document.querySelectorAll('.project').forEach(el => el.onclick = () => openProject(el.dataset.id));
}

async function openProject(id) {
  const project = await api(`/api/projects/${id}`);
  const style = project.style_profile;
  document.querySelector('#detail').innerHTML = `
    <div class="detail-head"><div><p class="eyebrow" style="color:#e84b38">${safe(project.status.toUpperCase())}</p><h2>${safe(project.title)}</h2><p>${safe(project.logline)}</p><button class="style-launch" data-style-id="${project.id}">Edit Creative DNA</button><button class="writer-launch" data-writer-id="${project.id}">Develop Story</button></div><button class="close" data-close-detail>×</button></div>
    <div class="style-grid"><div class="style-card"><b>ERA BLEND</b>${safe(style.era_primary)} × ${safe(style.era_secondary)}</div><div class="style-card"><b>VISUAL DNA</b>${safe(Object.values(style.visual).join(' · '))}</div><div class="style-card"><b>STORY DNA</b>${safe(Object.values(style.narrative).join(' · '))}</div></div>
    <h3>Scenes</h3>${project.scenes.length ? project.scenes.map(scene => `<div class="scene"><strong>${scene.position}. ${safe(scene.title)}</strong><br><small>${safe(scene.summary)} · ${scene.shots.length} shots</small></div>`).join('') : '<div class="empty">Scene planning will appear here.</div>'}`;
  detailDialog.showModal();
  document.querySelector('[data-close-detail]').onclick = () => detailDialog.close();
  document.querySelector('[data-style-id]').onclick = event => { detailDialog.close(); openStyleLab(Number(event.currentTarget.dataset.styleId)); };
  document.querySelector('[data-writer-id]').onclick = event => { detailDialog.close(); openWriterRoom(Number(event.currentTarget.dataset.writerId)); };
}

function options(items, selected) {
  return items.map(item => { const value = typeof item === 'string' ? item : item.id; const label = typeof item === 'string' ? item : item.label; return `<option value="${safe(value)}" ${value === selected ? 'selected' : ''}>${safe(label)}</option>`; }).join('');
}

function traitSection(title, group, values, description) {
  return `<section class="trait-section"><h3>${title}</h3><p>${description}</p><div class="trait-grid">${Object.entries(group).map(([key, choices]) => `<label>${key.replaceAll('_',' ')}<select name="${values === 'visual' ? 'visual' : values}.${key}">${options(choices, '')}</select></label>`).join('')}</div></section>`;
}

async function openStyleLab(projectId) {
  if (!projects.length) await loadProjects();
  if (!catalog) catalog = await api('/api/style-catalog');
  if (!projects.length) { projectDialog.showModal(); return; }
  const projectSelect = document.querySelector('#style-project');
  projectSelect.innerHTML = options(projects.map(p => ({id:String(p.id), label:p.title})), String(projectId || projects[0].id));
  document.querySelector('[name="era_primary"]').innerHTML = options(catalog.eras, '1990s');
  document.querySelector('[name="era_secondary"]').innerHTML = options(catalog.eras, '2020s');
  document.querySelector('#style-fields').innerHTML = traitSection('Visual language', catalog.visual, 'visual', 'Define the marks, color, light, and worlds seen on screen.') + traitSection('Direction', catalog.direction, 'direction', 'Set camera behavior, animation economy, and editorial rhythm.') + traitSection('Storytelling', catalog.narrative, 'narrative', 'Choose structural and emotional rules for the production.');
  document.querySelector('#archetypes').innerHTML = catalog.archetypes.map(value => `<label class="chip"><input type="checkbox" name="archetypes" value="${safe(value)}"><span>${safe(value)}</span></label>`).join('');
  projectSelect.onchange = () => fillStyle(Number(projectSelect.value));
  document.querySelector('#style-form').onchange = updateSummary;
  fillStyle(Number(projectSelect.value));
  styleDialog.showModal();
}

function fillStyle(projectId) {
  const style = projects.find(p => p.id === projectId)?.style_profile;
  if (!style) return;
  const primarySelect = document.querySelector('[name="era_primary"]');
  const secondarySelect = document.querySelector('[name="era_secondary"]');
  primarySelect.value = [...primarySelect.options].some(o => o.value === style.era_primary) ? style.era_primary : '1990s';
  secondarySelect.value = [...secondarySelect.options].some(o => o.value === style.era_secondary) ? style.era_secondary : '2020s';
  ['visual','direction','narrative'].forEach(group => Object.entries(style[group] || {}).forEach(([key,value]) => { const input = document.querySelector(`[name="${group}.${key}"]`); if (input && [...input.options].some(o => o.value === value)) input.value = value; }));
  document.querySelectorAll('[name="archetypes"]').forEach(input => input.checked = style.archetypes.includes(input.value));
  updateSummary();
}

function updateSummary() {
  const form = document.querySelector('#style-form');
  const primary = form.elements.era_primary.value;
  const secondary = form.elements.era_secondary.value;
  const camera = form.elements['direction.camera']?.value;
  const structure = form.elements['narrative.structure']?.value;
  document.querySelector('#dna-summary').textContent = `${primary} visual foundations blended with ${secondary} finishing, ${camera} direction, and a ${structure} story rhythm.`;
}

function collectStyle(form) {
  const payload = {era_primary:form.elements.era_primary.value, era_secondary:form.elements.era_secondary.value, visual:{}, direction:{}, narrative:{}, archetypes:[]};
  new FormData(form).forEach((value, key) => { if (key === 'archetypes') payload.archetypes.push(value); else if (key.includes('.')) { const [group, trait] = key.split('.'); payload[group][trait] = value; } });
  return payload;
}

async function openWriterRoom(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  const projectSelect = document.querySelector('#writer-project');
  projectSelect.innerHTML = options(projects.map(p => ({id:String(p.id), label:p.title})), String(projectId || projects[0].id));
  projectSelect.onchange = () => fillStory(Number(projectSelect.value));
  fillStory(Number(projectSelect.value));
  writerDialog.showModal();
}

function fillStory(projectId) {
  const brief = projects.find(project => project.id === projectId)?.story_brief;
  const form = document.querySelector('#writer-form');
  form.elements.premise.value = brief?.premise || '';
  form.elements.format.value = brief?.format || 'short film';
  form.elements.target_duration_minutes.value = brief?.target_duration_minutes || 5;
  form.elements.genre.value = brief?.genre || 'science fantasy';
  form.elements.audience.value = brief?.audience || 'general';
  form.elements.themes.value = (brief?.themes || []).join(', ');
  renderStory(brief);
}

function renderStory(brief) {
  const result = document.querySelector('#story-result');
  if (!brief?.synopsis) { result.innerHTML = ''; return; }
  result.innerHTML = `<div class="synopsis"><b>WORKING SYNOPSIS</b><div data-synopsis>${safe(brief.synopsis)}</div></div><div class="beats">${brief.beats.map(beat => `<div class="beat" data-position="${safe(beat.position)}" data-name="${safe(beat.name)}"><b>${safe(beat.position)} · ${safe(beat.name)}</b><textarea aria-label="${safe(beat.name)} summary">${safe(beat.summary)}</textarea></div>`).join('')}</div><div class="outline-actions"><button type="button" id="save-outline">Save outline edits</button></div>`;
  document.querySelector('#save-outline').onclick = saveOutline;
}

async function saveOutline() {
  const projectId = Number(document.querySelector('#writer-project').value);
  const beats = [...document.querySelectorAll('.beat')].map(beat => ({position:beat.dataset.position, name:beat.dataset.name, summary:beat.querySelector('textarea').value}));
  const synopsis = document.querySelector('[data-synopsis]').textContent;
  const brief = await api(`/api/projects/${projectId}/story/outline`, {method:'PATCH', body:JSON.stringify({synopsis, beats})});
  await loadProjects();
  renderStory(brief);
}

async function openCharacterStudio(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  if (!generationProviders.length) generationProviders = (await api('/api/generation/providers')).providers;
  const projectSelect = document.querySelector('#character-project');
  projectSelect.innerHTML = options(projects.map(p => ({id:String(p.id), label:p.title})), String(projectId || projects[0].id));
  projectSelect.onchange = () => { activeCharacterId = null; clearCharacterForm(); renderCharacterRoster(Number(projectSelect.value)); };
  renderCharacterRoster(Number(projectSelect.value));
  document.querySelector('#character-result').innerHTML = '';
  characterDialog.showModal();
}

function renderCharacterRoster(projectId) {
  const roster = projects.find(project => project.id === projectId)?.characters || [];
  document.querySelector('#character-roster').innerHTML = `<button type="button" class="character-pill ${activeCharacterId === null ? 'active' : ''}" data-new-character>＋ New</button>${roster.map(character => `<button type="button" class="character-pill ${activeCharacterId === character.id ? 'active' : ''}" data-character-id="${character.id}"><b>${safe(character.name)}</b> · ${safe(character.role)}${character.design ? ` · sheet v${character.design.version}` : ''}</button>`).join('')}`;
  document.querySelector('[data-new-character]').onclick = () => { activeCharacterId = null; clearCharacterForm(); renderCharacterRoster(projectId); };
  document.querySelectorAll('[data-character-id]').forEach(button => button.onclick = () => selectCharacter(projectId, Number(button.dataset.characterId)));
}

function clearCharacterForm() {
  const form = document.querySelector('#character-form');
  ['name','want','need','contradiction','silhouette','body_language','face','hair','eyes','signature_detail','palette','wardrobe','anchors'].forEach(name => form.elements[name].value = '');
  form.elements.role.value = 'protagonist';
  document.querySelector('#character-result').innerHTML = '';
}

function selectCharacter(projectId, characterId) {
  const character = projects.find(project => project.id === projectId)?.characters.find(item => item.id === characterId);
  if (!character) return;
  activeCharacterId = characterId;
  const form = document.querySelector('#character-form');
  ['name','role','want','need','contradiction'].forEach(name => form.elements[name].value = character[name] || '');
  const appearance = character.design?.appearance || {};
  ['silhouette','body_language','face','hair','eyes','signature_detail'].forEach(name => form.elements[name].value = appearance[name] || '');
  form.elements.palette.value = (character.design?.palette || []).join(', ');
  form.elements.wardrobe.value = (character.design?.wardrobe || []).join(', ');
  form.elements.anchors.value = (character.design?.consistency_anchors || []).join(', ');
  renderCharacterRoster(projectId);
  if (character.design) renderCharacterDesign(character, character.design); else document.querySelector('#character-result').innerHTML = '';
}

function listValue(form, name) {
  return form.elements[name].value.split(',').map(value => value.trim()).filter(Boolean);
}

function collectCharacter(form) {
  return {name:form.elements.name.value, role:form.elements.role.value, want:form.elements.want.value, need:form.elements.need.value, contradiction:form.elements.contradiction.value};
}

function collectCharacterDesign(form) {
  return {appearance:{silhouette:form.elements.silhouette.value, body_language:form.elements.body_language.value, face:form.elements.face.value, hair:form.elements.hair.value, eyes:form.elements.eyes.value, signature_detail:form.elements.signature_detail.value}, palette:listValue(form,'palette'), wardrobe:listValue(form,'wardrobe'), consistency_anchors:listValue(form,'anchors')};
}

function renderCharacterDesign(character, design) {
  const providerOptions = generationProviders.map(provider => `<option value="${safe(provider.id)}" ${provider.id === 'mock' ? 'selected' : ''}>${safe(provider.label)}${provider.ready ? '' : ' · setup required'}</option>`).join('');
  document.querySelector('#character-result').innerHTML = `<div class="reference-brief"><b>GENERATION-READY REFERENCE BRIEF · V${design.version}</b>${safe(design.reference_brief)}</div><div class="anchor-list">${design.consistency_anchors.map(anchor => `<span>LOCK · ${safe(anchor)}</span>`).join('')}</div><div class="generation-actions"><select id="generation-provider" aria-label="Generation provider">${providerOptions}</select><button type="button" id="generate-character">Generate reference sheet</button></div><div id="generation-result"></div>`;
  document.querySelector('#generate-character').onclick = generateCharacterReference;
}

async function generateCharacterReference() {
  if (!activeCharacterId) return;
  const button = document.querySelector('#generate-character');
  button.disabled = true;
  button.textContent = 'Queuing generation…';
  try {
    const provider = document.querySelector('#generation-provider').value;
    const job = await api(`/api/characters/${activeCharacterId}/generate`, {method:'POST', body:JSON.stringify({provider})});
    renderGenerationJob(job);
  } catch (error) {
    document.querySelector('#generation-result').innerHTML = `<div class="job-error">${safe(error.message)}</div>`;
  } finally {
    button.disabled = false;
    button.textContent = 'Generate reference sheet';
  }
}

function renderGenerationJob(job) {
  const result = document.querySelector('#generation-result');
  if (job.status === 'failed') { result.innerHTML = `<div class="job-error">${safe(job.error)}</div>`; return; }
  if (job.assets.length) { const asset = job.assets[0]; result.innerHTML = `<div class="asset-preview"><img src="${safe(asset.uri)}" alt="Generated character reference for the selected character"></div><div class="generation-actions"><small>${safe(job.provider)} · asset v${asset.version} · job ${job.id}</small></div>`; return; }
  result.innerHTML = `<div class="generation-actions"><small>${safe(job.provider)} job ${job.external_id || job.id} is ${safe(job.status)}.</small>${job.provider === 'comfyui' ? `<button type="button" data-sync-job="${job.id}">Check result</button>` : ''}</div>`;
  const sync = document.querySelector('[data-sync-job]');
  if (sync) sync.onclick = async () => renderGenerationJob(await api(`/api/generation-jobs/${job.id}/sync`, {method:'POST'}));
}

async function openRenderFarm() {
  renderDialog.showModal();
  await refreshRenderFarm();
}

async function refreshRenderFarm() {
  const farm = await api('/api/render-farm/status');
  const queued = farm.jobs.filter(job => job.status === 'queued').length;
  const running = farm.jobs.filter(job => job.status === 'running').length;
  const online = farm.workers.filter(worker => ['online','busy'].includes(worker.status)).length;
  document.querySelector('#farm-summary').innerHTML = `<div class="farm-stat"><b>${online}</b><span>WORKERS ONLINE</span></div><div class="farm-stat"><b>${running}</b><span>JOBS RENDERING</span></div><div class="farm-stat"><b>${queued}</b><span>JOBS QUEUED</span></div>`;
  document.querySelector('#farm-workers').innerHTML = farm.workers.length ? farm.workers.map(worker => { const gpu = worker.capabilities.gpu || worker.capabilities.gpus?.map(item => item.name).join(', ') || 'CPU worker'; const vram = worker.capabilities.vram_gb ? `${worker.capabilities.vram_gb} GB VRAM` : ''; return `<article class="worker-card"><header><div><b>${safe(worker.name)}</b><br><small>${safe(worker.hostname)}</small></div><span class="worker-status ${safe(worker.status)}">${safe(worker.status)}</span></header><p>${safe(gpu)} ${safe(vram)}</p><small>${worker.supported_tasks.map(safe).join(' · ')}</small></article>`; }).join('') : '<div class="empty">No render workers enrolled yet.</div>';
  document.querySelector('#farm-jobs').innerHTML = farm.jobs.length ? farm.jobs.map(job => `<div class="farm-job"><b>#${job.id}</b><span>Character ${job.character_id}</span><span>${safe(job.status)}</span><span>${job.assets} assets</span></div>`).join('') : '<div class="empty">No farm jobs yet. Choose Render farm in Character Studio to queue one.</div>';
}

function collectStory(form) {
  return {premise:form.elements.premise.value, format:form.elements.format.value, target_duration_minutes:Number(form.elements.target_duration_minutes.value), genre:form.elements.genre.value, audience:form.elements.audience.value, themes:form.elements.themes.value.split(',').map(value => value.trim()).filter(Boolean)};
}

document.querySelector('#new-project').onclick = () => projectDialog.showModal();
document.querySelector('#style-lab-nav').onclick = () => openStyleLab();
document.querySelector('#writer-nav').onclick = () => openWriterRoom();
document.querySelector('#characters-nav').onclick = () => openCharacterStudio();
document.querySelector('#render-nav').onclick = () => openRenderFarm();
document.querySelector('.close').onclick = () => projectDialog.close();
document.querySelector('#style-close').onclick = () => styleDialog.close();
document.querySelector('#writer-close').onclick = () => writerDialog.close();
document.querySelector('#character-close').onclick = () => characterDialog.close();
document.querySelector('#render-close').onclick = () => renderDialog.close();
document.querySelector('#refresh-farm').onclick = () => refreshRenderFarm();
document.querySelector('#project-form').onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); await api('/api/projects', {method:'POST', body:JSON.stringify(data)}); event.target.reset(); projectDialog.close(); await loadProjects(); };
document.querySelector('#style-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#style-project').value); await api(`/api/projects/${projectId}/style`, {method:'PUT', body:JSON.stringify(collectStyle(event.target))}); styleDialog.close(); await loadProjects(); openProject(projectId); };
document.querySelector('#writer-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#writer-project').value); const brief = await api(`/api/projects/${projectId}/story`, {method:'PUT', body:JSON.stringify(collectStory(event.target))}); await loadProjects(); renderStory(brief); };
document.querySelector('#character-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#character-project').value); const character = activeCharacterId ? await api(`/api/characters/${activeCharacterId}`, {method:'PUT', body:JSON.stringify(collectCharacter(event.target))}) : await api(`/api/projects/${projectId}/characters`, {method:'POST', body:JSON.stringify(collectCharacter(event.target))}); activeCharacterId = character.id; const design = await api(`/api/characters/${character.id}/design`, {method:'PUT', body:JSON.stringify(collectCharacterDesign(event.target))}); await loadProjects(); renderCharacterRoster(projectId); renderCharacterDesign(character, design); };
loadProjects().catch(error => projectsEl.innerHTML = `<div class="empty">Could not load the studio: ${safe(error.message)}</div>`);
