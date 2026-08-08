const projectsEl = document.querySelector('#projects');
const projectDialog = document.querySelector('#project-dialog');
const detailDialog = document.querySelector('#detail-dialog');
const styleDialog = document.querySelector('#style-dialog');
const writerDialog = document.querySelector('#writer-dialog');
let projects = [];
let catalog = null;

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

function collectStory(form) {
  return {premise:form.elements.premise.value, format:form.elements.format.value, target_duration_minutes:Number(form.elements.target_duration_minutes.value), genre:form.elements.genre.value, audience:form.elements.audience.value, themes:form.elements.themes.value.split(',').map(value => value.trim()).filter(Boolean)};
}

document.querySelector('#new-project').onclick = () => projectDialog.showModal();
document.querySelector('#style-lab-nav').onclick = () => openStyleLab();
document.querySelector('#writer-nav').onclick = () => openWriterRoom();
document.querySelector('.close').onclick = () => projectDialog.close();
document.querySelector('#style-close').onclick = () => styleDialog.close();
document.querySelector('#writer-close').onclick = () => writerDialog.close();
document.querySelector('#project-form').onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); await api('/api/projects', {method:'POST', body:JSON.stringify(data)}); event.target.reset(); projectDialog.close(); await loadProjects(); };
document.querySelector('#style-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#style-project').value); await api(`/api/projects/${projectId}/style`, {method:'PUT', body:JSON.stringify(collectStyle(event.target))}); styleDialog.close(); await loadProjects(); openProject(projectId); };
document.querySelector('#writer-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#writer-project').value); const brief = await api(`/api/projects/${projectId}/story`, {method:'PUT', body:JSON.stringify(collectStory(event.target))}); await loadProjects(); renderStory(brief); };
loadProjects().catch(error => projectsEl.innerHTML = `<div class="empty">Could not load the studio: ${safe(error.message)}</div>`);
