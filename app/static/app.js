const projectsEl = document.querySelector('#projects');
const projectDialog = document.querySelector('#project-dialog');
const detailDialog = document.querySelector('#detail-dialog');
const crewDialog = document.querySelector('#crew-dialog');
const styleDialog = document.querySelector('#style-dialog');
const writerDialog = document.querySelector('#writer-dialog');
const characterDialog = document.querySelector('#character-dialog');
const renderDialog = document.querySelector('#render-dialog');
const worldDialog = document.querySelector('#world-dialog');
const shotDialog = document.querySelector('#shot-dialog');
const timelineDialog = document.querySelector('#timeline-dialog');
const audioDialog = document.querySelector('#audio-dialog');
const compositorDialog = document.querySelector('#compositor-dialog');
const workspaceMain = document.querySelector('#workspace-main');
const dashboardHome = document.querySelector('#dashboard-home');
const workspaceDialogs = [detailDialog, crewDialog, styleDialog, writerDialog, characterDialog, renderDialog, worldDialog, shotDialog, timelineDialog, audioDialog, compositorDialog];
const workspaceNav = new Map([
  [detailDialog, 'productions-nav'], [crewDialog, 'crew-nav'], [styleDialog, 'style-lab-nav'], [writerDialog, 'writer-nav'],
  [characterDialog, 'characters-nav'], [renderDialog, 'render-nav'], [worldDialog, 'worlds-nav'],
  [shotDialog, 'shots-nav'], [timelineDialog, 'timeline-nav'], [audioDialog, 'audio-nav'],
  [compositorDialog, 'compositor-nav'],
]);

function setActiveNavigation(navId = 'productions-nav') {
  document.querySelectorAll('.rail button').forEach(button => {
    const active = button.id === navId;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page'); else button.removeAttribute('aria-current');
  });
}

function openWorkspace(dialog) {
  if (dialog !== timelineDialog) stopMasterExportPolling();
  workspaceDialogs.forEach(item => {
    if (item !== dialog) {
      item.removeAttribute('open');
      item.classList.remove('workspace-view');
    }
  });
  dashboardHome.hidden = true;
  workspaceMain.classList.add('tool-open');
  workspaceMain.appendChild(dialog);
  dialog.classList.add('workspace-view');
  dialog.setAttribute('open', '');
  dialog.setAttribute('role', 'region');
  const heading = dialog.querySelector('h2');
  if (heading) dialog.setAttribute('aria-label', heading.textContent);
  const back = dialog.querySelector('.close');
  if (back) {
    back.textContent = '← Productions';
    back.title = 'Back to productions';
    back.setAttribute('aria-label', 'Back to productions');
  }
  setActiveNavigation(workspaceNav.get(dialog));
  renderProductionFlow();
  window.scrollTo({top: 0, left: 0, behavior: 'auto'});
}

function showDashboard() {
  stopMasterExportPolling();
  workspaceDialogs.forEach(dialog => {
    dialog.removeAttribute('open');
    dialog.classList.remove('workspace-view');
  });
  dashboardHome.hidden = false;
  workspaceMain.classList.remove('tool-open');
  setActiveNavigation();
  renderProductionFlow();
  window.scrollTo({top: 0, left: 0, behavior: 'auto'});
}

const productionStages = [
  {key:'story',label:'Story',nav:'writer-nav'}, {key:'style',label:'Style',nav:'style-lab-nav'},
  {key:'characters',label:'Cast',nav:'characters-nav'}, {key:'worlds',label:'Worlds',nav:'worlds-nav'},
  {key:'shots',label:'Shots',nav:'shots-nav'}, {key:'timeline',label:'Edit',nav:'timeline-nav'},
  {key:'audio',label:'Sound',nav:'audio-nav'}, {key:'composite',label:'Finish',nav:'compositor-nav'},
  {key:'render',label:'Master',nav:'render-nav'}
];

function currentFlowProject() {
  const openDialog=workspaceDialogs.find(dialog=>dialog.hasAttribute('open'));
  const selected=openDialog?.querySelector('select[id$="-project"]')?.value;
  return projects.find(project=>project.id===Number(selected))||projects[0]||null;
}

function currentFlowStage() {
  const openDialog=workspaceDialogs.find(dialog=>dialog.hasAttribute('open'));
  const nav=workspaceNav.get(openDialog);
  return productionStages.find(stage=>stage.nav===nav)?.key||'';
}

function productionReadiness(project) {
  const shots=project?.scenes?.flatMap(scene=>scene.shots||[])||[];
  return {
    story:Boolean(project?.story_brief?.synopsis), style:Boolean(project?.style_profile), characters:Boolean(project?.characters?.length),
    worlds:Boolean(project?.locations?.length), shots:Boolean(shots.length), timeline:Boolean(activeTimeline?.project_id===project?.id),
    audio:Boolean(activeAudioStudio?.project_id===project?.id), composite:Boolean(activeCompositorStudio?.project_id===project?.id&&activeCompositorStudio.shots?.some(shot=>shot.composition_id)), render:false
  };
}

function renderProductionFlow() {
  const host=document.querySelector('#production-flow');if(!host)return;const project=currentFlowProject(),ready=productionReadiness(project),current=currentFlowStage();
  host.innerHTML=`<span class="flow-label">${project?safe(project.title):'PRODUCTION FLOW'}</span>${productionStages.map((stage,index)=>`<button type="button" class="flow-node ${ready[stage.key]?'ready':''} ${current===stage.key?'current':''}" data-flow-nav="${stage.nav}" title="Open ${stage.label}"><i>${ready[stage.key]?'&#10003;':String(index+1).padStart(2,'0')}</i>${stage.label}</button>`).join('')}`;
  host.querySelectorAll('[data-flow-nav]').forEach(button=>button.onclick=()=>document.querySelector(`#${button.dataset.flowNav}`)?.click());
}

function setupCraftWorkspaces() {
  const form=document.querySelector('#writer-form');if(form&&!form.querySelector('.writer-document-sidebar')){
    const sidebar=document.createElement('aside'),canvas=document.createElement('section'),page=document.createElement('div');sidebar.className='writer-document-sidebar';canvas.className='writer-document-canvas';page.className='writer-document-page';
    const heading=form.querySelector(':scope > .eyebrow'),title=form.querySelector(':scope > h2'),intro=form.querySelector(':scope > .form-intro'),labels=[...form.querySelectorAll(':scope > label')],agent=form.querySelector(':scope > .writer-agent-panel');
    [heading,title,intro,labels[0],agent].forEach(node=>node&&sidebar.appendChild(node));[labels[1],form.querySelector(':scope > .writer-grid'),labels[2],form.querySelector(':scope > button.primary'),form.querySelector(':scope > .story-result')].forEach(node=>node&&page.appendChild(node));canvas.appendChild(page);form.append(sidebar,canvas);
  }
  const shell=document.querySelector('.shell'),toggle=document.querySelector('#rail-toggle'),collapsed=localStorage.getItem('kizuna-rail-collapsed')==='true';toggle.firstChild.nodeValue='\u2039';shell.classList.toggle('rail-collapsed',collapsed);toggle.setAttribute('aria-expanded',String(!collapsed));toggle.setAttribute('aria-label',collapsed?'Expand navigation':'Collapse navigation');
  toggle.onclick=()=>{const next=!shell.classList.contains('rail-collapsed');shell.classList.toggle('rail-collapsed',next);localStorage.setItem('kizuna-rail-collapsed',String(next));toggle.setAttribute('aria-expanded',String(!next));toggle.setAttribute('aria-label',next?'Expand navigation':'Collapse navigation');};
  const timelineControls=document.querySelector('.timeline-project-control');if(timelineControls&&!timelineControls.querySelector('.advanced-settings')){const details=document.createElement('details'),body=document.createElement('div');details.className='advanced-settings header-advanced';details.innerHTML='<summary>Master export</summary>';['master-profile','render-master','segment-size','plan-segmented-export'].forEach(id=>{const node=document.querySelector(`#${id}`);if(node)body.appendChild(node);});details.appendChild(body);timelineControls.appendChild(details);}
  const voice=document.querySelector('.voice-bible');if(voice&&!voice.closest('.advanced-settings')){const details=document.createElement('details');details.className='advanced-settings voice-setup';details.innerHTML='<summary>Voice setup & rights</summary>';voice.before(details);details.appendChild(voice);}
  setupSimplifiedCrew();
}

function setupSimplifiedCrew() {
  const panel=document.querySelector('.crew-panel');if(!panel||panel.querySelector('.crew-mode-panel'))return;panel.querySelector('.crew-title h2').textContent='AI Crew';panel.querySelector('.crew-title .form-intro').textContent='Choose how much help you want. You can change this at any time.';
  const producer=document.querySelector('.producer-console'),controls=producer.querySelector('.producer-controls'),settings=document.createElement('details'),settingsBody=document.createElement('div'),actions=document.createElement('div');settings.className='advanced-settings producer-settings';settings.innerHTML='<summary>Optional workflow settings</summary>';[...controls.querySelectorAll(':scope > label')].forEach(label=>settingsBody.appendChild(label));settings.appendChild(settingsBody);actions.className='producer-simple-actions';[...controls.querySelectorAll(':scope > button')].forEach(button=>actions.appendChild(button));controls.append(actions,settings);producer.querySelector('.producer-head h3').textContent='Make the next step';producer.querySelector('.producer-head p:not(.eyebrow)').textContent='Kizuna coordinates one reviewable step at a time.';document.querySelector('#start-producer').textContent='Start guided workflow';
  producer.insertAdjacentHTML('afterend','<section class="crew-mode-panel"><header><div><p class="eyebrow">HOW MUCH HELP?</p><h3>Choose your working style</h3><p>Guided is the safest default. Kizuna prepares the work and waits for your approval.</p></div><span id="crew-mode-status">Custom</span></header><div class="crew-modes"><button type="button" data-crew-preset="guided"><b>Guided</b><small>Recommended &middot; review every change</small></button><button type="button" data-crew-preset="autopilot"><b>Autopilot</b><small>Let the full crew execute</small></button><button type="button" data-crew-preset="manual"><b>Manual</b><small>No active AI departments</small></button><button type="button" data-crew-preset="custom"><b>Custom</b><small>Choose departments below</small></button></div></section><div class="crew-section-heading"><div><p class="eyebrow">YOUR STUDIO</p><h3>Departments</h3></div><small>Open a card only when you need advanced control.</small></div>');
  document.querySelectorAll('[data-crew-preset]').forEach(button=>button.onclick=()=>applyCrewPreset(button.dataset.crewPreset));document.querySelector('.crew-deploy button').textContent='Save custom crew';document.querySelector('.crew-deploy label').classList.add('advanced-only');
}
document.querySelector('#render-composition').insertAdjacentHTML('afterend','<button id="render-motion" type="button">Render motion preview</button>');
document.querySelector('.compositor-title').insertAdjacentHTML('afterend','<section class="visual-agent-panel animator-agent-panel"><div class="visual-agent-head"><div><p class="eyebrow">AI ANIMATOR</p><h3>Delegate the motion pass</h3><p>Select a shot, then review camera movement, acting beats, and editable layer keyframes.</p></div></div><div class="visual-agent-controls"><label>Engine<select id="animator-provider"><option value="simulation">Local motion planner</option><option value="openai">OpenAI Animator</option></select></label><label>Assignment<textarea id="animator-objective" rows="2">Create an economical, performance-led motion pass that preserves continuity.</textarea></label><label>Output<select id="animator-output"><option value="plan">Motion plan only</option><option value="proxy">Plan + proxy preview</option><option value="full">Plan + full-resolution preview</option></select></label><button id="ask-animator" type="button">Ask Animator</button></div><div id="animator-result"></div></section>');
document.querySelector('.animator-agent-panel').insertAdjacentHTML('afterend','<section class="asset-review-board"><div class="asset-review-head"><div><p class="eyebrow">ASSET REVIEW</p><h3>Compare, approve, and roll back versions</h3><p>The active version feeds new shots. Choosing an older version safely relinks matching layers without deleting history.</p></div><div id="asset-review-summary"></div></div><div id="asset-review-groups"></div></section>');
document.querySelector('.timeline-title').insertAdjacentHTML('afterend','<section class="visual-agent-panel editor-agent-panel"><div class="visual-agent-head"><div><p class="eyebrow">AI EDITOR</p><h3>Delegate the picture edit</h3><p>Review clip order, timing, transitions, continuity, and missing-production flags before the timeline changes.</p></div></div><div class="visual-agent-controls"><label>Engine<select id="editor-provider"><option value="simulation">Local edit planner</option><option value="openai">OpenAI Editor</option></select></label><label>Pacing<select id="editor-pacing"><option value="balanced">Balanced</option><option value="restrained">Restrained</option><option value="kinetic">Kinetic</option></select></label><label>Assignment<textarea id="editor-objective" rows="2">Shape a clear, emotionally paced assembly while preserving story continuity.</textarea></label><label>Output<select id="editor-output"><option value="edit">Edit plan only</option><option value="preview">Edit + review preview</option><option value="1080p">Edit + 1080p review</option><option value="4k">Edit + 4K review</option></select></label><button id="ask-editor" type="button">Ask Editor</button></div><div id="editor-result"></div></section>');
document.querySelector('#crew-briefing').insertAdjacentHTML('afterend','<section class="producer-console"><div class="producer-head"><div><p class="eyebrow">AI PRODUCER</p><h3>Coordinate the whole production</h3><p>Advance one safe stage at a time using only the department bots you deploy.</p></div><span id="producer-status">Not started</span></div><div class="producer-controls"><label>Production goal<textarea id="producer-objective" rows="2">Guide this production from its current state to a reviewable master.</textarea></label><label>Planning engine<select id="producer-provider"><option value="simulation">Local coordinator</option><option value="openai">Hosted department bots</option></select></label><label>Final review<select id="producer-review-profile"><option value="preview">Preview</option><option value="1080p">1080p</option><option value="4k">4K</option></select></label><label class="producer-check"><input id="producer-motion-previews" type="checkbox" checked> Render motion previews</label><label class="producer-check"><input id="producer-final-review" type="checkbox" checked> Render final review</label><button id="start-producer" type="button">Start workflow</button><button id="advance-producer" class="primary" type="button">Advance next stage</button></div><div id="producer-workflow"></div></section>');
document.querySelector('#layer-form > .primary').insertAdjacentHTML('beforebegin','<section class="motion-controls"><p class="eyebrow">END KEYFRAME</p><div class="motion-grid"><label>Easing<select name="motion_easing"><option value="linear">Linear</option><option value="ease-in">Ease in</option><option value="ease-out">Ease out</option><option value="ease-in-out">Ease in/out</option></select></label><label>End X<input name="motion_end_x" type="number" min="-1" max="2" step="0.01"></label><label>End Y<input name="motion_end_y" type="number" min="-1" max="2" step="0.01"></label><label>End scale<input name="motion_end_scale" type="number" min="0.05" max="5" step="0.05"></label><label>End rotation<input name="motion_end_rotation" type="number" min="-360" max="360" step="1"></label><label>End opacity<input name="motion_end_opacity" type="number" min="0" max="1" step="0.05"></label></div></section>');
document.querySelector('#render-animatic').insertAdjacentHTML('beforebegin','<select id="master-profile" aria-label="Master profile"><option value="preview">Preview · source up to 720p</option><option value="1080p">Master · 1080p</option><option value="4k">Master · 4K UHD</option></select>');
document.querySelector('#render-animatic').insertAdjacentHTML('afterend','<button id="render-master" type="button">Export continuous master</button>');
document.querySelector('#render-master').insertAdjacentHTML('afterend','<select id="segment-size" aria-label="Segment size"><option value="4">4 clips / segment</option><option value="2">2 clips / segment</option><option value="8">8 clips / segment</option></select><button id="plan-segmented-export" type="button">Start farm export</button>');
document.querySelector('#timeline-summary').insertAdjacentHTML('afterend','<div id="segmented-export-result"></div>');
document.querySelector('#timeline-summary').insertAdjacentHTML('beforebegin','<div class="edit-toolbar timeline-edit-toolbar"><span>EDIT TOOLS</span><label>Zoom<input id="timeline-zoom" type="range" min="140" max="360" value="220" step="10"></label><label class="toolbar-check"><input id="timeline-magnetic" type="checkbox" checked> Magnetic sequence</label><small>Drag clips to reorder</small></div>');
document.querySelector('#audio-summary').insertAdjacentHTML('afterend','<div class="edit-toolbar audio-edit-toolbar"><span>AUDIO TOOLS</span><label>Zoom<input id="audio-zoom" type="range" min="620" max="1800" value="900" step="20"></label><label>Snap<select id="audio-snap"><option value="0.1">0.1s</option><option value="0.25" selected>0.25s</option><option value="0.5">0.5s</option><option value="1">1s</option></select></label><label>Playhead<input id="audio-playhead" type="number" min="0" step="0.1" value="0"></label><button id="split-audio-region" type="button">Split</button><button id="duplicate-audio-region" type="button">Duplicate</button><button id="delete-audio-region" type="button">Delete</button></div>');
document.querySelector('#writer-form > .primary').insertAdjacentHTML('afterend','<section class="writer-agent-panel"><div><p class="eyebrow">AI WRITER</p><h3>Delegate the story pass</h3><p>Give the Writer a goal, then review its complete proposal before it touches the outline.</p></div><div class="writer-agent-controls"><label>Engine<select id="writer-provider"><option value="simulation">Local story planner</option><option value="openai">OpenAI Writer</option></select></label><label>Assignment<textarea id="writer-objective" rows="2">Develop a production-ready story foundation with strong visual causality and an emotionally decisive climax.</textarea></label><button id="ask-writer" type="button">Ask Writer</button></div><div id="writer-ai-result"></div></section>');
document.querySelector('.shot-title').insertAdjacentHTML('afterend','<section class="director-agent-panel"><div class="director-agent-intro"><div><p class="eyebrow">AI DIRECTOR</p><h3>Delegate scene coverage</h3><p>Generate a non-destructive camera and performance plan from the approved story.</p></div><div class="director-agent-controls"><label>Engine<select id="director-provider"><option value="simulation">Local coverage planner</option><option value="openai">OpenAI Director</option></select></label><label>Pacing<select id="director-pacing"><option value="restrained">Restrained</option><option value="balanced" selected>Balanced</option><option value="kinetic">Kinetic</option></select></label><label>Coverage<select id="director-coverage"><option value="2">2 shots / beat</option><option value="3" selected>3 shots / beat</option><option value="4">4 shots / beat</option><option value="6">6 shots / beat</option></select></label><label>Assignment<input id="director-objective" value="Create clear, economical coverage with strong performances and continuity."></label><button id="ask-director" type="button">Ask Director</button></div></div><div id="director-ai-result"></div></section>');
document.querySelector('#character-roster').insertAdjacentHTML('afterend','<section class="visual-agent-panel"><div class="visual-agent-head"><div><p class="eyebrow">AI CHARACTER DESIGNER</p><h3>Delegate the model bible</h3><p>Select a character, then review identity locks before generating a reference sheet.</p></div></div><div class="visual-agent-controls"><label>Engine<select id="character-agent-provider"><option value="simulation">Local design planner</option><option value="openai">OpenAI visual development</option></select></label><label>Assignment<input id="character-agent-objective" value="Create an original, animation-ready identity with strong consistency locks."></label><label>Generation<select id="character-agent-generation"><option value="none">Bible only</option><option value="mock">Bible + simulation sheet</option><option value="farm">Bible + render farm</option><option value="comfyui">Bible + local ComfyUI</option></select></label><button id="ask-character-designer" type="button">Ask Designer</button></div><div id="character-agent-result"></div></section>');
document.querySelector('#world-roster').insertAdjacentHTML('afterend','<section class="visual-agent-panel"><div class="visual-agent-head"><div><p class="eyebrow">AI BACKGROUND ARTIST</p><h3>Delegate the environment bible</h3><p>Select a location, then review geography, layers, lighting, and continuity before generation.</p></div></div><div class="visual-agent-controls"><label>Engine<select id="background-agent-provider"><option value="simulation">Local design planner</option><option value="openai">OpenAI visual development</option></select></label><label>Assignment<input id="background-agent-objective" value="Create a reusable, camera-ready environment with clear staging and continuity."></label><label>Generation<select id="background-agent-generation"><option value="none">Bible only</option><option value="mock">Bible + simulation concept</option><option value="comfyui">Bible + local ComfyUI</option></select></label><button id="ask-background-artist" type="button">Ask Artist</button></div><div id="background-agent-result"></div></section>');
document.querySelector('#save-voice').insertAdjacentHTML('afterend','<section class="voice-automation"><p class="eyebrow">AI PERFORMANCE</p><div class="voice-grid"><label>Provider<select id="voice-provider"><option value="simulation">Timing slate</option><option value="openai">OpenAI voice</option></select></label><label>Voice ID<input id="voice-provider-id" placeholder="coral"></label><label class="voice-rights"><input id="voice-consent" type="checkbox"> Rights / AI disclosure confirmed</label><button id="save-voice-rights" type="button">Save rights record</button></div><div class="pronunciation-row"><input id="pronunciation-term" placeholder="Term, e.g. Kizuna"><input id="pronunciation-value" placeholder="Pronunciation, e.g. kee-zoo-nah"><button id="add-pronunciation" type="button">Add pronunciation</button></div><div class="ai-disclosure">AI-generated performances must be disclosed to the audience. Only use voices you are authorized to use.</div></section>');
let projects = [];
let catalog = null;
let activeCharacterId = null;
let activeLocationId = null;
let activeShotId = null;
let activeTimeline = null;
let activeClipId = null;
let activeAudioStudio = null;
let activeAudioTimeline = null;
let activeAudioCueId = null;
let activeCrew = null;
let activeProducerWorkflow = null;
let crewRoles = [];
let activeCompositorStudio = null;
let activeComposition = null;
let activeCompositorShotId = null;
let activeCompositionLayerId = null;
let activeMasterExport = null;
let masterExportPollTimer = null;
let generationProviders = [];
let draggedTimelineClipId = null;
let audioDragState = null;

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type': 'application/json'}, ...options});
  if (!response.ok) { const text=await response.text();try{throw new Error(JSON.parse(text).detail||text);}catch(error){if(error instanceof SyntaxError)throw new Error(text);throw error;} }
  if (response.status === 204) return null;
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
  renderProductionFlow();
}

async function openProject(id) {
  const project = await api(`/api/projects/${id}`);
  const style = project.style_profile;
  document.querySelector('#detail').innerHTML = `
    <div class="detail-head"><div><p class="eyebrow" style="color:#e84b38">${safe(project.status.toUpperCase())}</p><h2>${safe(project.title)}</h2><p>${safe(project.logline)}</p><button class="style-launch" data-style-id="${project.id}">Edit Creative DNA</button><button class="writer-launch" data-writer-id="${project.id}">Develop Story</button></div><button class="close" data-close-detail>×</button></div>
    <div class="style-grid"><div class="style-card"><b>ERA BLEND</b>${safe(style.era_primary)} × ${safe(style.era_secondary)}</div><div class="style-card"><b>VISUAL DNA</b>${safe(Object.values(style.visual).join(' · '))}</div><div class="style-card"><b>STORY DNA</b>${safe(Object.values(style.narrative).join(' · '))}</div></div>
    <h3>Scenes</h3>${project.scenes.length ? project.scenes.map(scene => `<div class="scene"><strong>${scene.position}. ${safe(scene.title)}</strong><br><small>${safe(scene.summary)} · ${scene.shots.length} shots</small></div>`).join('') : '<div class="empty">Scene planning will appear here.</div>'}`;
  openWorkspace(detailDialog);
  setupStorageConsole(project.id);
  document.querySelector('[data-close-detail]').onclick = showDashboard;
  document.querySelector('[data-style-id]').onclick = event => { detailDialog.close(); openStyleLab(Number(event.currentTarget.dataset.styleId)); };
  document.querySelector('[data-writer-id]').onclick = event => { detailDialog.close(); openWriterRoom(Number(event.currentTarget.dataset.writerId)); };
}

async function setupStorageConsole(projectId) {
  const detail=document.querySelector('#detail');if(!detail.querySelector('#storage-console'))detail.insertAdjacentHTML('beforeend','<section id="storage-console" class="production-storage"><div class="storage-loading">Loading production storage...</div></section>');
  const host=detail.querySelector('#storage-console');
  try {
    const [policy,backups,links,studio]=await Promise.all([api(`/api/projects/${projectId}/storage-policy`),api(`/api/projects/${projectId}/backups`),api(`/api/projects/${projectId}/delivery-links`),api(`/api/projects/${projectId}/compositor`)]);
    const assets=studio.assets.filter(asset=>asset.active);
    host.innerHTML=`<header><div><p class="eyebrow">PRODUCTION VAULT</p><h3>Backups & secure delivery</h3><p>Package the editable project with its media, then issue expiring review links without exposing the studio.</p></div><span>${safe(policy.backend)} storage</span></header><div class="storage-grid"><section><h4>Backup policy</h4><div class="storage-fields"><label>Keep for days<input id="storage-retention" type="number" min="1" max="3650" value="${policy.retention_days}"></label><label>Maximum copies<input id="storage-max" type="number" min="1" max="100" value="${policy.max_backups}"></label></div><label class="storage-check"><input id="storage-media" type="checkbox" ${policy.include_media?'checked':''}> Include generated media</label><div class="storage-actions"><button id="save-storage-policy" type="button">Save policy</button><button id="create-backup" class="primary" type="button">Create backup</button></div><div id="backup-list" class="vault-list">${backups.length?backups.map(item=>`<a href="${item.download_url}"><b>${safe(item.filename)}</b><small>${item.asset_count} assets Â· ${(item.size_bytes/1024).toFixed(1)} KB Â· ${safe(item.checksum_sha256.slice(0,10))}</small></a>`).join(''):'<span>No backups yet.</span>'}</div></section><section><h4>Expiring delivery link</h4><label>Approved asset<select id="delivery-asset">${assets.length?assets.map(asset=>`<option value="${safe(asset.uri)}">${safe(asset.name)} Â· v${asset.version}</option>`).join(''):'<option value="">Approve an asset first</option>'}</select></label><label>Label<input id="delivery-label" value="Studio review"></label><div class="storage-fields"><label>Expires in hours<input id="delivery-hours" type="number" min="1" max="720" value="72"></label><label>Download limit<input id="delivery-limit" type="number" min="1" max="10000" value="10"></label></div><button id="create-delivery" type="button" ${assets.length?'':'disabled'}>Create secure link</button><div id="delivery-result"></div><div class="vault-list">${links.length?links.map(link=>`<span><b>${safe(link.label)}</b><small>${link.download_count}/${link.max_downloads} downloads Â· ${link.revoked?'revoked':'expires '+new Date(link.expires_at).toLocaleDateString()}</small></span>`).join(''):'<span>No delivery links yet.</span>'}</div></section></div>`;
    document.querySelector('#save-storage-policy').onclick=async()=>{await api(`/api/projects/${projectId}/storage-policy`,{method:'PUT',body:JSON.stringify({retention_days:Number(document.querySelector('#storage-retention').value),max_backups:Number(document.querySelector('#storage-max').value),include_media:document.querySelector('#storage-media').checked})});await setupStorageConsole(projectId);};
    document.querySelector('#create-backup').onclick=async event=>{event.currentTarget.disabled=true;event.currentTarget.textContent='Packagingâ€¦';await api(`/api/projects/${projectId}/backups`,{method:'POST'});await setupStorageConsole(projectId);};
    document.querySelector('#create-delivery').onclick=async()=>{const link=await api(`/api/projects/${projectId}/delivery-links`,{method:'POST',body:JSON.stringify({asset_uri:document.querySelector('#delivery-asset').value,label:document.querySelector('#delivery-label').value,expires_hours:Number(document.querySelector('#delivery-hours').value),max_downloads:Number(document.querySelector('#delivery-limit').value)})}),url=new URL(link.url,location.origin).href;document.querySelector('#delivery-result').innerHTML=`<div class="delivery-created"><b>Copy this link now</b><input readonly value="${safe(url)}"><button type="button" id="copy-delivery">Copy link</button></div>`;document.querySelector('#copy-delivery').onclick=()=>navigator.clipboard.writeText(url);};
  } catch(error) { host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`; }
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
  openWorkspace(styleDialog);
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
  openWorkspace(writerDialog);
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
  document.querySelector('#writer-ai-result').innerHTML = '';
  renderStory(brief);
}

function renderStory(brief) {
  const result = document.querySelector('#story-result');
  if (!brief?.synopsis) { result.innerHTML = ''; return; }
  result.innerHTML = `<div class="synopsis"><b>WORKING SYNOPSIS</b><div data-synopsis>${safe(brief.synopsis)}</div></div><div class="beats">${brief.beats.map(beat => `<div class="beat" data-position="${safe(beat.position)}" data-name="${safe(beat.name)}"><b>${safe(beat.position)} · ${safe(beat.name)}</b><textarea aria-label="${safe(beat.name)} summary">${safe(beat.summary)}</textarea></div>`).join('')}</div><div class="outline-actions"><button type="button" id="save-outline">Save outline edits</button></div>`;
  result.insertAdjacentHTML('afterbegin',`<section class="story-flow-map"><header><span>STORY FLOW</span><small>Click any beat to open its card</small></header><div>${brief.beats.map(beat=>`<button type="button" data-story-beat="${safe(beat.position)}"><i>${safe(beat.position)}</i><b>${safe(beat.name)}</b></button>`).join('')}</div></section>`);
  result.querySelectorAll('[data-story-beat]').forEach(button=>button.onclick=()=>result.querySelector(`.beat[data-position="${CSS.escape(button.dataset.storyBeat)}"]`)?.scrollIntoView({behavior:'smooth',block:'center'}));
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

async function askWriter() {
  const projectId=Number(document.querySelector('#writer-project').value), form=document.querySelector('#writer-form'), result=document.querySelector('#writer-ai-result');
  const payload={...collectStory(form),objective:document.querySelector('#writer-objective').value,provider:document.querySelector('#writer-provider').value};
  result.innerHTML='<div class="render-progress">Writer is reading the production bible and developing a structured proposal…</div>';
  try { renderWriterAction(await api(`/api/projects/${projectId}/crew/writer/propose`,{method:'POST',body:JSON.stringify(payload)})); }
  catch(error) { result.innerHTML=`<div class="job-error">${safe(error.message)}</div>${error.message.includes('Deploy the Writer')?'<button id="deploy-writer-here" type="button">Deploy Writer for this production</button>':''}`;const deploy=document.querySelector('#deploy-writer-here');if(deploy)deploy.onclick=async()=>{await api(`/api/projects/${projectId}/crew/deploy`,{method:'POST',body:JSON.stringify({roles:['writer'],autonomy:'propose'})});await askWriter();}; }
}

function renderWriterAction(action) {
  const result=document.querySelector('#writer-ai-result'), proposal=action.payload?.proposal;
  if(action.status==='failed'){result.innerHTML=`<div class="job-error">${safe(action.error)}</div>`;return;}
  if(action.status==='rejected'){result.innerHTML='<div class="crew-empty">Writer proposal rejected. The working outline was not changed.</div>';return;}
  if(action.status==='completed'){result.innerHTML='<div class="writer-applied">Writer completed the assignment and updated the working outline.</div>';loadProjects().then(()=>fillStory(action.project_id));return;}
  if(!proposal){result.innerHTML='<div class="job-error">Writer proposal is unavailable.</div>';return;}
  result.innerHTML=`<article class="writer-proposal"><header><div><p class="eyebrow">PROPOSED STORY PACKAGE</p><h3>${safe(proposal.genre)} · ${safe(proposal.format)} · ${proposal.target_duration_minutes} min</h3></div><span>Awaiting approval</span></header><p class="proposal-rationale">${safe(proposal.rationale)}</p><div class="proposal-synopsis"><b>Synopsis</b><p>${safe(proposal.synopsis)}</p></div><div class="proposal-beats">${proposal.beats.map(beat=>`<div><b>${safe(beat.position)} · ${safe(beat.name)}</b><p>${safe(beat.summary)}</p></div>`).join('')}</div><div class="proposal-notes"><span><b>Changes</b>${proposal.changes.map(item=>`<small>${safe(item)}</small>`).join('')}</span><span><b>Review notes</b>${proposal.warnings.map(item=>`<small>${safe(item)}</small>`).join('')}</span></div><div class="crew-action-buttons"><button id="approve-writer-action" class="primary" type="button">Approve & apply outline</button><button id="reject-writer-action" type="button">Reject proposal</button></div></article>`;
  document.querySelector('#approve-writer-action').onclick=async()=>renderWriterAction(await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'}));
  document.querySelector('#reject-writer-action').onclick=async()=>renderWriterAction(await api(`/api/crew-actions/${action.id}/reject`,{method:'POST'}));
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
  openWorkspace(characterDialog);
}

function renderCharacterRosterLegacy(projectId) {
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

async function askCharacterDesigner() {
  const result=document.querySelector('#character-agent-result'), projectId=Number(document.querySelector('#character-project').value);
  if(!activeCharacterId){result.innerHTML='<div class="job-error">Select an existing character first.</div>';return;}
  const generation=document.querySelector('#character-agent-generation').value;
  const payload={objective:document.querySelector('#character-agent-objective').value,provider:document.querySelector('#character-agent-provider').value,queue_generation:generation!=='none',generation_provider:generation==='none'?'mock':generation};
  result.innerHTML='<div class="render-progress">Character Designer is developing identity, wardrobe, palette, and consistency locks…</div>';
  try{renderCharacterDesignerAction(await api(`/api/characters/${activeCharacterId}/crew/design`,{method:'POST',body:JSON.stringify(payload)}));}
  catch(error){result.innerHTML=`<div class="job-error">${safe(error.message)}</div>${error.message.includes('Deploy the Character Designer')?'<button id="deploy-character-designer" type="button">Deploy Character Designer</button>':''}`;const deploy=document.querySelector('#deploy-character-designer');if(deploy)deploy.onclick=async()=>{await api(`/api/projects/${projectId}/crew/deploy`,{method:'POST',body:JSON.stringify({roles:['character_designer'],autonomy:'propose'})});await askCharacterDesigner();};}
}

function renderCharacterDesignerAction(action) {
  const result=document.querySelector('#character-agent-result'), proposal=action.payload?.proposal;
  if(action.status==='failed'){result.innerHTML=`<div class="job-error">${safe(action.error)}</div>`;return;}
  if(action.status==='rejected'){result.innerHTML='<div class="crew-empty">Character design rejected. The current model bible was not changed.</div>';return;}
  if(action.status==='completed'){const data=action.result;result.innerHTML=`<div class="visual-applied">Character bible v${data.version} applied${data.generation_queued?` · ${safe(data.generation_provider)} job ${data.generation_job_id} is ${safe(data.generation_status)}`:''}${data.generation_error?` · generation needs attention: ${safe(data.generation_error)}`:''}.</div>`;loadProjects().then(()=>selectCharacter(action.project_id,data.character_id));return;}
  if(!proposal){result.innerHTML='<div class="job-error">Character design proposal is unavailable.</div>';return;}
  result.innerHTML=`<article class="visual-proposal"><header><div><p class="eyebrow">PROPOSED MODEL BIBLE</p><h3>Identity, wardrobe & consistency</h3></div><span>Awaiting approval</span></header><p>${safe(proposal.rationale)}</p><div class="visual-proposal-grid"><section><h4>Appearance</h4>${Object.entries(proposal.appearance).map(([key,value])=>`<span><b>${safe(key.replaceAll('_',' '))}</b> · ${safe(value)}</span>`).join('')}</section><section><h4>Palette & wardrobe</h4>${proposal.palette.map(item=>`<span>COLOR · ${safe(item)}</span>`).join('')}${proposal.wardrobe.map(item=>`<span>LOOK · ${safe(item)}</span>`).join('')}</section></div><div class="visual-locks">${proposal.consistency_anchors.map(item=>`<span>LOCK · ${safe(item)}</span>`).join('')}</div><div class="crew-action-buttons"><button id="approve-character-design" class="primary" type="button">Approve bible${action.payload.request.queue_generation?' & queue sheet':''}</button><button id="reject-character-design" type="button">Reject</button></div></article>`;
  document.querySelector('#approve-character-design').onclick=async()=>renderCharacterDesignerAction(await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'}));
  document.querySelector('#reject-character-design').onclick=async()=>renderCharacterDesignerAction(await api(`/api/crew-actions/${action.id}/reject`,{method:'POST'}));
}

async function openWorldStudio(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  if (!generationProviders.length) generationProviders = (await api('/api/generation/providers')).providers;
  const projectSelect = document.querySelector('#world-project');
  projectSelect.innerHTML = options(projects.map(p => ({id:String(p.id), label:p.title})), String(projectId || projects[0].id));
  projectSelect.onchange = () => { activeLocationId = null; clearWorldForm(); renderWorldRoster(Number(projectSelect.value)); };
  renderWorldRoster(Number(projectSelect.value));
  document.querySelector('#world-result').innerHTML = '';
  openWorkspace(worldDialog);
}

function renderWorldRoster(projectId) {
  const locations = projects.find(project => project.id === projectId)?.locations || [];
  document.querySelector('#world-roster').innerHTML = `<button type="button" class="world-pill ${activeLocationId === null ? 'active' : ''}" data-new-world>＋ New</button>${locations.map(location => `<button type="button" class="world-pill ${activeLocationId === location.id ? 'active' : ''}" data-location-id="${location.id}"><b>${safe(location.name)}</b>${location.design ? ` · bible v${location.design.version}` : ''}</button>`).join('')}`;
  document.querySelector('[data-new-world]').onclick = () => { activeLocationId = null; clearWorldForm(); renderWorldRoster(projectId); };
  document.querySelectorAll('[data-location-id]').forEach(button => button.onclick = () => selectWorld(projectId, Number(button.dataset.locationId)));
}

function clearWorldForm() {
  const form = document.querySelector('#world-form');
  ['name','narrative_function','geography','time_period','description','architecture','materials','atmosphere','scale','staging_zones','perspective','world_palette','layers','lighting_variants','continuity_anchors'].forEach(name => form.elements[name].value = '');
  document.querySelector('#world-result').innerHTML = '';
}

function selectWorld(projectId, locationId) {
  const location = projects.find(project => project.id === projectId)?.locations.find(item => item.id === locationId);
  if (!location) return;
  activeLocationId = locationId;
  const form = document.querySelector('#world-form');
  ['name','narrative_function','geography','time_period','description'].forEach(name => form.elements[name].value = location[name] || '');
  const appearance = location.design?.appearance || {};
  ['architecture','materials','atmosphere','scale','staging_zones','perspective'].forEach(name => form.elements[name].value = appearance[name] || '');
  form.elements.world_palette.value = (location.design?.palette || []).join(', ');
  form.elements.layers.value = (location.design?.layers || []).join(', ');
  form.elements.lighting_variants.value = (location.design?.lighting_variants || []).join(', ');
  form.elements.continuity_anchors.value = (location.design?.continuity_anchors || []).join(', ');
  renderWorldRoster(projectId);
  if (location.design) renderWorldDesign(location, location.design); else document.querySelector('#world-result').innerHTML = '';
}

function collectWorld(form) {
  return {name:form.elements.name.value, narrative_function:form.elements.narrative_function.value, description:form.elements.description.value, geography:form.elements.geography.value, time_period:form.elements.time_period.value};
}

function collectWorldDesign(form) {
  return {appearance:{architecture:form.elements.architecture.value, materials:form.elements.materials.value, atmosphere:form.elements.atmosphere.value, scale:form.elements.scale.value, staging_zones:form.elements.staging_zones.value, perspective:form.elements.perspective.value}, palette:listValue(form,'world_palette'), layers:listValue(form,'layers'), lighting_variants:listValue(form,'lighting_variants'), continuity_anchors:listValue(form,'continuity_anchors')};
}

function renderWorldDesign(location, design) {
  const providerOptions = generationProviders.filter(provider => provider.id !== 'farm').map(provider => `<option value="${safe(provider.id)}" ${provider.id === 'mock' ? 'selected' : ''}>${safe(provider.label)}${provider.ready ? '' : ' · setup required'}</option>`).join('');
  document.querySelector('#world-result').innerHTML = `<div class="reference-brief"><b>BACKGROUND PRODUCTION BRIEF · V${design.version}</b>${safe(design.reference_brief)}</div><div class="layer-plan">${design.layers.map((layer,index) => `<span>LAYER ${index+1} · ${safe(layer)}</span>`).join('')}</div><div class="lighting-plan">${design.lighting_variants.map(light => `<span>LIGHT · ${safe(light)}</span>`).join('')}</div><div class="anchor-list">${design.continuity_anchors.map(anchor => `<span>LOCK · ${safe(anchor)}</span>`).join('')}</div><div class="world-generation"><select id="background-provider" aria-label="Background provider">${providerOptions}</select><button type="button" id="generate-background">Generate background concept</button></div><div id="background-result"></div>`;
  document.querySelector('#generate-background').onclick = generateBackground;
}

async function generateBackground() {
  if (!activeLocationId) return;
  const button = document.querySelector('#generate-background');
  button.disabled = true; button.textContent = 'Queuing generation…';
  try { renderBackgroundJob(await api(`/api/locations/${activeLocationId}/generate`, {method:'POST', body:JSON.stringify({provider:document.querySelector('#background-provider').value})})); }
  catch (error) { document.querySelector('#background-result').innerHTML = `<div class="job-error">${safe(error.message)}</div>`; }
  finally { button.disabled = false; button.textContent = 'Generate background concept'; }
}

function renderBackgroundJob(job) {
  const result = document.querySelector('#background-result');
  if (job.status === 'failed') { result.innerHTML = `<div class="job-error">${safe(job.error)}</div>`; return; }
  if (job.assets.length) { const asset = job.assets[0]; result.innerHTML = `<div class="background-preview"><img src="${safe(asset.uri)}" alt="Generated background concept for the selected location"></div><div class="generation-actions"><small>${safe(job.provider)} · background v${asset.version} · job ${job.id}</small></div>`; return; }
  result.innerHTML = `<div class="world-generation"><small>${safe(job.provider)} job ${job.external_id || job.id} is ${safe(job.status)}.</small>${job.provider === 'comfyui' ? `<button type="button" data-sync-background="${job.id}">Check result</button>` : ''}</div>`;
  const sync = document.querySelector('[data-sync-background]');
  if (sync) sync.onclick = async () => renderBackgroundJob(await api(`/api/background-jobs/${job.id}/sync`, {method:'POST'}));
}

async function askBackgroundArtist() {
  const result=document.querySelector('#background-agent-result'), projectId=Number(document.querySelector('#world-project').value);
  if(!activeLocationId){result.innerHTML='<div class="job-error">Select an existing location first.</div>';return;}
  const generation=document.querySelector('#background-agent-generation').value;
  const payload={objective:document.querySelector('#background-agent-objective').value,provider:document.querySelector('#background-agent-provider').value,queue_generation:generation!=='none',generation_provider:generation==='none'?'mock':generation};
  result.innerHTML='<div class="render-progress">Background Artist is planning geography, layers, lighting, and continuity…</div>';
  try{renderBackgroundArtistAction(await api(`/api/locations/${activeLocationId}/crew/design`,{method:'POST',body:JSON.stringify(payload)}));}
  catch(error){result.innerHTML=`<div class="job-error">${safe(error.message)}</div>${error.message.includes('Deploy the Background Artist')?'<button id="deploy-background-artist" type="button">Deploy Background Artist</button>':''}`;const deploy=document.querySelector('#deploy-background-artist');if(deploy)deploy.onclick=async()=>{await api(`/api/projects/${projectId}/crew/deploy`,{method:'POST',body:JSON.stringify({roles:['background_artist'],autonomy:'propose'})});await askBackgroundArtist();};}
}

function renderBackgroundArtistAction(action) {
  const result=document.querySelector('#background-agent-result'), proposal=action.payload?.proposal;
  if(action.status==='failed'){result.innerHTML=`<div class="job-error">${safe(action.error)}</div>`;return;}
  if(action.status==='rejected'){result.innerHTML='<div class="crew-empty">Background design rejected. The current environment bible was not changed.</div>';return;}
  if(action.status==='completed'){const data=action.result;result.innerHTML=`<div class="visual-applied">Environment bible v${data.version} applied${data.generation_queued?` · ${safe(data.generation_provider)} job ${data.generation_job_id} is ${safe(data.generation_status)}`:''}${data.generation_error?` · generation needs attention: ${safe(data.generation_error)}`:''}.</div>`;loadProjects().then(()=>selectWorld(action.project_id,data.location_id));return;}
  if(!proposal){result.innerHTML='<div class="job-error">Background design proposal is unavailable.</div>';return;}
  result.innerHTML=`<article class="visual-proposal"><header><div><p class="eyebrow">PROPOSED ENVIRONMENT BIBLE</p><h3>Geography, layers & lighting</h3></div><span>Awaiting approval</span></header><p>${safe(proposal.rationale)}</p><div class="visual-proposal-grid"><section><h4>Construction</h4>${Object.entries(proposal.appearance).map(([key,value])=>`<span><b>${safe(key.replaceAll('_',' '))}</b> · ${safe(value)}</span>`).join('')}</section><section><h4>Production layers</h4>${proposal.layers.map(item=>`<span>LAYER · ${safe(item)}</span>`).join('')}${proposal.lighting_variants.map(item=>`<span>LIGHT · ${safe(item)}</span>`).join('')}</section></div><div class="visual-locks">${proposal.continuity_anchors.map(item=>`<span>LOCK · ${safe(item)}</span>`).join('')}</div><div class="crew-action-buttons"><button id="approve-background-design" class="primary" type="button">Approve bible${action.payload.request.queue_generation?' & queue concept':''}</button><button id="reject-background-design" type="button">Reject</button></div></article>`;
  document.querySelector('#approve-background-design').onclick=async()=>renderBackgroundArtistAction(await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'}));
  document.querySelector('#reject-background-design').onclick=async()=>renderBackgroundArtistAction(await api(`/api/crew-actions/${action.id}/reject`,{method:'POST'}));
}

async function askAnimator() {
  const result=document.querySelector('#animator-result'), projectId=Number(document.querySelector('#compositor-project').value);
  if(!activeCompositorShotId){result.innerHTML='<div class="job-error">Select a planned shot first.</div>';return;}
  const output=document.querySelector('#animator-output').value;
  const payload={objective:document.querySelector('#animator-objective').value,provider:document.querySelector('#animator-provider').value,render_preview:output!=='plan',quality:output==='full'?'full':'proxy'};
  result.innerHTML='<div class="render-progress">Animator is planning acting beats, camera movement, and editable layer keyframes…</div>';
  try{renderAnimatorAction(await api(`/api/shots/${activeCompositorShotId}/crew/animate`,{method:'POST',body:JSON.stringify(payload)}));}
  catch(error){result.innerHTML=`<div class="job-error">${safe(error.message)}</div>${error.message.includes('Deploy the Animator')?'<button id="deploy-animator-here" type="button">Deploy Animator</button>':''}`;const deploy=document.querySelector('#deploy-animator-here');if(deploy)deploy.onclick=async()=>{await api(`/api/projects/${projectId}/crew/deploy`,{method:'POST',body:JSON.stringify({roles:['animator'],autonomy:'propose'})});await askAnimator();};}
}

async function refreshAnimatorComposition(projectId, shotId) {
  activeCompositorStudio=await api(`/api/projects/${projectId}/compositor`);activeCompositorShotId=shotId;activeComposition=await api(`/api/shots/${shotId}/composition`);renderAssetReview();renderCompositorShots();renderCompositionEditor();if(activeComposition.layers.length)selectCompositionLayer(activeComposition.layers[0].id);
}

function renderAnimatorAction(action) {
  const result=document.querySelector('#animator-result'), proposal=action.payload?.proposal;
  if(action.status==='failed'){result.innerHTML=`<div class="job-error">${safe(action.error)}</div>`;return;}
  if(action.status==='rejected'){result.innerHTML='<div class="crew-empty">Motion proposal rejected. The composition was not changed.</div>';return;}
  if(action.status==='completed'){const data=action.result;result.innerHTML=`<div class="visual-applied">Motion pass applied to ${data.applied_layers.length} layer${data.applied_layers.length===1?'':'s'} · composition v${data.composition_version}${data.preview_queued?` · preview ${safe(data.preview_status)}`:''}${data.preview_error?` · render needs attention: ${safe(data.preview_error)}`:''}.</div>`;refreshAnimatorComposition(action.project_id,data.shot_id);return;}
  if(!proposal){result.innerHTML='<div class="job-error">Animator proposal is unavailable.</div>';return;}
  result.innerHTML=`<article class="visual-proposal animator-proposal"><header><div><p class="eyebrow">PROPOSED MOTION PASS</p><h3>Acting, camera & layer motion</h3></div><span>Awaiting approval</span></header><p>${safe(proposal.approach)}</p><div class="visual-proposal-grid"><section><h4>Virtual camera</h4><span><b>${safe(proposal.camera.move)}</b> · ${safe(proposal.camera.intent)}</span><span>${proposal.camera.start_scale.toFixed(2)}× → ${proposal.camera.end_scale.toFixed(2)}× · pan ${proposal.camera.pan_x.toFixed(2)}, ${proposal.camera.pan_y.toFixed(2)}</span>${proposal.acting_beats.map((item,index)=>`<span>BEAT ${index+1} · ${safe(item)}</span>`).join('')}</section><section><h4>Editable layer motion</h4>${proposal.layer_motions.map(item=>`<span><b>${safe(item.layer_name)}</b> · ${safe(item.intent)}<small>${item.end_x.toFixed(2)}, ${item.end_y.toFixed(2)} · ${item.end_scale.toFixed(2)}× · ${safe(item.easing)}</small></span>`).join('')}</section></div><div class="visual-locks">${proposal.timing_notes.map(item=>`<span>TIMING · ${safe(item)}</span>`).join('')}</div><div class="crew-action-buttons"><button id="approve-animation" class="primary" type="button">Approve motion${action.payload.request.render_preview?' & render preview':''}</button><button id="reject-animation" type="button">Reject</button></div></article>`;
  document.querySelector('#approve-animation').onclick=async()=>{result.innerHTML='<div class="render-progress">Applying editable keyframes and rendering the requested preview…</div>';renderAnimatorAction(await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'}));};
  document.querySelector('#reject-animation').onclick=async()=>renderAnimatorAction(await api(`/api/crew-actions/${action.id}/reject`,{method:'POST'}));
}

async function askEditor() {
  const projectId=Number(document.querySelector('#timeline-project').value), result=document.querySelector('#editor-result'), output=document.querySelector('#editor-output').value;
  const payload={objective:document.querySelector('#editor-objective').value,pacing:document.querySelector('#editor-pacing').value,provider:document.querySelector('#editor-provider').value,render_review:output!=='edit',review_profile:output==='edit'?'preview':output};
  result.innerHTML='<div class="render-progress">Editor is analyzing action, dialogue, continuity, picture readiness, and pacing…</div>';
  try{renderEditorAction(await api(`/api/projects/${projectId}/crew/editor/propose`,{method:'POST',body:JSON.stringify(payload)}));}
  catch(error){result.innerHTML=`<div class="job-error">${safe(error.message)}</div>${error.message.includes('Deploy the Editor')?'<button id="deploy-editor-here" type="button">Deploy Editor</button>':''}`;const deploy=document.querySelector('#deploy-editor-here');if(deploy)deploy.onclick=async()=>{await api(`/api/projects/${projectId}/crew/deploy`,{method:'POST',body:JSON.stringify({roles:['editor'],autonomy:'propose'})});await askEditor();};}
}

function renderEditorAction(action) {
  const result=document.querySelector('#editor-result'), proposal=action.payload?.proposal;
  if(action.status==='failed'){result.innerHTML=`<div class="job-error">${safe(action.error)}</div>`;return;}
  if(action.status==='rejected'){result.innerHTML='<div class="crew-empty">Edit proposal rejected. The current timeline was not changed.</div>';return;}
  if(action.status==='completed'){const data=action.result;const message=`<div class="visual-applied">Edit applied to ${data.applied_clips.length} clips · ${data.total_duration_seconds.toFixed(1)}s runtime${data.review_rendered?` · review ${safe(data.review_status)}`:''}${data.review_error?` · render needs attention: ${safe(data.review_error)}`:''}${data.review_uri?` · <a href="${safe(data.review_uri)}" target="_blank">open review master</a>`:''}.</div>`;loadTimeline(action.project_id).then(()=>{document.querySelector('#editor-result').innerHTML=message;});return;}
  if(!proposal){result.innerHTML='<div class="job-error">Editor proposal is unavailable.</div>';return;}
  result.innerHTML=`<article class="visual-proposal editor-proposal"><header><div><p class="eyebrow">PROPOSED PICTURE EDIT</p><h3>${proposal.clips.length} clips · ${proposal.estimated_runtime_seconds.toFixed(1)}s</h3></div><span>Awaiting approval</span></header><p>${safe(proposal.approach)}</p><div class="editor-clip-list">${proposal.clips.map(item=>`<div><b>${item.position}. ${safe(item.shot_title)}</b><span>${item.duration_seconds.toFixed(1)}s · ${safe(item.transition)}${item.transition!=='cut'?` ${item.transition_duration.toFixed(1)}s`:''}</span><small>${safe(item.rationale)}</small></div>`).join('')}</div><div class="visual-proposal-grid"><section><h4>Rhythm</h4>${proposal.rhythm_notes.map(item=>`<span>${safe(item)}</span>`).join('')}</section><section><h4>Quality review</h4>${(proposal.quality_flags.length?proposal.quality_flags:['No missing-production flags in this pass']).map(item=>`<span>${safe(item)}</span>`).join('')}</section></div><div class="visual-locks">${proposal.continuity_checks.map(item=>`<span>CHECK · ${safe(item)}</span>`).join('')}</div><div class="crew-action-buttons"><button id="approve-edit" class="primary" type="button">Approve edit${action.payload.request.render_review?' & render review':''}</button><button id="reject-edit" type="button">Reject</button></div></article>`;
  document.querySelector('#approve-edit').onclick=async()=>{result.innerHTML='<div class="render-progress">Applying the edit and preparing the requested review master…</div>';renderEditorAction(await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'}));};
  document.querySelector('#reject-edit').onclick=async()=>renderEditorAction(await api(`/api/crew-actions/${action.id}/reject`,{method:'POST'}));
}

async function openShotPlanner(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  if (!generationProviders.length) generationProviders = (await api('/api/generation/providers')).providers;
  const projectSelect = document.querySelector('#shot-project');
  projectSelect.innerHTML = options(projects.map(project => ({id:String(project.id),label:project.title})), String(projectId || projects[0].id));
  projectSelect.onchange = () => { activeShotId = null; renderShotTree(Number(projectSelect.value)); hideShotEditor(); };
  renderShotTree(Number(projectSelect.value));
  hideShotEditor();
  openWorkspace(shotDialog);
}

function currentShotProject() {
  return projects.find(project => project.id === Number(document.querySelector('#shot-project').value));
}

async function askDirector() {
  const projectId=Number(document.querySelector('#shot-project').value), result=document.querySelector('#director-ai-result');
  const payload={objective:document.querySelector('#director-objective').value,shots_per_beat:Number(document.querySelector('#director-coverage').value),pacing:document.querySelector('#director-pacing').value,provider:document.querySelector('#director-provider').value};
  result.innerHTML='<div class="render-progress">Director is planning scenes, coverage, performances, and continuity…</div>';
  try { renderDirectorAction(await api(`/api/projects/${projectId}/crew/director/propose`,{method:'POST',body:JSON.stringify(payload)})); }
  catch(error) { result.innerHTML=`<div class="job-error">${safe(error.message)}</div>${error.message.includes('Deploy the Director')?'<button id="deploy-director-here" type="button">Deploy Director for this production</button>':''}`;const deploy=document.querySelector('#deploy-director-here');if(deploy)deploy.onclick=async()=>{await api(`/api/projects/${projectId}/crew/deploy`,{method:'POST',body:JSON.stringify({roles:['director'],autonomy:'propose'})});await askDirector();}; }
}

function renderDirectorAction(action) {
  const result=document.querySelector('#director-ai-result'), proposal=action.payload?.proposal;
  if(action.status==='failed'){result.innerHTML=`<div class="job-error">${safe(action.error)}</div>`;return;}
  if(action.status==='rejected'){result.innerHTML='<div class="crew-empty">Director proposal rejected. Existing scenes and shots were not changed.</div>';return;}
  if(action.status==='completed'){const data=action.result;result.innerHTML=`<div class="director-applied">Director plan applied non-destructively · ${data.created_scenes} scenes and ${data.created_shots} shots added · ${data.updated_scenes} scenes and ${data.updated_shots} shots updated${data.timeline_needs_rebuild?' · timeline marked for rebuild':''}.</div>`;loadProjects().then(()=>renderShotTree(action.project_id));return;}
  if(!proposal){result.innerHTML='<div class="job-error">Director proposal is unavailable.</div>';return;}
  const shotCount=proposal.scenes.reduce((total,scene)=>total+scene.shots.length,0);
  result.innerHTML=`<article class="director-proposal"><header><div><p class="eyebrow">PROPOSED DIRECTING PACKAGE</p><h3>${proposal.scenes.length} scenes · ${shotCount} shots · ${proposal.estimated_duration_seconds.toFixed(1)}s skeleton</h3></div><span>Awaiting approval</span></header><p>${safe(proposal.approach)}</p><div class="director-scenes">${proposal.scenes.map(scene=>`<section><h4>${scene.position} · ${safe(scene.title)}</h4><p>${safe(scene.dramatic_goal)}</p><div>${scene.shots.map(shot=>`<span><b>${shot.position} · ${safe(shot.shot_size)}</b>${safe(shot.movement)} · ${shot.duration_seconds}s<small>${safe(shot.performance_intent)}</small></span>`).join('')}</div></section>`).join('')}</div><div class="director-rules">${proposal.continuity_rules.map(rule=>`<span>${safe(rule)}</span>`).join('')}</div><div class="crew-action-buttons"><button id="approve-director-action" class="primary" type="button">Approve & apply coverage</button><button id="reject-director-action" type="button">Reject proposal</button></div></article>`;
  document.querySelector('#approve-director-action').onclick=async()=>renderDirectorAction(await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'}));
  document.querySelector('#reject-director-action').onclick=async()=>renderDirectorAction(await api(`/api/crew-actions/${action.id}/reject`,{method:'POST'}));
}

function findShot(project, shotId) {
  for (const scene of project?.scenes || []) { const shot = scene.shots.find(item => item.id === shotId); if (shot) return {scene,shot}; }
  return null;
}

function renderShotTree(projectId) {
  const project = projects.find(item => item.id === projectId);
  const expandButton = document.querySelector('#expand-story');
  expandButton.disabled = Boolean(project?.scenes.length);
  expandButton.textContent = project?.scenes.length ? 'Scenes already built' : 'Build from story';
  document.querySelector('#shot-tree').innerHTML = project?.scenes.length ? project.scenes.map(scene => `<section class="scene-group"><h4>${scene.position} · ${safe(scene.title)}</h4>${scene.shots.map(shot => `<button type="button" class="shot-item ${activeShotId === shot.id ? 'active' : ''}" data-shot-id="${shot.id}"><b>${shot.position}. ${safe(shot.title)}</b>${shot.duration_seconds}s · ${shot.plan ? safe(shot.plan.camera.shot_size || 'planned') : 'unplanned'}</button>`).join('')}</section>`).join('') : '<div class="empty">No scenes yet. Develop the story, then build its initial shots.</div>';
  document.querySelectorAll('[data-shot-id]').forEach(button => button.onclick = () => selectShot(projectId, Number(button.dataset.shotId)));
}

function hideShotEditor() {
  document.querySelector('#shot-editor-empty').style.display = 'block';
  document.querySelector('#shot-form').style.display = 'none';
}

function selectShot(projectId, shotId) {
  const project = projects.find(item => item.id === projectId);
  const found = findShot(project, shotId);
  if (!found) return;
  activeShotId = shotId;
  const {shot} = found; const plan = shot.plan || {character_ids:[],camera:{}}; const form = document.querySelector('#shot-form');
  form.elements.shot_title.value = shot.title;
  form.elements.shot_duration.value = shot.duration_seconds;
  form.elements.shot_description.value = shot.description;
  form.elements.shot_location.innerHTML = `<option value="">No location assigned</option>${options(project.locations.map(location => ({id:String(location.id),label:location.name})), String(plan.location_id || ''))}`;
  form.elements.shot_location.value = plan.location_id || '';
  document.querySelector('#shot-characters').innerHTML = project.characters.length ? project.characters.map(character => `<label class="chip"><input type="checkbox" name="shot_character" value="${character.id}" ${plan.character_ids.includes(character.id) ? 'checked' : ''}><span>${safe(character.name)}</span></label>`).join('') : '<span class="form-intro">Create characters before assigning them to shots.</span>';
  form.elements.shot_action.value = plan.action || shot.description;
  form.elements.shot_dialogue.value = plan.dialogue || '';
  form.elements.shot_lighting.value = plan.lighting || '';
  form.elements.camera_size.value = plan.camera.shot_size || 'wide';
  form.elements.camera_angle.value = plan.camera.angle || 'eye level';
  form.elements.camera_lens.value = plan.camera.lens || '35mm';
  form.elements.camera_movement.value = plan.camera.movement || 'locked';
  form.elements.camera_composition.value = plan.camera.composition || '';
  form.elements.camera_focus.value = plan.camera.focus || '';
  form.elements.shot_continuity.value = plan.continuity_notes || '';
  document.querySelector('#shot-editor-empty').style.display = 'none'; form.style.display = 'block';
  renderShotTree(projectId);
  if (shot.plan) renderShotPlan(shot.plan); else document.querySelector('#shot-result').innerHTML = '';
}

function collectShotPlan(form) {
  return {location_id:form.elements.shot_location.value ? Number(form.elements.shot_location.value) : null, character_ids:[...document.querySelectorAll('[name="shot_character"]:checked')].map(input => Number(input.value)), action:form.elements.shot_action.value, dialogue:form.elements.shot_dialogue.value, camera:{shot_size:form.elements.camera_size.value, angle:form.elements.camera_angle.value, lens:form.elements.camera_lens.value, movement:form.elements.camera_movement.value, composition:form.elements.camera_composition.value, focus:form.elements.camera_focus.value}, lighting:form.elements.shot_lighting.value, continuity_notes:form.elements.shot_continuity.value};
}

function renderShotPlan(plan) {
  const providerOptions = generationProviders.filter(provider => provider.id !== 'farm').map(provider => `<option value="${safe(provider.id)}" ${provider.id === 'mock' ? 'selected' : ''}>${safe(provider.label)}${provider.ready ? '' : ' · setup required'}</option>`).join('');
  document.querySelector('#shot-result').innerHTML = `<div class="shot-prompt"><b>STORYBOARD PROMPT · PLAN V${plan.version}</b>${safe(plan.storyboard_prompt)}</div><div class="storyboard-actions"><select id="storyboard-provider" aria-label="Storyboard provider">${providerOptions}</select><button type="button" id="generate-storyboard">Generate storyboard frame</button></div><div id="storyboard-result"></div>`;
  document.querySelector('#generate-storyboard').onclick = generateStoryboard;
}

async function generateStoryboard() {
  if (!activeShotId) return;
  const button = document.querySelector('#generate-storyboard'); button.disabled = true; button.textContent = 'Generating…';
  try { renderStoryboardJob(await api(`/api/shots/${activeShotId}/storyboard`, {method:'POST',body:JSON.stringify({provider:document.querySelector('#storyboard-provider').value})})); }
  catch (error) { document.querySelector('#storyboard-result').innerHTML = `<div class="job-error">${safe(error.message)}</div>`; }
  finally { button.disabled = false; button.textContent = 'Generate storyboard frame'; }
}

function renderStoryboardJob(job) {
  const result = document.querySelector('#storyboard-result');
  if (job.status === 'failed') { result.innerHTML = `<div class="job-error">${safe(job.error)}</div>`; return; }
  if (job.assets.length) { const asset = job.assets[0]; result.innerHTML = `<div class="storyboard-preview"><img src="${safe(asset.uri)}" alt="Generated storyboard for the selected shot"></div><div class="generation-actions"><small>${safe(job.provider)} · frame v${asset.version} · job ${job.id}</small></div>`; return; }
  result.innerHTML = `<div class="storyboard-actions"><small>${safe(job.provider)} job ${job.external_id || job.id} is ${safe(job.status)}.</small>${job.provider === 'comfyui' ? `<button type="button" data-sync-storyboard="${job.id}">Check result</button>` : ''}</div>`;
  const sync = document.querySelector('[data-sync-storyboard]'); if (sync) sync.onclick = async () => renderStoryboardJob(await api(`/api/storyboard-jobs/${job.id}/sync`, {method:'POST'}));
}

async function openRenderFarm() {
  openWorkspace(renderDialog);
  await refreshRenderFarm();
}

async function refreshRenderFarm() {
  const farm = await api('/api/render-farm/status');
  const segments = farm.master_segments || [];
  const queued = farm.jobs.filter(job => job.status === 'queued').length + segments.filter(segment => segment.status === 'queued').length;
  const running = farm.jobs.filter(job => job.status === 'running').length + segments.filter(segment => ['leased','rendering'].includes(segment.status)).length;
  const online = farm.workers.filter(worker => ['online','busy'].includes(worker.status)).length;
  document.querySelector('#farm-summary').innerHTML = `<div class="farm-stat"><b>${online}</b><span>WORKERS ONLINE</span></div><div class="farm-stat"><b>${running}</b><span>JOBS RENDERING</span></div><div class="farm-stat"><b>${queued}</b><span>JOBS QUEUED</span></div>`;
  document.querySelector('#farm-workers').innerHTML = farm.workers.length ? farm.workers.map(worker => { const gpu = worker.capabilities.gpu || worker.capabilities.gpus?.map(item => item.name).join(', ') || 'CPU worker'; const vram = worker.capabilities.vram_gb ? `${worker.capabilities.vram_gb} GB VRAM` : ''; return `<article class="worker-card"><header><div><b>${safe(worker.name)}</b><br><small>${safe(worker.hostname)}</small></div><span class="worker-status ${safe(worker.status)}">${safe(worker.status)}</span></header><p>${safe(gpu)} ${safe(vram)}</p><small>${worker.supported_tasks.map(safe).join(' · ')}</small></article>`; }).join('') : '<div class="empty">No render workers enrolled yet.</div>';
  const characterJobs = farm.jobs.map(job => `<div class="farm-job"><b>#${job.id}</b><span>Character ${job.character_id}</span><span>${safe(job.status)}</span><span>${job.assets} assets</span></div>`);
  const masterJobs = segments.map(segment => `<div class="farm-job"><b>S${segment.id}</b><span>Master ${segment.export_id} · segment ${segment.position}</span><span>${safe(segment.status)}</span><span>${segment.attempts} attempt${segment.attempts === 1 ? '' : 's'}</span></div>`);
  document.querySelector('#farm-jobs').innerHTML = characterJobs.length || masterJobs.length ? [...masterJobs, ...characterJobs].join('') : '<div class="empty">No farm jobs yet. Queue a character render or segmented master export.</div>';
}

async function openTimeline(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  const select = document.querySelector('#timeline-project');
  select.innerHTML = options(projects.map(project => ({id:String(project.id),label:project.title})), String(projectId || projects[0].id));
  select.onchange = () => { document.querySelector('#editor-result').innerHTML=''; loadTimeline(Number(select.value)); };
  document.querySelector('#editor-result').innerHTML='';
  openWorkspace(timelineDialog);
  await loadTimeline(Number(select.value));
}

async function loadTimeline(projectId) {
  stopMasterExportPolling();
  activeClipId = null;
  activeMasterExport = null; document.querySelector('#segmented-export-result').innerHTML='';
  try { activeTimeline = await api(`/api/projects/${projectId}/timeline`); renderTimeline(); try { renderSegmentedExport(await api(`/api/timelines/${activeTimeline.id}/master-exports/latest`)); } catch {} }
  catch { activeTimeline = null; document.querySelector('#timeline-summary').innerHTML = '<span>No edit assembled yet.</span>'; document.querySelector('#timeline-clips').innerHTML = '<div class="empty">Build the timeline from the current shot plan.</div>'; hideClipEditor(); }
}

function renderTimeline() {
  if (!activeTimeline) return;
  const minutes = Math.floor(activeTimeline.total_duration_seconds / 60); const seconds = Math.round(activeTimeline.total_duration_seconds % 60);
  document.querySelector('#timeline-summary').innerHTML = `<b>${activeTimeline.clips.length} CLIPS</b><span>${minutes}:${String(seconds).padStart(2,'0')} runtime</span><span>${activeTimeline.fps} fps</span><span>${activeTimeline.width} × ${activeTimeline.height}</span><span>${safe(activeTimeline.status)}</span>`;
  document.querySelector('#timeline-clips').innerHTML = activeTimeline.clips.map(clip => `<button type="button" class="timeline-clip ${activeClipId === clip.id ? 'active' : ''}" data-clip-id="${clip.id}">${clip.storyboard_uri ? `<img class="timeline-thumb" src="${safe(clip.storyboard_uri)}" alt="">` : '<span class="timeline-thumb timeline-placeholder">FRAME</span>'}<span><b>${clip.position}. ${safe(clip.shot_title)}</b><small>${safe(clip.scene_title)}${clip.motion_uri?' · MOTION':''}</small></span><small>${clip.duration_seconds.toFixed(1)}s<br>${safe(clip.transition)}</small></button>`).join('');
  document.querySelectorAll('[data-clip-id]').forEach(button => button.onclick = () => selectClip(Number(button.dataset.clipId)));
  document.querySelectorAll('[data-clip-id]').forEach(button=>{button.draggable=true;button.ondragstart=event=>{draggedTimelineClipId=Number(button.dataset.clipId);button.classList.add('dragging');event.dataTransfer.effectAllowed='move';};button.ondragend=()=>{button.classList.remove('dragging');draggedTimelineClipId=null;};button.ondragover=event=>{event.preventDefault();button.classList.add('drag-target');};button.ondragleave=()=>button.classList.remove('drag-target');button.ondrop=event=>{event.preventDefault();button.classList.remove('drag-target');dropTimelineClip(Number(button.dataset.clipId));};});
  if (activeClipId) selectClip(activeClipId, false);
}

async function dropTimelineClip(targetId) {
  if(!draggedTimelineClipId||draggedTimelineClipId===targetId)return;const clips=[...activeTimeline.clips],from=clips.findIndex(item=>item.id===draggedTimelineClipId),to=clips.findIndex(item=>item.id===targetId);if(from<0||to<0)return;const [moved]=clips.splice(from,1);clips.splice(to,0,moved);activeClipId=moved.id;activeTimeline=await api(`/api/timelines/${activeTimeline.id}/clips/order`,{method:'PUT',body:JSON.stringify({clip_ids:clips.map(item=>item.id)})});renderTimeline();
}

function hideClipEditor() { document.querySelector('#clip-empty').style.display='block'; document.querySelector('#clip-form').style.display='none'; }

function selectClip(clipId, rerender=true) {
  const clip = activeTimeline?.clips.find(item => item.id === clipId); if (!clip) return;
  activeClipId = clipId; const form = document.querySelector('#clip-form');
  document.querySelector('#clip-empty').style.display='none'; form.style.display='block';
  document.querySelector('#clip-scene').textContent = clip.scene_title; document.querySelector('#clip-title').textContent = clip.shot_title;
  document.querySelector('#clip-frame').innerHTML = clip.storyboard_uri ? `<img src="${safe(clip.storyboard_uri)}" alt="Storyboard frame for ${safe(clip.shot_title)}">` : '';
  form.elements.clip_duration.value = clip.duration_seconds; form.elements.clip_transition.value = clip.transition; form.elements.clip_transition_duration.value = clip.transition_duration; form.elements.clip_audio_cue.value = clip.audio_cue;
  const index = activeTimeline.clips.findIndex(item => item.id === clipId); document.querySelector('#clip-earlier').disabled=index===0; document.querySelector('#clip-later').disabled=index===activeTimeline.clips.length-1;
  if (rerender) renderTimeline();
}

async function moveClip(delta) {
  const clips = [...activeTimeline.clips]; const index = clips.findIndex(clip => clip.id === activeClipId); const next=index+delta; if(index<0||next<0||next>=clips.length)return;
  [clips[index],clips[next]]=[clips[next],clips[index]];
  activeTimeline = await api(`/api/timelines/${activeTimeline.id}/clips/order`,{method:'PUT',body:JSON.stringify({clip_ids:clips.map(clip=>clip.id)})}); renderTimeline();
}

function stopMasterExportPolling() {
  if (masterExportPollTimer) clearInterval(masterExportPollTimer);
  masterExportPollTimer = null;
}

function startMasterExportPolling() {
  stopMasterExportPolling();
  if (!activeMasterExport || !['farm-queued','farm-rendering','assembling'].includes(activeMasterExport.status)) return;
  masterExportPollTimer = setInterval(async () => {
    if (!timelineDialog.hasAttribute('open') || !activeMasterExport) return;
    try { renderSegmentedExport(await api(`/api/master-exports/${activeMasterExport.id}`)); } catch {}
  }, 2500);
}

function renderSegmentedExport(job) {
  activeMasterExport = job;
  const ready = job.completed_segments === job.total_segments && job.total_segments > 0;
  const distributed = ['farm-queued','farm-rendering','assembling'].includes(job.status);
  const stateText = {
    'farm-queued':'Waiting for an available render worker',
    'farm-rendering':'Render farm processing segments automatically',
    'assembling':'All segments verified · assembling the final master',
    'segments-ready':'All segments ready for assembly',
    'needs-attention':'Export needs attention before it can continue',
    'completed':'Final master completed',
    'planned':'Export plan ready',
  }[job.status] || job.status;
  let actions = '';
  if (distributed) actions = '<button type="button" data-export-action="refresh">Refresh status</button>';
  else if (job.status !== 'completed') actions = `<button type="button" data-export-action="dispatch">Send to render farm</button><button type="button" data-export-action="run-next">Run next locally</button><button type="button" data-export-action="run-all">Run all locally</button><button type="button" data-export-action="resume">Verify & resume</button>${ready?'<button type="button" data-export-action="assemble">Assemble master</button>':''}`;
  document.querySelector('#segmented-export-result').innerHTML=`<section class="segment-export"><header><div><p class="eyebrow">DISTRIBUTED MASTER · JOB ${job.id}</p><b>${safe(job.profile.toUpperCase())} · ${job.width} × ${job.height} · ${job.fps} fps</b></div><span>${job.completed_segments}/${job.total_segments} segments · ${job.progress_percent}%</span></header><div class="export-state ${safe(job.status)}"><i></i><span>${safe(stateText)}</span></div><div class="segment-progress"><i style="width:${job.progress_percent}%"></i></div><div class="segment-list">${job.segments.map(segment=>`<span class="segment-chip ${safe(segment.status)}"><b>${segment.position}</b> clips ${segment.manifest.clip_start}–${segment.manifest.clip_end}<small>${safe(segment.status)}${segment.checksum_sha256?' · '+safe(segment.checksum_sha256.slice(0,8)):''}</small></span>`).join('')}</div>${actions?`<div class="segment-actions">${actions}</div>`:''}${job.final_uri?`<div class="master-manifest"><b>FINAL MASTER READY</b><span>All segments passed integrity checks and were assembled automatically.</span><a href="${safe(job.final_uri)}" download>Download final master</a></div>`:''}${job.error?`<div class="job-error">${safe(job.error)}</div>`:''}</section>`;
  document.querySelectorAll('[data-export-action]').forEach(button=>button.onclick=()=>runExportAction(button.dataset.exportAction));
  if (distributed) startMasterExportPolling(); else stopMasterExportPolling();
}

async function runExportAction(action) {
  if (!activeMasterExport) return;
  const panel = document.querySelector('#segmented-export-result');
  panel.querySelectorAll('button').forEach(button=>button.disabled=true);
  const labels = {'run-next':'Rendering next segment…','run-all':'Rendering remaining segments…','resume':'Verifying checksums…','assemble':'Assembling master…','dispatch':'Sending segments to the render farm…','refresh':'Refreshing farm progress…'};
  panel.insertAdjacentHTML('beforeend',`<div class="render-progress">${labels[action]}</div>`);
  try {
    const job = action === 'refresh' ? await api(`/api/master-exports/${activeMasterExport.id}`) : await api(`/api/master-exports/${activeMasterExport.id}/${action}`,{method:'POST'});
    renderSegmentedExport(job);
  } catch(error) { panel.insertAdjacentHTML('beforeend',`<div class="job-error">${safe(error.message)}</div>`); }
}

async function openCrewStudio(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  const select=document.querySelector('#crew-project');
  select.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(projectId||projects[0].id));
  select.onchange=()=>loadCrew(Number(select.value));
  openWorkspace(crewDialog);
  await loadCrew(Number(select.value));
}

async function loadCrew(projectId) {
  const [roles, crew, briefing, workflow]=await Promise.all([api('/api/crew/roles'),api(`/api/projects/${projectId}/crew`),api(`/api/projects/${projectId}/crew/briefing`),api(`/api/projects/${projectId}/producer/workflow`).catch(()=>null)]);
  crewRoles=roles; activeCrew=crew; activeProducerWorkflow=workflow; renderCrew(briefing);renderProducerWorkflow(workflow);
}

function renderProducerWorkflowLegacy(workflow) {
  const panel=document.querySelector('#producer-workflow'), status=document.querySelector('#producer-status'), advance=document.querySelector('#advance-producer');
  if(!workflow){status.textContent='Not started';panel.innerHTML='<div class="crew-empty">Set a production goal, deploy the departments you want, then start a resumable workflow.</div>';advance.disabled=true;document.querySelector('#start-producer').textContent='Start workflow';return;}
  status.textContent=workflow.status.replaceAll('_',' ');document.querySelector('#producer-objective').value=workflow.objective;document.querySelector('#producer-provider').value=workflow.settings.provider||'simulation';document.querySelector('#producer-review-profile').value=workflow.settings.review_profile||'preview';document.querySelector('#producer-motion-previews').checked=workflow.settings.render_motion_previews!==false;document.querySelector('#producer-final-review').checked=workflow.settings.render_final_review!==false;document.querySelector('#start-producer').textContent='Update workflow';
  panel.innerHTML=`<div class="producer-stages">${workflow.stages.map((stage,index)=>`<article class="producer-stage ${safe(stage.status)}"><span>${stage.status==='complete'?'✓':String(index+1).padStart(2,'0')}</span><div><b>${safe(stage.label)}</b><small>${safe(stage.progress)}</small><p>${safe(stage.reason)}</p></div><em>${safe(stage.status.replaceAll('_',' '))}</em></article>`).join('')}</div>`;
  const current=workflow.stages.find(stage=>stage.key===workflow.current_stage);advance.disabled=workflow.status!=='active'||current?.status!=='ready';advance.textContent=workflow.status==='complete'?'Production complete':current?.status==='awaiting_approval'?'Awaiting approval':current?.status==='ready'?`Advance · ${current.label}`:'Resolve current blocker';
}

async function saveProducerWorkflow() {
  const projectId=activeCrew.project_id;const payload={objective:document.querySelector('#producer-objective').value,provider:document.querySelector('#producer-provider').value,render_motion_previews:document.querySelector('#producer-motion-previews').checked,render_final_review:document.querySelector('#producer-final-review').checked,review_profile:document.querySelector('#producer-review-profile').value};
  activeProducerWorkflow=await api(`/api/projects/${projectId}/producer/workflow`,{method:'POST',body:JSON.stringify(payload)});renderProducerWorkflow(activeProducerWorkflow);
}

async function advanceProducerWorkflow() {
  if(!activeProducerWorkflow)return;const button=document.querySelector('#advance-producer');button.disabled=true;button.textContent='Coordinating next stage…';try{activeProducerWorkflow=await api(`/api/producer-workflows/${activeProducerWorkflow.id}/advance`,{method:'POST'});await loadCrew(activeCrew.project_id);}catch(error){renderProducerWorkflow(activeProducerWorkflow);document.querySelector('#producer-workflow').insertAdjacentHTML('beforeend',`<div class="job-error">${safe(error.message)}</div>`);}
}

function renderCrewLegacy(briefing) {
  document.querySelector('#crew-briefing').innerHTML=`<p class="eyebrow">AI ASSISTANT BRIEFING</p><h3>${safe(briefing.headline)}</h3><div class="crew-suggestions">${briefing.suggestions.map(item=>`<span><b>${safe(crewRoles.find(role=>role.id===item.role)?.name||item.role)}</b> · ${safe(item.reason)}</span>`).join('')||'<span>No blocking production gaps detected.</span>'}</div>`;
  document.querySelector('#crew-roles').innerHTML=crewRoles.map(role=>{
    const assignment=activeCrew.assignments.find(item=>item.role===role.id);
    const autonomy=assignment?.autonomy||'propose';
    return `<article class="crew-role ${assignment?.enabled?'deployed':''}" data-role-card="${safe(role.id)}"><header><div><h3>${safe(role.name)}</h3><small>${assignment?.enabled?'DEPLOYED':'AVAILABLE'}</small></div><input type="checkbox" data-crew-role="${safe(role.id)}" ${assignment?.enabled?'checked':''} aria-label="Deploy ${safe(role.name)}"></header><p>${safe(role.description)}</p><small>${role.capabilities.map(safe).join(' · ')}</small><label>Autonomy<select data-role-autonomy="${safe(role.id)}"><option value="assist" ${autonomy==='assist'?'selected':''}>Assist only</option><option value="propose" ${autonomy==='propose'?'selected':''}>Propose for approval</option><option value="execute" ${autonomy==='execute'?'selected':''}>Execute automatically</option></select></label><label>Standing direction<textarea data-role-instructions="${safe(role.id)}" placeholder="What should this bot always protect or prioritize?">${safe(assignment?.instructions||'')}</textarea></label>${assignment?`<button type="button" data-save-role="${assignment.id}">Save role settings</button>`:''}</article>`;
  }).join('');
  document.querySelectorAll('[data-save-role]').forEach(button=>button.onclick=()=>saveCrewRole(Number(button.dataset.saveRole)));
  document.querySelector('#crew-actions').innerHTML=activeCrew.actions.length?activeCrew.actions.map(action=>`<article class="crew-action"><div><b>${safe(action.title)}</b><small>${safe(action.summary)}</small>${action.error?`<div class="job-error">${safe(action.error)}</div>`:''}${action.status==='proposed'?`<div class="crew-action-buttons"><button data-crew-action="approve" data-action-id="${action.id}" class="primary">Approve</button><button data-crew-action="reject" data-action-id="${action.id}">Reject</button></div>`:''}</div><span class="status">${safe(action.status)}</span></article>`).join(''):'<div class="crew-empty">Crew proposals, approvals, automatic work, and failures will appear here.</div>';
  document.querySelectorAll('[data-crew-action]').forEach(button=>button.onclick=()=>reviewCrewAction(button.dataset.crewAction,Number(button.dataset.actionId)));
}

function crewMode() {
  const enabled=activeCrew.assignments.filter(item=>item.enabled);if(!enabled.length)return'manual';if(enabled.length===crewRoles.length&&enabled.every(item=>item.autonomy==='execute'))return'autopilot';if(enabled.length===crewRoles.length&&enabled.every(item=>item.autonomy==='propose'))return'guided';return'custom';
}

function renderProducerWorkflow(workflow) {
  const panel=document.querySelector('#producer-workflow'),status=document.querySelector('#producer-status'),advance=document.querySelector('#advance-producer'),start=document.querySelector('#start-producer');
  if(!workflow){status.textContent='Ready';panel.innerHTML='<div class="producer-next"><i>01</i><div><b>Start when your crew is ready</b><small>Kizuna will prepare one step, then pause for review.</small></div></div>';advance.disabled=true;start.textContent='Start guided workflow';return;}
  status.textContent=workflow.status.replaceAll('_',' ');document.querySelector('#producer-objective').value=workflow.objective;document.querySelector('#producer-provider').value=workflow.settings.provider||'simulation';document.querySelector('#producer-review-profile').value=workflow.settings.review_profile||'preview';document.querySelector('#producer-motion-previews').checked=workflow.settings.render_motion_previews!==false;document.querySelector('#producer-final-review').checked=workflow.settings.render_final_review!==false;start.textContent='Update workflow';
  const current=workflow.stages.find(stage=>stage.key===workflow.current_stage),complete=workflow.stages.filter(stage=>stage.status==='complete').length;panel.innerHTML=`<div class="producer-progress" aria-label="Production workflow">${workflow.stages.map((stage,index)=>`<span class="${safe(stage.status)}"><i>${stage.status==='complete'?'&#10003;':index+1}</i>${safe(stage.label)}</span>`).join('')}</div><div class="producer-next"><i>${String(Math.min(complete+1,workflow.stages.length)).padStart(2,'0')}</i><div><b>${safe(current?.label||'Production complete')}</b><small>${safe(current?.reason||'Every planned stage is complete.')}</small></div><em>${safe(current?.status?.replaceAll('_',' ')||workflow.status)}</em></div>`;
  advance.disabled=workflow.status!=='active'||current?.status!=='ready';advance.textContent=workflow.status==='complete'?'Production complete':current?.status==='awaiting_approval'?'Review pending work':current?.status==='ready'?`Continue to ${current.label}`:'Resolve current blocker';
}

function renderCrew(briefing) {
  const icons={writer:'W',director:'D',character_designer:'C',background_artist:'B',animator:'A',sound_producer:'S',editor:'E'},mode=crewMode(),pending=activeCrew.actions.filter(action=>action.status==='proposed'),history=activeCrew.actions.filter(action=>action.status!=='proposed');
  document.querySelector('#crew-mode-status').textContent={guided:'Guided',autopilot:'Autopilot',manual:'Manual',custom:'Custom'}[mode];document.querySelectorAll('[data-crew-preset]').forEach(button=>button.classList.toggle('active',button.dataset.crewPreset===mode));
  document.querySelector('#crew-briefing').innerHTML=`<i>${briefing.suggestions.length?'!':'&#10003;'}</i><div><b>${safe(briefing.headline)}</b><small>${safe(briefing.suggestions[0]?.reason||'Nothing is blocking the next creative pass.')}</small></div>`;
  document.querySelector('#crew-roles').innerHTML=crewRoles.map(role=>{const assignment=activeCrew.assignments.find(item=>item.role===role.id),autonomy=assignment?.autonomy||'propose';return `<article class="crew-role ${assignment?.enabled?'deployed':''}" data-role-card="${safe(role.id)}"><header><i>${icons[role.id]||'AI'}</i><div><h3>${safe(role.name)}</h3><small>${assignment?.enabled?'ON':'OFF'}</small></div><label class="crew-switch"><input type="checkbox" data-crew-role="${safe(role.id)}" ${assignment?.enabled?'checked':''} aria-label="Use ${safe(role.name)}"><span></span></label></header><p>${safe(role.description)}</p><details class="advanced-settings crew-role-advanced"><summary>Advanced</summary><div><label>How independently?<select data-role-autonomy="${safe(role.id)}"><option value="assist" ${autonomy==='assist'?'selected':''}>Only when asked</option><option value="propose" ${autonomy==='propose'?'selected':''}>Ask before changing anything</option><option value="execute" ${autonomy==='execute'?'selected':''}>Work automatically</option></select></label><label>Always remember<textarea data-role-instructions="${safe(role.id)}" placeholder="Optional creative rule">${safe(assignment?.instructions||'')}</textarea></label>${assignment?`<button type="button" data-save-role="${assignment.id}">Save department settings</button>`:''}</div></details></article>`;}).join('');
  document.querySelectorAll('[data-save-role]').forEach(button=>button.onclick=()=>saveCrewRole(Number(button.dataset.saveRole)));
  const actionCard=action=>`<article class="crew-action"><div><b>${safe(action.title)}</b><small>${safe(action.summary)}</small>${action.error?`<div class="job-error">${safe(action.error)}</div>`:''}${action.status==='proposed'?`<div class="crew-action-buttons"><button data-crew-action="approve" data-action-id="${action.id}" class="primary">Approve</button><button data-crew-action="reject" data-action-id="${action.id}">Reject</button></div>`:''}</div><span class="status">${safe(action.status)}</span></article>`;
  document.querySelector('#crew-actions').innerHTML=`${pending.length?`<div class="approval-summary"><b>${pending.length} decision${pending.length===1?'':'s'} waiting</b><small>Approve only the work you want to keep.</small></div>${pending.map(actionCard).join('')}`:'<div class="crew-empty">Nothing needs your attention right now.</div>'}${history.length?`<details class="advanced-settings crew-history"><summary>Recent activity &middot; ${history.length}</summary><div>${history.map(actionCard).join('')}</div></details>`:''}`;
  document.querySelectorAll('[data-crew-action]').forEach(button=>button.onclick=()=>reviewCrewAction(button.dataset.crewAction,Number(button.dataset.actionId)));
}

async function applyCrewPreset(preset) {
  if(preset==='custom'){document.querySelector('#crew-roles').scrollIntoView({behavior:'smooth',block:'start'});return;}const roles=preset==='manual'?[]:crewRoles.map(role=>role.id),autonomy=preset==='autopilot'?'execute':'propose',status=document.querySelector('#crew-mode-status');status.textContent='Saving...';document.querySelector('#crew-default-autonomy').value=autonomy;await api(`/api/projects/${activeCrew.project_id}/crew/deploy`,{method:'POST',body:JSON.stringify({roles,autonomy})});await loadCrew(activeCrew.project_id);
}

async function saveCrewRole(assignmentId) {
  const assignment=activeCrew.assignments.find(item=>item.id===assignmentId), role=assignment.role;
  await api(`/api/crew-assignments/${assignmentId}`,{method:'PUT',body:JSON.stringify({enabled:document.querySelector(`[data-crew-role="${role}"]`).checked,autonomy:document.querySelector(`[data-role-autonomy="${role}"]`).value,instructions:document.querySelector(`[data-role-instructions="${role}"]`).value})});
  await loadCrew(activeCrew.project_id);
}

async function deploySelectedCrew() {
  const roles=[...document.querySelectorAll('[data-crew-role]:checked')].map(input=>input.dataset.crewRole);
  const button=document.querySelector('#deploy-crew');button.disabled=true;button.textContent='Saving...';await api(`/api/projects/${activeCrew.project_id}/crew/deploy`,{method:'POST',body:JSON.stringify({roles,autonomy:document.querySelector('#crew-default-autonomy').value})});
  await loadCrew(activeCrew.project_id);
  button.disabled=false;button.textContent='Save custom crew';
}

async function reviewCrewAction(decision, actionId) {
  await api(`/api/crew-actions/${actionId}/${decision}`,{method:'POST'});
  await loadCrew(activeCrew.project_id);
}

async function openAudioStudio(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  const select=document.querySelector('#audio-project'); select.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(projectId||projects[0].id));
  select.onchange=()=>loadAudioStudio(Number(select.value)); openWorkspace(audioDialog); await loadAudioStudio(Number(select.value));
}

async function loadAudioStudio(projectId) {
  activeAudioCueId=null;
  try { activeAudioTimeline=await api(`/api/projects/${projectId}/timeline`); activeAudioStudio=await api(`/api/projects/${projectId}/audio-studio`); renderAudioStudio(projectId); }
  catch(error) { activeAudioTimeline=null; activeAudioStudio=null; document.querySelector('#audio-summary').innerHTML='<span>Build the picture timeline before sound work begins.</span>'; document.querySelector('#audio-tracks').innerHTML=`<div class="empty">${safe(error.message)}</div>`; document.querySelector('#cue-form').style.display='none'; document.querySelector('#cue-empty').style.display='block'; fillVoiceBible(projectId); }
}

function renderAudioStudioLegacy(projectId) {
  const cues=activeAudioStudio.tracks.flatMap(track=>track.cues); document.querySelector('#audio-summary').innerHTML=`<b>${activeAudioStudio.tracks.length} TRACKS</b><span>${cues.length} cues</span><span>${activeAudioStudio.total_duration_seconds.toFixed(1)}s picture lock</span>`;
  document.querySelector('#audio-tracks').innerHTML=activeAudioStudio.tracks.length?activeAudioStudio.tracks.map(track=>`<section class="track-group"><header class="track-head"><b>${safe(track.name)}</b><button type="button" data-new-cue="${track.id}">＋ Cue</button></header>${track.cues.length?track.cues.map(cue=>`<button type="button" class="cue-item ${activeAudioCueId===cue.id?'active':''}" data-cue-id="${cue.id}"><small>${cue.start_seconds.toFixed(1)}s</small><span><b>${safe(cue.text||cue.direction||'Untitled cue')}</b><small>${safe(cue.status)}</small></span><small>${cue.duration_seconds.toFixed(1)}s</small></button>`).join(''):'<div class="empty">No cues on this track.</div>'}</section>`).join(''):'<div class="empty">Initialize the standard production tracks.</div>';
  document.querySelectorAll('[data-new-cue]').forEach(button=>button.onclick=()=>newAudioCue(Number(button.dataset.newCue))); document.querySelectorAll('[data-cue-id]').forEach(button=>button.onclick=()=>selectAudioCue(Number(button.dataset.cueId)));
  fillVoiceBible(projectId);
}

function fillVoiceBible(projectId) {
  const project=projects.find(item=>item.id===projectId); const select=document.querySelector('#voice-character');
  select.innerHTML=project?.characters.length?options(project.characters.map(character=>({id:String(character.id),label:character.name})),select.value):'<option value="">Create a character first</option>';
  select.onchange=()=>fillVoiceProfile(Number(select.value)); fillVoiceProfile(Number(select.value));
}

function fillVoiceProfile(characterId) {
  const profile=activeAudioStudio?.voice_profiles.find(item=>item.character_id===characterId);
  document.querySelector('#voice-texture').value=profile?.texture||'clear and grounded'; document.querySelector('#voice-energy').value=profile?.energy||'restrained'; document.querySelector('#voice-pace').value=profile?.pace||1; document.querySelector('#voice-pitch').value=profile?.pitch||0; document.querySelector('#voice-direction').value=profile?.direction_notes||'';
  document.querySelector('#voice-provider').value=profile?.provider||'simulation'; document.querySelector('#voice-provider-id').value=profile?.provider_voice_id||'';
}

function findAudioCue(cueId) { for(const track of activeAudioStudio?.tracks||[]){const cue=track.cues.find(item=>item.id===cueId);if(cue)return {track,cue};} return null; }

function cueFormOptions(trackId, characterId) {
  const form=document.querySelector('#cue-form'); const project=projects.find(item=>item.id===activeAudioStudio.project_id);
  form.elements.cue_track.innerHTML=options(activeAudioStudio.tracks.map(track=>({id:String(track.id),label:track.name})),String(trackId));
  form.elements.cue_character.innerHTML='<option value="">No character / non-dialogue</option>'+options(project.characters.map(character=>({id:String(character.id),label:character.name})),String(characterId||'')); form.elements.cue_character.value=characterId||'';
}

function newAudioCue(trackId) {
  activeAudioCueId=null; const form=document.querySelector('#cue-form'); const track=activeAudioStudio.tracks.find(item=>item.id===trackId); const project=projects.find(item=>item.id===activeAudioStudio.project_id); const defaultCharacter=track?.kind==='dialogue'?project?.characters[0]?.id:null; document.querySelector('#cue-empty').style.display='none'; form.style.display='block'; document.querySelector('#cue-mode').textContent='NEW AUDIO CUE'; cueFormOptions(trackId,defaultCharacter); form.elements.cue_track.disabled=false; form.elements.cue_start.value=0; form.elements.cue_duration.value=2; form.elements.cue_text.value=''; form.elements.cue_direction.value=''; document.querySelector('#cue-result').innerHTML=''; renderAudioStudio(activeAudioStudio.project_id);
}

function selectAudioCue(cueId,rerender=true) {
  const found=findAudioCue(cueId);if(!found)return; activeAudioCueId=cueId; const {track,cue}=found; const form=document.querySelector('#cue-form'); document.querySelector('#cue-empty').style.display='none'; form.style.display='block'; document.querySelector('#cue-mode').textContent=`${track.name.toUpperCase()} CUE`; cueFormOptions(track.id,cue.character_id); form.elements.cue_track.disabled=true; form.elements.cue_start.value=cue.start_seconds; form.elements.cue_duration.value=cue.duration_seconds; form.elements.cue_text.value=cue.text; form.elements.cue_direction.value=cue.direction; renderCueResult(cue); if(rerender)renderAudioStudio(activeAudioStudio.project_id);
}

function renderCueResult(cue) {
  document.querySelector('#cue-result').innerHTML=`<div class="audio-actions"><button type="button" id="ask-sound-producer" class="primary">Ask Sound Producer</button><button type="button" id="generate-scratch">Generate timing slate</button><label class="audio-upload">Upload performance<input id="audio-file" type="file" accept=".wav,.mp3,.m4a,.ogg,audio/*"></label>${cue.uri?`<audio controls src="${safe(cue.uri)}"></audio>`:''}</div><div id="sound-producer-result"></div>${cue.uri?`<div class="sound-ready">${safe(cue.status)} · ${safe(cue.filename)}</div>`:''}`;
  document.querySelector('#ask-sound-producer').onclick=askSoundProducer; document.querySelector('#generate-scratch').onclick=generateScratchAudio; document.querySelector('#audio-file').onchange=uploadCueAudio;
}

async function generateScratchAudio() { if(!activeAudioCueId)return; const cue=await api(`/api/audio-cues/${activeAudioCueId}/generate-scratch`,{method:'POST'}); await refreshAudioAndSelect(cue.id); }
async function askSoundProducer() { if(!activeAudioCueId)return; const result=document.querySelector('#sound-producer-result');result.innerHTML='<div class="render-progress">Sound Producer is preparing the performance…</div>';try{const action=await api(`/api/audio-cues/${activeAudioCueId}/crew/generate-voice`,{method:'POST',body:JSON.stringify({provider:document.querySelector('#voice-provider').value,voice:document.querySelector('#voice-provider-id').value||null})});renderSoundAction(action);}catch(error){result.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;} }
function renderSoundAction(action) { const result=document.querySelector('#sound-producer-result');if(action.status==='proposed'){result.innerHTML=`<div class="crew-action"><div><b>${safe(action.title)}</b><small>${safe(action.summary)}</small><div class="crew-action-buttons"><button id="approve-sound-action" class="primary">Approve performance</button></div></div><span class="status">proposed</span></div>`;document.querySelector('#approve-sound-action').onclick=async()=>{const updated=await api(`/api/crew-actions/${action.id}/approve`,{method:'POST'});renderSoundAction(updated);if(updated.status==='completed')await refreshAudioAndSelect(activeAudioCueId);};}else if(action.status==='completed'){result.innerHTML='<div class="sound-ready">Sound Producer completed and placed the performance.</div>';}else{result.innerHTML=`<div class="job-error">${safe(action.error||action.status)}</div>`;} }
async function uploadCueAudio(event) { const file=event.target.files[0];if(!file||!activeAudioCueId)return; const response=await fetch(`/api/audio-cues/${activeAudioCueId}/upload?filename=${encodeURIComponent(file.name)}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream'},body:file}); if(!response.ok)throw new Error(await response.text()); const cue=await response.json(); await refreshAudioAndSelect(cue.id); }
async function refreshAudioAndSelect(cueId) { activeAudioStudio=await api(`/api/projects/${activeAudioStudio.project_id}/audio-studio`); renderAudioStudio(activeAudioStudio.project_id); selectAudioCue(cueId); }

async function openCompositor(projectId) {
  if(!projects.length)await loadProjects();if(!projects.length){projectDialog.showModal();return;} const select=document.querySelector('#compositor-project');select.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(projectId||projects[0].id));select.onchange=()=>loadCompositorStudio(Number(select.value));openWorkspace(compositorDialog);await loadCompositorStudio(Number(select.value));
}

async function loadCompositorStudio(projectId) {
  activeCompositorStudio=await api(`/api/projects/${projectId}/compositor`);activeComposition=null;activeCompositionLayerId=null;document.querySelector('#animator-result').innerHTML='';renderAssetReview();renderCompositorShots();document.querySelector('#composition-editor').style.display='none';document.querySelector('#composition-empty').style.display='block';document.querySelector('#layer-form').style.display='none';document.querySelector('#layer-empty').style.display='block';if(activeCompositorStudio.shots.length)await selectCompositorShot(activeCompositorStudio.shots[0].id);
}

function renderAssetReview() {
  const assets=activeCompositorStudio?.assets||[], groups=new Map();
  assets.forEach(asset=>{const key=`${asset.asset_type}:${asset.group_id}`;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(asset);});
  const counts={pending:assets.filter(item=>item.review_status==='pending').length,approved:assets.filter(item=>item.review_status==='approved').length,rejected:assets.filter(item=>item.review_status==='rejected').length};document.querySelector('#asset-review-summary').innerHTML=`<span>${counts.pending} pending</span><span>${counts.approved} approved</span><span>${counts.rejected} rejected</span>`;
  document.querySelector('#asset-review-groups').innerHTML=groups.size?[...groups.values()].map(items=>`<section class="asset-version-group"><header><div><b>${safe(items[0].name)}</b><small>${safe(items[0].asset_type)} · ${items.length} version${items.length===1?'':'s'}</small></div></header><div class="asset-version-grid">${items.sort((a,b)=>b.version-a.version).map(asset=>`<article class="asset-version ${asset.active?'active':''} ${safe(asset.review_status)}"><div class="asset-version-preview">${asset.uri?`<img src="${safe(asset.uri)}" alt="${safe(asset.name)} version ${asset.version}">`:'<span>NO PREVIEW</span>'}</div><div class="asset-version-meta"><b>Version ${asset.version}</b><span>${asset.active?'CURRENT · ':''}${safe(asset.review_status)}</span></div><textarea data-asset-notes="${asset.asset_type}:${asset.id}" rows="2" placeholder="Review notes">${safe(asset.review_notes||'')}</textarea><div class="asset-review-actions"><button type="button" data-asset-review="alternate" data-asset-type="${safe(asset.asset_type)}" data-asset-id="${asset.id}">Approve alternate</button><button type="button" class="primary" data-asset-review="select" data-asset-type="${safe(asset.asset_type)}" data-asset-id="${asset.id}">${asset.active?'Reconfirm current':'Use this version'}</button><button type="button" data-asset-review="reject" data-asset-type="${safe(asset.asset_type)}" data-asset-id="${asset.id}">Reject</button></div></article>`).join('')}</div></section>`).join(''):'<div class="crew-empty">Generate character sheets, backgrounds, or storyboards to begin asset review.</div>';
  document.querySelectorAll('[data-asset-review]').forEach(button=>button.onclick=()=>reviewAsset(button.dataset.assetType,Number(button.dataset.assetId),button.dataset.assetReview));
}

async function reviewAsset(assetType, assetId, decision) {
  const notes=document.querySelector(`[data-asset-notes="${assetType}:${assetId}"]`)?.value||'', selected=decision==='select', status=decision==='reject'?'rejected':'approved';
  await api(`/api/assets/${assetType}/${assetId}/review`,{method:'PUT',body:JSON.stringify({status,notes,selected})});const projectId=activeCompositorStudio.project_id;activeCompositorStudio=await api(`/api/projects/${projectId}/compositor`);renderAssetReview();renderCompositorShots();if(activeComposition){activeComposition=await api(`/api/shots/${activeCompositorShotId}/composition`);renderCompositionEditor();if(activeCompositionLayerId)selectCompositionLayer(activeCompositionLayerId);}
}

function renderCompositorShots() {
  document.querySelector('#compositor-shots').innerHTML=activeCompositorStudio.shots.length?activeCompositorStudio.shots.map(shot=>`<button type="button" class="compositor-shot ${shot.id===activeCompositorShotId?'active':''}" data-compositor-shot="${shot.id}"><b>${safe(shot.title)}</b><small>${safe(shot.scene_title)} · ${shot.duration_seconds.toFixed(1)}s · ${safe(shot.composition_status)}</small></button>`).join(''):'<div class="empty">Build shots before compositing.</div>';document.querySelectorAll('[data-compositor-shot]').forEach(button=>button.onclick=()=>selectCompositorShot(Number(button.dataset.compositorShot)));
}

async function selectCompositorShot(shotId) {
  if(activeCompositorShotId!==shotId)document.querySelector('#animator-result').innerHTML='';activeCompositorShotId=shotId;activeCompositionLayerId=null;renderCompositorShots();const shot=activeCompositorStudio.shots.find(item=>item.id===shotId);if(!shot?.composition_id){activeComposition=null;document.querySelector('#composition-editor').style.display='none';document.querySelector('#composition-empty').style.display='block';document.querySelector('#composition-empty').textContent='Build this shot to create its background and character layer stack.';return;} activeComposition=await api(`/api/shots/${shotId}/composition`);renderCompositionEditor();
}

function stageLayer(layer) {
  const transform=layer.transform||{};const translateX=(Number(transform.x??.5)-.5)*100;const translateY=(Number(transform.y??.5)-.5)*100;const style=`z-index:${layer.z_index};opacity:${layer.visible?layer.opacity:0};transform:translate(${translateX}%,${translateY}%) scale(${Number(transform.scale||1)}) rotate(${Number(transform.rotation||0)}deg);mix-blend-mode:${layer.blend_mode}`;
  return layer.source_uri?`<img class="stage-layer ${safe(layer.kind)}" src="${safe(layer.source_uri)}" style="${style}" alt="${safe(layer.name)} layer">`:`<div class="stage-layer stage-placeholder ${safe(layer.kind)}" style="${style}">${safe(layer.name)}</div>`;
}

function renderCompositionEditor() {
  const editor=document.querySelector('#composition-editor');document.querySelector('#composition-empty').style.display='none';editor.style.display='block';document.querySelector('#composition-stage').innerHTML=activeComposition.layers.map(stageLayer).join('');document.querySelector('#composition-layers').innerHTML=activeComposition.layers.map(layer=>`<button type="button" class="layer-pill ${layer.id===activeCompositionLayerId?'active':''}" data-layer-id="${layer.id}">${layer.z_index} · ${safe(layer.name)}</button>`).join('');document.querySelectorAll('[data-layer-id]').forEach(button=>button.onclick=()=>selectCompositionLayer(Number(button.dataset.layerId)));
  const camera=activeComposition.camera||{},grade=activeComposition.color_grade||{};document.querySelector('#comp-camera-move').value=camera.move||'locked';document.querySelector('#comp-start-scale').value=camera.start_scale??1;document.querySelector('#comp-end-scale').value=camera.end_scale??1;document.querySelector('#comp-exposure').value=grade.exposure??1;document.querySelector('#comp-contrast').value=grade.contrast??1;document.querySelector('#comp-saturation').value=grade.saturation??1;
  const assets=activeCompositorStudio.assets;document.querySelector('#composition-asset').innerHTML=assets.length?assets.map((asset,index)=>`<option value="${index}">${safe(asset.kind)} · ${safe(asset.name)} · v${asset.version}</option>`).join(''):'<option value="">Generate assets in Characters or Worlds first</option>';document.querySelector('#add-composition-layer').disabled=!assets.length;
  document.querySelector('#composite-result').innerHTML=`${activeComposition.latest_render_uri?`<div class="composite-preview"><img src="${safe(activeComposition.latest_render_uri)}" alt="Rendered composite preview"><div class="composite-ready">Still preview ready · automatically available in Timeline</div></div>`:''}${activeComposition.latest_motion_uri?`<div class="motion-preview"><video controls loop src="${safe(activeComposition.latest_motion_uri)}"></video><div class="composite-ready">Motion preview · composition v${activeComposition.version}</div></div>`:''}`;
}

function selectCompositionLayer(layerId) {
  const layer=activeComposition.layers.find(item=>item.id===layerId);if(!layer)return;activeCompositionLayerId=layerId;const form=document.querySelector('#layer-form'),transform=layer.transform||{},animation=layer.animation||{},end=animation.end||{};document.querySelector('#layer-empty').style.display='none';form.style.display='block';document.querySelector('#layer-title').textContent=layer.name;form.elements.layer_name.value=layer.name;form.elements.layer_z.value=layer.z_index;form.elements.layer_opacity.value=layer.opacity;form.elements.layer_blend.value=layer.blend_mode;form.elements.layer_visible.value=String(layer.visible);form.elements.layer_x.value=transform.x??.5;form.elements.layer_y.value=transform.y??.5;form.elements.layer_scale.value=transform.scale??1;form.elements.layer_rotation.value=transform.rotation??0;form.elements.layer_animation.value=animation.intent||animation.entrance||'';form.elements.motion_easing.value=animation.easing||'ease-in-out';form.elements.motion_end_x.value=end.x??transform.x??.5;form.elements.motion_end_y.value=end.y??transform.y??.5;form.elements.motion_end_scale.value=end.scale??transform.scale??1;form.elements.motion_end_rotation.value=end.rotation??transform.rotation??0;form.elements.motion_end_opacity.value=end.opacity??layer.opacity;renderCompositionEditor();
}

async function refreshComposition() { activeComposition=await api(`/api/shots/${activeCompositorShotId}/composition`);activeCompositorStudio=await api(`/api/projects/${activeCompositorStudio.project_id}/compositor`);renderAssetReview();renderCompositorShots();renderCompositionEditor();if(activeCompositionLayerId)selectCompositionLayer(activeCompositionLayerId); }

function renderCharacterRoster(projectId) {
  const roster=projects.find(project=>project.id===projectId)?.characters||[],host=document.querySelector('#character-roster');
  host.innerHTML=`<button type="button" class="character-pill ${activeCharacterId===null?'active':''}" data-new-character data-initial="+">&#43; Build a new character</button>${roster.map(character=>`<button type="button" class="character-pill ${activeCharacterId===character.id?'active':''}" data-character-id="${character.id}" data-initial="${safe(character.name.slice(0,1).toUpperCase())}"><b>${safe(character.name)}</b><small>${safe(character.role)}${character.design?` &middot; model sheet v${character.design.version}`:' &middot; identity open'}</small><small>${safe(character.want||'History and motivation ready to define')}</small></button>`).join('')}`;
  host.querySelector('[data-new-character]').onclick=()=>{activeCharacterId=null;clearCharacterForm();renderCharacterRoster(projectId);};
  host.querySelectorAll('[data-character-id]').forEach(button=>button.onclick=()=>selectCharacter(projectId,Number(button.dataset.characterId)));
}

function renderAudioStudioArrangementLegacy(projectId) {
  const cues=activeAudioStudio.tracks.flatMap(track=>track.cues),duration=Math.max(activeAudioStudio.total_duration_seconds,10),colors={dialogue:'#79d7ff',music:'#a98aff',sfx:'#ffbd66',ambience:'#67d6a2'};
  document.querySelector('#audio-summary').innerHTML=`<b>${activeAudioStudio.tracks.length} TRACKS</b><span>${cues.length} clips</span><span>${activeAudioStudio.total_duration_seconds.toFixed(1)}s picture lock</span><span>Arrangement view</span>`;
  document.querySelector('#audio-tracks').innerHTML=activeAudioStudio.tracks.length?activeAudioStudio.tracks.map(track=>`<section class="track-group" style="--track-color:${colors[track.kind]||'#79d7ff'}"><header class="track-head"><b>${safe(track.name)}</b><button type="button" data-new-cue="${track.id}">ï¼‹ Clip</button></header><div class="track-lane">${track.cues.map(cue=>`<button type="button" class="cue-item ${activeAudioCueId===cue.id?'active':''}" data-cue-id="${cue.id}" style="left:${Math.min(96,cue.start_seconds/duration*100)}%;--cue-width:${Math.max(4,cue.duration_seconds/duration*100)}%"><small>${cue.start_seconds.toFixed(1)}s</small><span><b>${safe(cue.text||cue.direction||'Untitled clip')}</b><small>${safe(cue.status)}</small></span><small>${cue.duration_seconds.toFixed(1)}s</small></button>`).join('')}</div></section>`).join(''):'<div class="empty">Initialize the standard production tracks.</div>';
  document.querySelectorAll('[data-new-cue]').forEach(button=>button.onclick=()=>newAudioCue(Number(button.dataset.newCue)));document.querySelectorAll('[data-cue-id]').forEach(button=>button.onclick=()=>selectAudioCue(Number(button.dataset.cueId)));fillVoiceBible(projectId);renderProductionFlow();
}

function snapAudioTime(value) { const snap=Number(document.querySelector('#audio-snap')?.value||.25);return Math.max(0,Math.round(value/snap)*snap); }

function audioCuePayload(cue,start=cue.start_seconds,duration=cue.duration_seconds) { return {clip_id:cue.clip_id,character_id:cue.character_id,start_seconds:Number(start.toFixed(3)),duration_seconds:Number(Math.max(.05,duration).toFixed(3)),text:cue.text,direction:cue.direction}; }

function renderAudioStudio(projectId) {
  const cues=activeAudioStudio.tracks.flatMap(track=>track.cues),duration=Math.max(activeAudioStudio.total_duration_seconds,10),colors={dialogue:'#79d7ff',music:'#a98aff',sfx:'#ffbd66',ambience:'#67d6a2'},zoom=Number(document.querySelector('#audio-zoom')?.value||900),playhead=Math.min(duration,Number(document.querySelector('#audio-playhead')?.value||0));
  document.querySelector('#audio-playhead').max=duration;
  document.querySelector('#audio-summary').innerHTML=`<b>${activeAudioStudio.tracks.length} TRACKS</b><span>${cues.length} regions</span><span>${activeAudioStudio.total_duration_seconds.toFixed(1)}s picture lock</span><span>Snap ${document.querySelector('#audio-snap')?.value||.25}s</span>`;
  const host=document.querySelector('#audio-tracks');host.style.setProperty('--audio-lane-width',`${zoom}px`);host.innerHTML=`<i class="audio-playhead-marker" style="left:${142+playhead/duration*zoom}px"></i>`+(activeAudioStudio.tracks.length?activeAudioStudio.tracks.map(track=>`<section class="track-group" style="--track-color:${colors[track.kind]||'#79d7ff'}"><header class="track-head"><b>${safe(track.name)}</b><button type="button" data-new-cue="${track.id}">ï¼‹ Region</button></header><div class="track-lane" data-audio-lane="${track.id}" data-duration="${duration}">${track.cues.map(cue=>`<button type="button" draggable="true" class="cue-item ${activeAudioCueId===cue.id?'active':''}" data-cue-id="${cue.id}" style="left:${cue.start_seconds/duration*100}%;--cue-width:${Math.max(1,cue.duration_seconds/duration*100)}%"><small>${cue.start_seconds.toFixed(2)}s</small><span><b>${safe(cue.text||cue.direction||'Untitled region')}</b><small>${safe(cue.status)}</small></span><small>${cue.duration_seconds.toFixed(2)}s</small><i class="cue-resize" data-cue-resize="${cue.id}" aria-label="Resize region"></i></button>`).join('')}</div></section>`).join(''):'<div class="empty">Initialize the standard production tracks.</div>');
  host.querySelectorAll('[data-new-cue]').forEach(button=>button.onclick=()=>newAudioCue(Number(button.dataset.newCue)));host.querySelectorAll('[data-cue-id]').forEach(button=>{button.onclick=()=>selectAudioCue(Number(button.dataset.cueId));button.ondragstart=event=>{const found=findAudioCue(Number(button.dataset.cueId));if(!found)return;audioDragState={cueId:found.cue.id,trackId:found.track.id};event.dataTransfer.effectAllowed='move';button.classList.add('dragging');};button.ondragend=()=>{button.classList.remove('dragging');audioDragState=null;};});
  host.querySelectorAll('[data-audio-lane]').forEach(lane=>{lane.onclick=event=>{if(event.target===lane){const rect=lane.getBoundingClientRect();document.querySelector('#audio-playhead').value=snapAudioTime((event.clientX-rect.left)/rect.width*Number(lane.dataset.duration));renderAudioStudio(projectId);}};lane.ondragover=event=>{event.preventDefault();lane.classList.add('drag-target');};lane.ondragleave=()=>lane.classList.remove('drag-target');lane.ondrop=event=>{event.preventDefault();lane.classList.remove('drag-target');dropAudioRegion(event,lane);};});
  host.querySelectorAll('[data-cue-resize]').forEach(handle=>handle.onpointerdown=event=>beginAudioResize(event,Number(handle.dataset.cueResize)));
  fillVoiceBible(projectId);renderProductionFlow();
}

async function dropAudioRegion(event,lane) {
  if(!audioDragState||Number(lane.dataset.audioLane)!==audioDragState.trackId)return;const found=findAudioCue(audioDragState.cueId);if(!found)return;const rect=lane.getBoundingClientRect(),duration=Number(lane.dataset.duration),start=snapAudioTime((event.clientX-rect.left)/rect.width*duration);await api(`/api/audio-cues/${found.cue.id}`,{method:'PUT',body:JSON.stringify(audioCuePayload(found.cue,start))});await refreshAudioAndSelect(found.cue.id);
}

function beginAudioResize(event,cueId) {
  event.preventDefault();event.stopPropagation();const found=findAudioCue(cueId),lane=event.currentTarget.closest('[data-audio-lane]');if(!found||!lane)return;const origin=event.clientX,startDuration=found.cue.duration_seconds,laneDuration=Number(lane.dataset.duration),laneWidth=lane.getBoundingClientRect().width;const move=moveEvent=>{const preview=Math.max(.05,startDuration+(moveEvent.clientX-origin)/laneWidth*laneDuration);event.currentTarget.closest('.cue-item').style.setProperty('--cue-width',`${preview/laneDuration*100}%`);};const finish=async upEvent=>{document.removeEventListener('pointermove',move);document.removeEventListener('pointerup',finish);const resized=snapAudioTime(Math.max(.05,startDuration+(upEvent.clientX-origin)/laneWidth*laneDuration));await api(`/api/audio-cues/${cueId}`,{method:'PUT',body:JSON.stringify(audioCuePayload(found.cue,found.cue.start_seconds,Math.max(.05,resized)))});await refreshAudioAndSelect(cueId);};document.addEventListener('pointermove',move);document.addEventListener('pointerup',finish,{once:true});
}

async function splitSelectedAudioRegion() { if(!activeAudioCueId)return;const found=findAudioCue(activeAudioCueId);if(!found)return;const playhead=Number(document.querySelector('#audio-playhead').value),relative=playhead>found.cue.start_seconds&&playhead<found.cue.start_seconds+found.cue.duration_seconds?playhead-found.cue.start_seconds:found.cue.duration_seconds/2;const regions=await api(`/api/audio-cues/${activeAudioCueId}/split`,{method:'POST',body:JSON.stringify({split_seconds:relative})});await refreshAudioAndSelect(regions[1].id); }

async function duplicateSelectedAudioRegion() { if(!activeAudioCueId)return;const cue=await api(`/api/audio-cues/${activeAudioCueId}/duplicate`,{method:'POST',body:JSON.stringify({offset_seconds:Number(document.querySelector('#audio-snap').value)})});await refreshAudioAndSelect(cue.id); }

async function deleteSelectedAudioRegion() { if(!activeAudioCueId)return;await api(`/api/audio-cues/${activeAudioCueId}`,{method:'DELETE'});activeAudioCueId=null;activeAudioStudio=await api(`/api/projects/${activeAudioStudio.project_id}/audio-studio`);document.querySelector('#cue-form').style.display='none';document.querySelector('#cue-empty').style.display='block';renderAudioStudio(activeAudioStudio.project_id); }

function collectStory(form) {
  return {premise:form.elements.premise.value, format:form.elements.format.value, target_duration_minutes:Number(form.elements.target_duration_minutes.value), genre:form.elements.genre.value, audience:form.elements.audience.value, themes:form.elements.themes.value.split(',').map(value => value.trim()).filter(Boolean)};
}

document.querySelector('#new-project').onclick = () => projectDialog.showModal();
document.querySelector('#productions-nav').onclick = showDashboard;
document.querySelector('#crew-nav').onclick = () => openCrewStudio();
document.querySelector('.brand').onclick = event => { event.preventDefault(); showDashboard(); };
document.querySelector('#style-lab-nav').onclick = () => openStyleLab();
document.querySelector('#writer-nav').onclick = () => openWriterRoom();
document.querySelector('#characters-nav').onclick = () => openCharacterStudio();
document.querySelector('#render-nav').onclick = () => openRenderFarm();
document.querySelector('#worlds-nav').onclick = () => openWorldStudio();
document.querySelector('#shots-nav').onclick = () => openShotPlanner();
document.querySelector('#timeline-nav').onclick = () => openTimeline();
document.querySelector('#audio-nav').onclick = () => openAudioStudio();
document.querySelector('#compositor-nav').onclick = () => openCompositor();
document.querySelector('.close').onclick = () => projectDialog.close();
document.querySelector('#style-close').onclick = showDashboard;
document.querySelector('#crew-close').onclick = showDashboard;
document.querySelector('#writer-close').onclick = showDashboard;
document.querySelector('#character-close').onclick = showDashboard;
document.querySelector('#render-close').onclick = showDashboard;
document.querySelector('#world-close').onclick = showDashboard;
document.querySelector('#shot-close').onclick = showDashboard;
document.querySelector('#timeline-close').onclick = showDashboard;
document.querySelector('#audio-close').onclick = showDashboard;
document.querySelector('#compositor-close').onclick = showDashboard;
document.querySelector('#deploy-crew').onclick = deploySelectedCrew;
document.querySelector('#start-producer').onclick = saveProducerWorkflow;
document.querySelector('#advance-producer').onclick = advanceProducerWorkflow;
document.querySelector('#ask-writer').onclick = askWriter;
document.querySelector('#ask-director').onclick = askDirector;
document.querySelector('#ask-character-designer').onclick = askCharacterDesigner;
document.querySelector('#ask-background-artist').onclick = askBackgroundArtist;
document.querySelector('#ask-animator').onclick = askAnimator;
document.querySelector('#ask-editor').onclick = askEditor;
document.querySelector('#build-composition').onclick = async () => { if(!activeCompositorShotId)return;activeComposition=await api(`/api/shots/${activeCompositorShotId}/composition/build`,{method:'POST'});activeCompositorStudio=await api(`/api/projects/${activeCompositorStudio.project_id}/compositor`);renderCompositorShots();renderCompositionEditor();if(activeComposition.layers.length)selectCompositionLayer(activeComposition.layers[0].id); };
document.querySelector('#save-composition').onclick = async () => { if(!activeComposition)return;activeComposition=await api(`/api/compositions/${activeComposition.id}`,{method:'PUT',body:JSON.stringify({camera:{...activeComposition.camera,move:document.querySelector('#comp-camera-move').value,start_scale:Number(document.querySelector('#comp-start-scale').value),end_scale:Number(document.querySelector('#comp-end-scale').value)},color_grade:{exposure:Number(document.querySelector('#comp-exposure').value),contrast:Number(document.querySelector('#comp-contrast').value),saturation:Number(document.querySelector('#comp-saturation').value)}})});renderCompositionEditor(); };
document.querySelector('#add-composition-layer').onclick = async () => { if(!activeComposition)return;const asset=activeCompositorStudio.assets[Number(document.querySelector('#composition-asset').value)];if(!asset)return;const z=Math.max(0,...activeComposition.layers.map(layer=>layer.z_index))+10;const layer=await api(`/api/compositions/${activeComposition.id}/layers`,{method:'POST',body:JSON.stringify({name:asset.name,kind:asset.kind,source_kind:asset.source_kind,source_asset_id:asset.id,source_uri:asset.uri,z_index:z,visible:true,opacity:1,blend_mode:'normal',transform:{x:.5,y:.5,scale:1,rotation:0},animation:{intent:'hold'}})});activeCompositionLayerId=layer.id;await refreshComposition(); };
document.querySelector('#layer-form').onsubmit = async event => { event.preventDefault();const layer=activeComposition.layers.find(item=>item.id===activeCompositionLayerId);if(!layer)return;const form=event.target;await api(`/api/composition-layers/${layer.id}`,{method:'PUT',body:JSON.stringify({name:form.elements.layer_name.value,kind:layer.kind,source_kind:layer.source_kind,source_asset_id:layer.source_asset_id,source_uri:layer.source_uri,z_index:Number(form.elements.layer_z.value),visible:form.elements.layer_visible.value==='true',opacity:Number(form.elements.layer_opacity.value),blend_mode:form.elements.layer_blend.value,transform:{x:Number(form.elements.layer_x.value),y:Number(form.elements.layer_y.value),scale:Number(form.elements.layer_scale.value),rotation:Number(form.elements.layer_rotation.value)},animation:{intent:form.elements.layer_animation.value,easing:form.elements.motion_easing.value,end:{x:Number(form.elements.motion_end_x.value),y:Number(form.elements.motion_end_y.value),scale:Number(form.elements.motion_end_scale.value),rotation:Number(form.elements.motion_end_rotation.value),opacity:Number(form.elements.motion_end_opacity.value)}}})});await refreshComposition(); };
document.querySelector('#render-composition').onclick = async () => { if(!activeComposition)return;const button=document.querySelector('#render-composition');button.disabled=true;button.textContent='Rendering…';try{const result=await api(`/api/compositions/${activeComposition.id}/render`,{method:'POST'});if(result.status==='failed')document.querySelector('#composite-result').innerHTML=`<div class="job-error">${safe(result.error)}</div>`;else await refreshComposition();}finally{button.disabled=false;button.textContent='Render preview';} };
document.querySelector('#render-motion').onclick = async () => { if(!activeComposition)return;const button=document.querySelector('#render-motion');button.disabled=true;button.textContent='Rendering motion…';document.querySelector('#composite-result').innerHTML='<div class="render-progress">Interpolating layers and encoding the shot preview…</div>';try{const result=await api(`/api/compositions/${activeComposition.id}/render-video`,{method:'POST',body:JSON.stringify({quality:'proxy'})});if(result.status==='failed')document.querySelector('#composite-result').innerHTML=`<div class="job-error">${safe(result.error)}</div>`;else await refreshComposition();}finally{button.disabled=false;button.textContent='Render motion preview';} };
document.querySelector('#build-audio').onclick = async () => { const projectId=Number(document.querySelector('#audio-project').value); try { if(!activeAudioTimeline)activeAudioTimeline=await api(`/api/projects/${projectId}/timeline`); activeAudioStudio=await api(`/api/timelines/${activeAudioTimeline.id}/audio/build`,{method:'POST'}); renderAudioStudio(projectId); } catch(error) { document.querySelector('#audio-tracks').innerHTML=`<div class="job-error">${safe(error.message)}</div>`; } };
document.querySelector('#save-voice').onclick = async () => { const characterId=Number(document.querySelector('#voice-character').value);if(!characterId)return; const existing=activeAudioStudio?.voice_profiles.find(item=>item.character_id===characterId); await api(`/api/characters/${characterId}/voice`,{method:'PUT',body:JSON.stringify({vocal_age:existing?.vocal_age||'young adult',texture:document.querySelector('#voice-texture').value,energy:document.querySelector('#voice-energy').value,accent:existing?.accent||'neutral',language:existing?.language||'English',pace:Number(document.querySelector('#voice-pace').value),pitch:Number(document.querySelector('#voice-pitch').value),provider:document.querySelector('#voice-provider').value,provider_voice_id:document.querySelector('#voice-provider-id').value,direction_notes:document.querySelector('#voice-direction').value})}); if(activeAudioStudio){activeAudioStudio=await api(`/api/projects/${activeAudioStudio.project_id}/audio-studio`);renderAudioStudio(activeAudioStudio.project_id);} };
document.querySelector('#save-voice-rights').onclick = async () => { const characterId=Number(document.querySelector('#voice-character').value);if(!characterId)return;await api(`/api/characters/${characterId}/voice-consent`,{method:'PUT',body:JSON.stringify({source_type:'built_in_ai',subject_name:'',consent_confirmed:document.querySelector('#voice-consent').checked,disclosure_required:true,notes:'Creator confirmed authorized AI voice use.'})}); };
document.querySelector('#add-pronunciation').onclick = async () => { const term=document.querySelector('#pronunciation-term').value.trim(), pronunciation=document.querySelector('#pronunciation-value').value.trim();if(!term||!pronunciation||!activeAudioStudio)return;await api(`/api/projects/${activeAudioStudio.project_id}/pronunciations`,{method:'POST',body:JSON.stringify({character_id:Number(document.querySelector('#voice-character').value)||null,term,pronunciation,language:'English',notes:''})});document.querySelector('#pronunciation-term').value='';document.querySelector('#pronunciation-value').value=''; };
document.querySelector('#cue-form').onsubmit = async event => { event.preventDefault(); const form=event.target; const payload={clip_id:null,character_id:form.elements.cue_character.value?Number(form.elements.cue_character.value):null,start_seconds:Number(form.elements.cue_start.value),duration_seconds:Number(form.elements.cue_duration.value),text:form.elements.cue_text.value,direction:form.elements.cue_direction.value}; const cue=activeAudioCueId?await api(`/api/audio-cues/${activeAudioCueId}`,{method:'PUT',body:JSON.stringify(payload)}):await api(`/api/audio-tracks/${Number(form.elements.cue_track.value)}/cues`,{method:'POST',body:JSON.stringify(payload)}); await refreshAudioAndSelect(cue.id); };
document.querySelector('#build-timeline').onclick = async () => { const projectId=Number(document.querySelector('#timeline-project').value); try { activeTimeline=await api(`/api/projects/${projectId}/timeline/build`,{method:'POST',body:JSON.stringify({fps:24,width:1920,height:1080})}); renderTimeline(); } catch(error) { document.querySelector('#timeline-clips').innerHTML=`<div class="job-error">${safe(error.message)}</div>`; } };
document.querySelector('#clip-form').onsubmit = async event => { event.preventDefault(); const form=event.target; activeTimeline=await api(`/api/timeline-clips/${activeClipId}`,{method:'PUT',body:JSON.stringify({duration_seconds:Number(form.elements.clip_duration.value),transition:form.elements.clip_transition.value,transition_duration:Number(form.elements.clip_transition_duration.value),audio_cue:form.elements.clip_audio_cue.value})}); renderTimeline(); };
document.querySelector('#clip-earlier').onclick = () => moveClip(-1);
document.querySelector('#clip-later').onclick = () => moveClip(1);
document.querySelector('#render-animatic').onclick = async () => { if(!activeTimeline)return; const button=document.querySelector('#render-animatic'); button.disabled=true; button.textContent='Rendering proxy…'; document.querySelector('#animatic-result').innerHTML='<div class="render-progress">Preparing frames and encoding the edit…</div>'; try { const result=await api(`/api/timelines/${activeTimeline.id}/render`,{method:'POST'}); document.querySelector('#animatic-result').innerHTML=result.status==='completed'?`<video controls src="${safe(result.uri)}"></video><p><a href="${safe(result.uri)}" download>Download proxy MP4</a></p>`:`<div class="job-error">${safe(result.error)}</div>`; await loadTimeline(activeTimeline.project_id); } catch(error) { document.querySelector('#animatic-result').innerHTML=`<div class="job-error">${safe(error.message)}</div>`; } finally { button.disabled=false; button.textContent='Render proxy animatic'; } };
document.querySelector('#render-master').onclick = async () => { if(!activeTimeline)return;const button=document.querySelector('#render-master'),profile=document.querySelector('#master-profile').value;button.disabled=true;button.textContent='Exporting master…';document.querySelector('#animatic-result').innerHTML=`<div class="render-progress">Assembling motion clips, transitions, fallback frames, and the audio mix at ${safe(profile)}…</div>`;try{const result=await api(`/api/timelines/${activeTimeline.id}/render-master`,{method:'POST',body:JSON.stringify({profile})});if(result.status==='completed'){const settings=result.render_settings;document.querySelector('#animatic-result').innerHTML=`<video controls src="${safe(result.uri)}"></video><div class="master-manifest"><b>${safe(settings.profile.toUpperCase())} MASTER</b><span>${settings.width} × ${settings.height} · ${settings.fps} fps</span><span>${settings.motion_clips} motion clip${settings.motion_clips===1?'':'s'} · ${settings.fallback_clips} fallback clip${settings.fallback_clips===1?'':'s'} · ${settings.audio_cues} audio cue${settings.audio_cues===1?'':'s'}</span><a href="${safe(result.uri)}" download>Download continuous master</a></div>`;}else document.querySelector('#animatic-result').innerHTML=`<div class="job-error">${safe(result.error)}</div>`;await loadTimeline(activeTimeline.project_id);}catch(error){document.querySelector('#animatic-result').innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}finally{button.disabled=false;button.textContent='Export continuous master';} };
document.querySelector('#plan-segmented-export').onclick = async () => { if(!activeTimeline)return;const button=document.querySelector('#plan-segmented-export');button.disabled=true;button.textContent='Starting farm…';try{renderSegmentedExport(await api(`/api/timelines/${activeTimeline.id}/master-exports/distributed`,{method:'POST',body:JSON.stringify({profile:document.querySelector('#master-profile').value,segment_size:Number(document.querySelector('#segment-size').value)})}));}catch(error){document.querySelector('#segmented-export-result').innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}finally{button.disabled=false;button.textContent='Start farm export';} };
document.querySelector('#expand-story').onclick = async () => { const projectId = Number(document.querySelector('#shot-project').value); try { await api(`/api/projects/${projectId}/expand-story`, {method:'POST',body:JSON.stringify({shots_per_beat:Number(document.querySelector('#shots-per-beat').value)})}); await loadProjects(); renderShotTree(projectId); } catch(error) { document.querySelector('#shot-tree').innerHTML = `<div class="job-error">${safe(error.message)}</div>`; } };
document.querySelector('#refresh-farm').onclick = () => refreshRenderFarm();
document.querySelector('#project-form').onsubmit = async event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.target)); await api('/api/projects', {method:'POST', body:JSON.stringify(data)}); event.target.reset(); projectDialog.close(); await loadProjects(); showDashboard(); };
document.querySelector('#style-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#style-project').value); await api(`/api/projects/${projectId}/style`, {method:'PUT', body:JSON.stringify(collectStyle(event.target))}); styleDialog.close(); await loadProjects(); openProject(projectId); };
document.querySelector('#writer-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#writer-project').value); const brief = await api(`/api/projects/${projectId}/story`, {method:'PUT', body:JSON.stringify(collectStory(event.target))}); await loadProjects(); renderStory(brief); };
document.querySelector('#character-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#character-project').value); const character = activeCharacterId ? await api(`/api/characters/${activeCharacterId}`, {method:'PUT', body:JSON.stringify(collectCharacter(event.target))}) : await api(`/api/projects/${projectId}/characters`, {method:'POST', body:JSON.stringify(collectCharacter(event.target))}); activeCharacterId = character.id; const design = await api(`/api/characters/${character.id}/design`, {method:'PUT', body:JSON.stringify(collectCharacterDesign(event.target))}); await loadProjects(); renderCharacterRoster(projectId); renderCharacterDesign(character, design); };
document.querySelector('#world-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#world-project').value); const location = activeLocationId ? await api(`/api/locations/${activeLocationId}`, {method:'PUT', body:JSON.stringify(collectWorld(event.target))}) : await api(`/api/projects/${projectId}/locations`, {method:'POST', body:JSON.stringify(collectWorld(event.target))}); activeLocationId = location.id; const design = await api(`/api/locations/${location.id}/design`, {method:'PUT', body:JSON.stringify(collectWorldDesign(event.target))}); await loadProjects(); renderWorldRoster(projectId); renderWorldDesign(location, design); };
document.querySelector('#shot-form').onsubmit = async event => { event.preventDefault(); const project = currentShotProject(); const found = findShot(project, activeShotId); if (!found) return; const form = event.target; await api(`/api/shots/${activeShotId}`, {method:'PUT',body:JSON.stringify({title:form.elements.shot_title.value,description:form.elements.shot_description.value,position:found.shot.position,duration_seconds:Number(form.elements.shot_duration.value)})}); const plan = await api(`/api/shots/${activeShotId}/plan`, {method:'PUT',body:JSON.stringify(collectShotPlan(form))}); await loadProjects(); selectShot(project.id, activeShotId); renderShotPlan(plan); };
document.querySelector('#timeline-zoom').oninput=event=>document.querySelector('#timeline-clips').style.setProperty('--timeline-clip-width',`${event.target.value}px`);
document.querySelector('#audio-zoom').oninput=()=>{if(activeAudioStudio)renderAudioStudio(activeAudioStudio.project_id);};
document.querySelector('#audio-snap').onchange=()=>{if(activeAudioStudio)renderAudioStudio(activeAudioStudio.project_id);};
document.querySelector('#audio-playhead').onchange=()=>{if(activeAudioStudio)renderAudioStudio(activeAudioStudio.project_id);};
document.querySelector('#split-audio-region').onclick=splitSelectedAudioRegion;
document.querySelector('#duplicate-audio-region').onclick=duplicateSelectedAudioRegion;
document.querySelector('#delete-audio-region').onclick=deleteSelectedAudioRegion;
setupCraftWorkspaces();
loadProjects().catch(error => projectsEl.innerHTML = `<div class="empty">Could not load the studio: ${safe(error.message)}</div>`);
