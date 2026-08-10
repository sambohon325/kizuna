const projectsEl = document.querySelector('#projects');
const projectDialog = document.querySelector('#project-dialog');
const detailDialog = document.querySelector('#detail-dialog');
const crewDialog = document.querySelector('#crew-dialog');
const styleDialog = document.querySelector('#style-dialog');
const writerDialog = document.querySelector('#writer-dialog');
const characterDialog = document.querySelector('#character-dialog');
const renderDialog = document.querySelector('#render-dialog');
const worldDialog = document.querySelector('#world-dialog');
const assetDialog = document.querySelector('#asset-dialog');
const shotDialog = document.querySelector('#shot-dialog');
const timelineDialog = document.querySelector('#timeline-dialog');
const audioDialog = document.querySelector('#audio-dialog');
const compositorDialog = document.querySelector('#compositor-dialog');
const accountDialog = document.querySelector('#account-dialog');
const settingsDialog = document.querySelector('#settings-dialog');
const workspaceMain = document.querySelector('#workspace-main');
const dashboardHome = document.querySelector('#dashboard-home');
const workspaceDialogs = [detailDialog, crewDialog, styleDialog, writerDialog, characterDialog, renderDialog, worldDialog, assetDialog, shotDialog, timelineDialog, audioDialog, compositorDialog, accountDialog, settingsDialog];
const workspaceNav = new Map([
  [detailDialog, 'productions-nav'], [crewDialog, 'crew-nav'], [styleDialog, 'style-lab-nav'], [writerDialog, 'writer-nav'],
  [characterDialog, 'characters-nav'], [renderDialog, 'render-nav'], [worldDialog, 'worlds-nav'], [assetDialog, 'assets-nav'],
  [shotDialog, 'shots-nav'], [timelineDialog, 'timeline-nav'], [audioDialog, 'audio-nav'],
  [compositorDialog, 'compositor-nav'], [accountDialog, 'settings-nav'], [settingsDialog, 'settings-nav'],
]);
const workspaceKeys = new Map([
  [crewDialog,'crew'],[styleDialog,'style'],[writerDialog,'writer'],[characterDialog,'characters'],[worldDialog,'worlds'],[assetDialog,'assets'],[shotDialog,'shots'],[timelineDialog,'timeline'],[audioDialog,'audio'],[compositorDialog,'compositor'],[renderDialog,'render'],[accountDialog,'account'],[settingsDialog,'settings'],
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
  workspaceMain.classList.toggle('settings-open',dialog===settingsDialog||dialog===accountDialog);
  workspaceMain.appendChild(dialog);
  dialog.classList.add('workspace-view');
  dialog.setAttribute('open', '');
  dialog.setAttribute('role', 'region');
  const heading = dialog.querySelector('h2');
  if (heading) dialog.setAttribute('aria-label', heading.textContent);
  const back = dialog.querySelector('.close');
  if (back) {
    back.textContent = '← Productions';
    const popout=document.body.classList.contains('popout-mode');if(popout)back.textContent='Close window';
    back.title = popout?'Close this workspace window':'Back to productions';
    back.setAttribute('aria-label', back.title);
  }
  setActiveNavigation(workspaceNav.get(dialog));
  renderProductionFlow();
  refreshAssistantContext();
  window.scrollTo({top: 0, left: 0, behavior: 'auto'});
}

function setupWorkspacePopouts() {
  workspaceKeys.forEach((key,dialog)=>{const root=dialog.firstElementChild;if(!root||root.querySelector('.workspace-popout'))return;const button=document.createElement('button');button.type='button';button.className='workspace-popout';button.innerHTML='<span aria-hidden="true">\u2197</span> Open in new window';button.setAttribute('aria-label',`Open ${dialog.querySelector('h2')?.textContent||key} in a new window`);button.onclick=()=>openWorkspaceWindow(key,dialog);root.appendChild(button);});
}

function openWorkspaceWindow(key,dialog) {
  const selected=dialog.querySelector('select[id$="-project"]')?.value||currentFlowProject()?.id,url=new URL(location.href);url.search='';url.searchParams.set('workspace',key);if(selected)url.searchParams.set('project',selected);url.searchParams.set('popout','1');window.open(url,`kizuna-${key}-${selected||'studio'}`,'popup=yes,width=1440,height=960,resizable=yes,scrollbars=yes');
}

async function openRequestedWorkspace() {
  const params=new URLSearchParams(location.search),key=params.get('workspace'),projectId=Number(params.get('project'))||undefined;if(params.get('popout')==='1')document.body.classList.add('popout-mode');const openers={crew:openCrewStudio,style:openStyleLab,writer:openWriterRoom,characters:openCharacterStudio,worlds:openWorldStudio,assets:id=>window.openAssetLibraryReady?.(id),shots:openShotPlanner,timeline:openTimeline,audio:openAudioStudio,compositor:openCompositor,render:openRenderFarm,account:openAccountCenter,settings:openSettings};if(key&&openers[key])await openers[key](projectId);
}

function showDashboard() {
  stopMasterExportPolling();
  workspaceDialogs.forEach(dialog => {
    dialog.removeAttribute('open');
    dialog.classList.remove('workspace-view');
  });
  dashboardHome.hidden = false;
  workspaceMain.classList.remove('tool-open');
  workspaceMain.classList.remove('settings-open');
  setActiveNavigation();
  renderProductionFlow();
  refreshAssistantContext();
  window.scrollTo({top: 0, left: 0, behavior: 'auto'});
}

function closeWorkspace() {
  if(document.body.classList.contains('popout-mode'))window.close();else showDashboard();
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

const productionStatusCache=new Map(),productionStatusRequests=new Map();

async function refreshProductionStatus(projectId,force=false) {
  if(!projectId)return;if(force)productionStatusCache.delete(projectId);if(productionStatusRequests.has(projectId))return productionStatusRequests.get(projectId);
  const request=api(`/api/projects/${projectId}/production-status`).then(status=>{productionStatusCache.set(projectId,status);productionStatusRequests.delete(projectId);if(currentFlowProject()?.id===projectId)renderProductionFlow();return status;}).catch(()=>{productionStatusRequests.delete(projectId);});productionStatusRequests.set(projectId,request);return request;
}

function renderProductionFlow() {
  const host=document.querySelector('#production-flow');if(!host)return;const project=currentFlowProject(),status=project?productionStatusCache.get(project.id):null,current=currentFlowStage();
  if(!project){host.innerHTML='<span class="flow-label">PRODUCTION STATUS</span><span class="flow-next">Create a production to begin.</span>';return;}
  if(!status){host.innerHTML=`<span class="flow-label">${safe(project.title)}</span><span class="flow-next">Checking production status...</span>`;refreshProductionStatus(project.id);return;}
  const byKey=new Map(status.stages.map(stage=>[stage.key,stage])),next=status.stages.find(stage=>stage.key===status.next_key);
  host.innerHTML=`<span class="flow-label"><b>${safe(project.title)}</b><small>${status.complete_count}/${status.total_count} complete</small></span><div class="flow-track" aria-label="Production milestones">${productionStages.map((definition,index)=>{const stage=byKey.get(definition.key)||{state:'blocked',summary:'Status unavailable',label:definition.label};return `<div class="flow-node ${safe(stage.state)} ${current===definition.key?'viewing':''}" title="${safe(stage.summary)}" aria-label="${safe(stage.label)}: ${safe(stage.summary)}"><i>${stage.state==='complete'?'&#10003;':String(index+1).padStart(2,'0')}</i><span>${safe(definition.label)}</span></div>`;}).join('')}</div><span class="flow-next"><b>${next?'Next: '+safe(next.label):'Production complete'}</b><small>${safe(next?.summary||'Every milestone is complete.')}</small></span>`;
}

function setupCraftWorkspaces() {
  const form=document.querySelector('#writer-form');if(form&&!form.querySelector('.writer-document-sidebar')){
    if(![...form.elements.format.options].some(option=>option.value==='trailer'))form.elements.format.add(new Option('trailer','trailer'),1);
    const sidebar=document.createElement('aside'),canvas=document.createElement('section'),page=document.createElement('div');sidebar.className='writer-document-sidebar';canvas.className='writer-document-canvas';page.className='writer-document-page';
    const heading=form.querySelector(':scope > .eyebrow'),title=form.querySelector(':scope > h2'),intro=form.querySelector(':scope > .form-intro'),labels=[...form.querySelectorAll(':scope > label')],agent=form.querySelector(':scope > .writer-agent-panel');
    const scopeCard=document.createElement('section');scopeCard.id='writer-scope-card';scopeCard.className='writer-scope-card';scopeCard.innerHTML='<div class="settings-loading">Loading release plan...</div>';[heading,title,intro,labels[0],scopeCard,agent].forEach(node=>node&&sidebar.appendChild(node));[labels[1],form.querySelector(':scope > .writer-grid'),labels[2],form.querySelector(':scope > button.primary'),form.querySelector(':scope > .story-result')].forEach(node=>node&&page.appendChild(node));canvas.innerHTML='<nav class="writer-view-tabs" aria-label="Writer view"><button type="button" class="active" data-writer-view="document">Document</button><button type="button" data-writer-view="map">Story map</button></nav>';canvas.appendChild(page);form.append(sidebar,canvas);form.dataset.writerView='document';canvas.querySelectorAll('[data-writer-view]').forEach(button=>button.onclick=()=>setWriterView(button.dataset.writerView));
    if(agent){const controls=agent.querySelector('.writer-agent-controls'),details=document.createElement('details'),body=document.createElement('div'),ask=controls.querySelector('#ask-writer');details.className='advanced-settings writer-agent-settings';details.innerHTML='<summary>Writer settings</summary>';[...controls.querySelectorAll('label')].forEach(label=>body.appendChild(label));details.appendChild(body);controls.replaceChildren(ask,details);agent.querySelector('h3').textContent='Help me shape the story';agent.querySelector('div>p:not(.eyebrow)').textContent='The Writer prepares a complete proposal for your review.';ask.textContent='Ask Writer';}
  }
  const shell=document.querySelector('.shell'),toggle=document.querySelector('#rail-toggle'),collapsed=localStorage.getItem('kizuna-rail-collapsed')==='true';toggle.firstChild.nodeValue='\u2039';shell.classList.toggle('rail-collapsed',collapsed);toggle.setAttribute('aria-expanded',String(!collapsed));toggle.setAttribute('aria-label',collapsed?'Expand navigation':'Collapse navigation');
  toggle.onclick=()=>{const next=!shell.classList.contains('rail-collapsed');shell.classList.toggle('rail-collapsed',next);localStorage.setItem('kizuna-rail-collapsed',String(next));toggle.setAttribute('aria-expanded',String(!next));toggle.setAttribute('aria-label',next?'Expand navigation':'Collapse navigation');};
  const timelineControls=document.querySelector('.timeline-project-control');if(timelineControls&&!timelineControls.querySelector('.advanced-settings')){const details=document.createElement('details'),body=document.createElement('div');details.className='advanced-settings header-advanced';details.innerHTML='<summary>Master export</summary>';['master-profile','render-master','segment-size','plan-segmented-export'].forEach(id=>{const node=document.querySelector(`#${id}`);if(node)body.appendChild(node);});details.appendChild(body);timelineControls.appendChild(details);}
  const voice=document.querySelector('.voice-bible');if(voice&&!voice.closest('.advanced-settings')){const details=document.createElement('details');details.className='advanced-settings voice-setup';details.innerHTML='<summary>Voice setup & rights</summary>';voice.before(details);details.appendChild(voice);}
  setupSimplifiedCrew();
  setupCharacterStoryWorkspace();
}

function setWriterView(view) {
  const form=document.querySelector('#writer-form');form.dataset.writerView=view;form.querySelectorAll('[data-writer-view]').forEach(button=>button.classList.toggle('active',button.dataset.writerView===view));if(view==='map')form.querySelector('.connected-story-map')?.scrollIntoView({behavior:'smooth',block:'start'});else form.querySelector('.writer-document-page')?.scrollIntoView({behavior:'smooth',block:'start'});
}

function setupCharacterStoryWorkspace() {
  const form=document.querySelector('#character-form'),roster=document.querySelector('#character-roster');if(!form||form.querySelector('.character-view-tabs'))return;const sections=[...form.querySelectorAll(':scope > .character-section')],agent=roster.nextElementSibling;sections[0]?.classList.add('character-identity-section');sections[1]?.classList.add('character-visual-section');if(agent?.classList.contains('visual-agent-panel'))agent.classList.add('character-ai-panel');
  const tabs=document.createElement('nav');tabs.className='character-view-tabs';tabs.setAttribute('aria-label','Character view');tabs.innerHTML='<button type="button" class="active" data-character-view="identity">Identity</button><button type="button" data-character-view="story">Story & arc</button><button type="button" data-character-view="visual">Visual model</button>';
  const story=document.createElement('section');story.id='character-story-panel';story.className='character-story-panel';story.innerHTML='<div class="character-story-empty">Save or select a character to develop their history, arc, and relationships.</div>';
  roster.after(tabs,story);form.dataset.characterView='identity';tabs.querySelectorAll('[data-character-view]').forEach(button=>button.onclick=()=>setCharacterView(button.dataset.characterView));
}

function setCharacterView(view) {
  const form=document.querySelector('#character-form');form.dataset.characterView=view;form.querySelectorAll('[data-character-view]').forEach(button=>button.classList.toggle('active',button.dataset.characterView===view));
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
let activeAccount = null;
let generationProviders = [];
let draggedTimelineClipId = null;
let audioDragState = null;

async function api(path, options = {}) {
  const csrf=(document.cookie.match(/(?:^|; )kizuna_csrf=([^;]+)/)||[])[1]||'';
  const headers={'Content-Type':'application/json',...(options.headers||{})};
  if(csrf)headers['X-Kizuna-CSRF']=decodeURIComponent(csrf);
  const response = await fetch(path, {...options,headers});
  if(response.status===401){location.href='/login';throw new Error('Sign in required');}
  if (!response.ok) { const text=await response.text();try{const detail=JSON.parse(text).detail;throw new Error(typeof detail==='string'?detail:detail?.message||text);}catch(error){if(error instanceof SyntaxError)throw new Error(text);throw error;} }
  if (response.status === 204) return null;
  return response.json();
}

function safe(value = '') {
  return String(value).replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

async function loadAccountIdentity(){
  const status=await fetch('/api/auth/status').then(response=>response.json());if(!status.auth_required)return;
  const user=await api('/api/auth/me');activeAccount=user;document.querySelector('#studio-identity').textContent=user.account_tier==='trial'?`${user.display_name} · Trial`:user.display_name;
  const accountButton=document.querySelector('#account-nav');accountButton.hidden=false;accountButton.onclick=openAccountCenter;
  const button=document.querySelector('#sign-out');button.hidden=false;button.onclick=async()=>{await api('/api/auth/logout',{method:'POST'});location.href='/login';};
}

function scopeDisplay(scope) {
  if(!scope)return'Scope open';const formats={one_off:'One-off',trailer:'Trailer',feature_film:'Feature',ongoing_series:'Ongoing series',limited_series:'Limited series'},duration=scope.target_duration_seconds<60?`${scope.target_duration_seconds}s`:`${Math.round(scope.target_duration_seconds/60)} min`;return`${formats[scope.release_format]||scope.release_format} · ${scope.distribution_channel} · ${scope.aspect_ratio} · ${duration}`;
}

function aspectDimensions(ratio) {
  return {'16:9':[1920,1080],'9:16':[1080,1920],'1:1':[1080,1080],'4:3':[1440,1080],'2.39:1':[3840,1608]}[ratio]||[1920,1080];
}

async function loadProjects() {
  projects = await api('/api/projects');
  productionStatusCache.clear();
  document.querySelector('#project-count').textContent = `${projects.length} production${projects.length === 1 ? '' : 's'}`;
  projectsEl.innerHTML = projects.length ? projects.map(project => `
    <article class="project" data-id="${project.id}"><span class="tag">${safe(project.status)}</span><h3>${safe(project.title)}</h3><p>${safe(project.logline || 'Your story is waiting for its first scene.')}</p><div class="project-scope-summary">${safe(scopeDisplay(project.scope))}</div><footer><span class="era">${safe(project.style_profile?.era_primary || 'Style open')}</span><span>${project.scenes.length} scenes</span><button type="button" data-project-scope="${project.id}">Change scope</button></footer></article>`).join('') : '<div class="empty">No productions yet. Start with a title and release plan—everything else can evolve.</div>';
  document.querySelectorAll('.project').forEach(el => el.onclick = () => openProject(el.dataset.id));
  document.querySelectorAll('[data-project-scope]').forEach(button=>button.onclick=event=>{event.stopPropagation();openWriterRoom(Number(button.dataset.projectScope));});
  renderProductionFlow();
}

async function openProject(id) {
  const project = await api(`/api/projects/${id}`);
  const style = project.style_profile;
  document.querySelector('#detail').innerHTML = `
    <div class="detail-head"><div><p class="eyebrow" style="color:#e84b38">${safe(project.status.toUpperCase())}</p><h2>${safe(project.title)}</h2><p>${safe(project.logline)}</p><div class="detail-scope"><b>RELEASE PLAN</b><span>${safe(scopeDisplay(project.scope))}</span></div><button class="style-launch" data-style-id="${project.id}">Edit Creative DNA</button><button class="writer-launch" data-writer-id="${project.id}">Develop story / change scope</button></div><button class="close" data-close-detail>×</button></div>
    <div class="style-grid"><div class="style-card"><b>ERA BLEND</b>${safe(style.era_primary)} × ${safe(style.era_secondary)}</div><div class="style-card"><b>VISUAL DNA</b>${safe(Object.values(style.visual).join(' · '))}</div><div class="style-card"><b>STORY DNA</b>${safe(Object.values(style.narrative).join(' · '))}</div></div>
    <h3>Scenes</h3>${project.scenes.length ? project.scenes.map(scene => `<div class="scene"><strong>${scene.position}. ${safe(scene.title)}</strong><br><small>${safe(scene.summary)} · ${scene.shots.length} shots</small></div>`).join('') : '<div class="empty">Scene planning will appear here.</div>'}`;
  openWorkspace(detailDialog);
  setupComplianceConsole(project.id);
  setupStorageConsole(project.id);
  document.querySelector('[data-close-detail]').onclick = showDashboard;
  document.querySelector('[data-style-id]').onclick = event => { detailDialog.close(); openStyleLab(Number(event.currentTarget.dataset.styleId)); };
  document.querySelector('[data-writer-id]').onclick = event => { detailDialog.close(); openWriterRoom(Number(event.currentTarget.dataset.writerId)); };
}

const complianceLabels={story:'Story',style:'Creative DNA',characters:'Characters',worlds:'Worlds',shots:'Shots',timeline:'Edit',audio:'Sound',composite:'Finish',render:'Master'};

function renderComplianceConsoleLegacy(data){
  const accepted=Boolean(data.policy.accepted_at),cleared=Boolean(data.release_clearance);
  return `<header><div><p class="eyebrow">ORIGINALITY & RIGHTS</p><h3>Compliance Center</h3><p>Scan the current version before each milestone. Changed work automatically needs a new scan.</p></div><span class="${data.release_ready?'pass':'blocked'}">${data.release_ready?'Release ready':'Release locked'}</span></header><div class="compliance-summary"><span><b>${data.stages.filter(item=>item.status==='pass').length}/${data.stages.length}</b> current scans passed</span><span><b>${data.audit.events}</b> chained audit events</span><span><b>${accepted?'Yes':'No'}</b> creator acknowledgement</span><span><b>${cleared?'Yes':'No'}</b> qualified release clearance</span></div><div class="compliance-stage-grid">${data.stages.map(item=>`<article class="${safe(item.status)}"><header><b>${safe(complianceLabels[item.stage]||item.stage)}</b><span>${item.stale?'Changed':item.status==='pass'?'Passed':item.status==='blocked'?'Blocked':'Scan needed'}</span></header><p>${safe(item.summary)}</p>${item.findings.map(finding=>`<div class="compliance-finding"><b>${safe(finding.message)}</b><small>${safe(finding.evidence)}</small><em>${safe(finding.suggestion)}</em></div>`).join('')}<button type="button" data-compliance-scan="${safe(item.stage)}">${item.status==='pass'?'Scan again':'Run scan'}</button></article>`).join('')}</div><div class="compliance-actions"><button id="scan-all-compliance" class="primary" type="button">Scan every current stage</button><small>Built-in scans detect direct-copy instructions and internal duplicate files. Comprehensive story, trademark, artwork, and music matching requires connected rights databases and qualified review.</small></div>${accepted?'':`<form id="compliance-ack"><h4>Creator responsibility</h4><p>${safe(data.legal_notice)}</p><label>Name<input name="accepted_by" required minlength="2" placeholder="Creator or authorized producer"></label><label class="storage-check"><input name="accepted" type="checkbox" required> I understand that Kizuna assists with screening, while I remain responsible for licenses, clearances, disclosures, and released content.</label><button type="submit">Acknowledge</button></form>`}${cleared?`<div class="release-clearance pass"><b>Release clearance recorded</b><span>${safe(data.release_clearance.confirmed_by)} · ${new Date(data.release_clearance.created_at).toLocaleDateString()}</span><p>${safe(data.release_clearance.notes)}</p></div>`:`<form id="release-clearance"><h4>Qualified release clearance</h4><p>Record counsel, a rights-and-clearance professional, or an authorized studio reviewer after external story, title/trademark, visual, music, voice, and license checks.</p><label>Reviewed by<input name="confirmed_by" required minlength="2"></label><label>Review notes<textarea name="notes" required minlength="10" rows="3"></textarea></label><label>Evidence references<input name="evidence_refs" placeholder="Report IDs or secure document references, comma separated"></label><button type="submit">Record clearance</button></form>`}<footer><b>Audit head</b><code>${safe(data.audit.head_hash||'No events yet')}</code><a href="/api/projects/${data.project_id}/audit-ledger" target="_blank">View audit ledger</a></footer>`;
}

function renderComplianceConsole(data){
  const accepted=Boolean(data.policy.accepted_at),clearanceCurrent=Boolean(data.release_clearance?.current);
  const passing=item=>['pass','pass_with_resolution'].includes(item.status);
  const findingMarkup=(finding,item)=>{
    const resolution=finding.resolution;
    const provider=finding.provider_key&&finding.provider_key!=='local'?`<span class="scanner-pill">${safe(finding.provider_key)}</span>`:'';
    if(resolution)return `<div class="compliance-finding resolved">${provider}<b>${safe(finding.message)}</b><small>${safe(finding.evidence)}</small><div class="resolution-note"><strong>${resolution.status==='rights_verified'?'Rights verified':'False positive'}</strong> by ${safe(resolution.reviewer)}${resolution.evidence_refs.length?` · ${resolution.evidence_refs.map(safe).join(', ')}`:''}</div></div>`;
    const resolutionForm=finding.resolvable===false?'<div class="resolution-note blocked">Restore or disable this scanner before rescanning. Availability failures cannot be overridden.</div>':`<details class="finding-resolution"><summary>Review and resolve</summary><form data-finding-resolution data-scan-id="${item.scan_id}" data-finding-id="${safe(finding.id)}"><label>Decision<select name="status"><option value="rights_verified">Rights verified</option><option value="false_positive">False positive</option></select></label><label>Reviewer<input name="reviewer" required minlength="2" placeholder="Name or role"></label><label>Rationale<textarea name="rationale" required minlength="10" rows="2" placeholder="Why this finding can be cleared"></textarea></label><label>Evidence references<input name="evidence_refs" placeholder="License, report, registration, or secure link"></label><button type="submit">Save resolution</button></form></details>`;
    return `<div class="compliance-finding">${provider}<b>${safe(finding.message)}</b><small>${safe(finding.evidence)}</small><em>${safe(finding.suggestion)}</em>${resolutionForm}</div>`;
  };
  const stageMarkup=data.stages.map(item=>{
    const status=item.stale?'Changed':passing(item)?(item.status==='pass_with_resolution'?'Resolved':'Passed'):item.status==='blocked'?'Blocked':'Scan needed';
    const providers=item.provider_runs.map(run=>`<span class="scanner-pill ${safe(run.status)}" title="${safe(run.error||`${run.matches} matches`)}">${safe(run.provider_key)} · ${safe(run.status)}</span>`).join('');
    return `<article class="${passing(item)?'pass':safe(item.status)}"><header><b>${safe(complianceLabels[item.stage]||item.stage)}</b><span>${status}</span></header><div class="coverage-row"><span>${safe(item.coverage)} coverage</span>${providers}</div><p>${safe(item.summary)}</p>${item.findings.map(finding=>findingMarkup(finding,item)).join('')}<button type="button" data-compliance-scan="${safe(item.stage)}">${passing(item)?'Scan again':'Run scan'}</button></article>`;
  }).join('');
  const scannerMarkup=data.scanners.length?data.scanners.map(scanner=>`<span class="scanner-pill ${scanner.ready?'pass':'blocked'}">${safe(scanner.name)} · ${scanner.ready?'connected':'setup needed'}</span>`).join(''):'<span class="scanner-empty">Built-in preliminary checks only</span>';
  const rightsRows=data.rights_records.map(record=>`<article><div><b>${safe(record.asset_key)}</b><span>${safe(record.source_type.replaceAll('_',' '))}</span></div><p>${safe(record.rights_holder||record.license_name||'Creator-declared source')}</p><small>${record.evidence_refs.length?record.evidence_refs.map(safe).join(' · '):'No external evidence reference'}</small></article>`).join('')||'<div class="compute-empty">No asset rights records yet. Add them as final artwork, music, voices, and footage enter the production.</div>';
  const assetOptions=data.asset_candidates.map(asset=>`<option value="${safe(asset.asset_key)}">${safe(asset.asset_key)}</option>`).join('');
  const clearanceMarkup=data.release_clearance&&clearanceCurrent?`<div class="release-clearance pass"><b>Release clearance recorded</b><span>${safe(data.release_clearance.confirmed_by)} · ${new Date(data.release_clearance.created_at).toLocaleDateString()}</span><p>${safe(data.release_clearance.notes)}</p></div>`:`${data.release_clearance?'<div class="release-clearance stale"><b>Release clearance needs renewal</b><p>Scans, finding decisions, or rights records changed after the last review.</p></div>':''}<form id="release-clearance"><h4>Qualified release clearance</h4><p>Record counsel, a rights-and-clearance professional, or an authorized studio reviewer after external story, title/trademark, visual, music, voice, and license checks.</p><label>Reviewed by<input name="confirmed_by" required minlength="2"></label><label>Review notes<textarea name="notes" required minlength="10" rows="3"></textarea></label><label>Evidence references<input name="evidence_refs" placeholder="Report IDs or secure document references, comma separated"></label><button type="submit">Record clearance</button></form>`;
  return `<header><div><p class="eyebrow">ORIGINALITY & RIGHTS</p><h3>Compliance Center</h3><p>Scan the current version, resolve findings with evidence, and keep asset rights attached to the production.</p></div><span class="${data.release_ready?'pass':'blocked'}">${data.release_ready?'Release ready':'Release locked'}</span></header><div class="compliance-summary"><span><b>${data.stages.filter(passing).length}/${data.stages.length}</b> current scans passed</span><span><b>${data.audit.events}</b> chained audit events</span><span><b>${accepted?'Yes':'No'}</b> creator acknowledgement</span><span><b>${clearanceCurrent?'Yes':'No'}</b> current release clearance</span></div><div class="scanner-coverage"><b>Originality services</b><div>${scannerMarkup}</div><small>Connected services receive the current stage content. Manage endpoints and credentials in Settings.</small></div><div class="compliance-stage-grid">${stageMarkup}</div><div class="compliance-actions"><button id="scan-all-compliance" class="primary" type="button">Scan every current stage</button><small>Kizuna fails closed when a configured scanner cannot respond. Built-in checks remain preliminary; commercial release still needs appropriate databases and qualified review.</small></div><section class="rights-register"><header><div><h4>Asset rights register</h4><p>Attach provenance and licenses to the actual production files.</p></div><span>${data.rights_records.length}/${data.asset_candidates.length} documented</span></header><div class="rights-list">${rightsRows}</div>${assetOptions?`<details><summary>Add or update an asset record</summary><form id="asset-rights-form"><label>Asset<select name="asset_key">${assetOptions}</select></label><label>Source<select name="source_type"><option value="original">Original work</option><option value="ai_generated">AI generated</option><option value="user_owned">User owned</option><option value="commissioned">Commissioned</option><option value="licensed">Licensed</option><option value="stock">Stock library</option><option value="public_domain">Public domain</option></select></label><label>Rights holder<input name="rights_holder"></label><label>License<input name="license_name"></label><label>Permitted uses<input name="permitted_uses" placeholder="commercial, streaming, social"></label><label>Territories<input name="territories" placeholder="worldwide, US, JP"></label><label>License expires<input name="expires_at" type="datetime-local"></label><label>Evidence references<input name="evidence_refs" placeholder="Required for licensed, stock, commissioned, and public-domain sources"></label><label>Reviewer<input name="reviewer" required minlength="2"></label><label class="wide">Notes<textarea name="notes" rows="2"></textarea></label><button type="submit">Save rights record</button></form></details>`:'<small>Create or import production media before adding rights records.</small>'}</section>${accepted?'':`<form id="compliance-ack"><h4>Creator responsibility</h4><p>${safe(data.legal_notice)}</p><label>Name<input name="accepted_by" required minlength="2" placeholder="Creator or authorized producer"></label><label class="storage-check"><input name="accepted" type="checkbox" required> I understand that Kizuna assists with screening, while I remain responsible for licenses, clearances, disclosures, and released content.</label><button type="submit">Acknowledge</button></form>`}${clearanceMarkup}<footer><b>Audit head</b><code>${safe(data.audit.head_hash||'No events yet')}</code><a href="/api/projects/${data.project_id}/audit-ledger" target="_blank">View audit ledger</a></footer>`;
}

async function setupComplianceConsole(projectId){
  const detail=document.querySelector('#detail');let host=detail.querySelector('#compliance-console');if(!host){host=document.createElement('section');host.id='compliance-console';host.className='compliance-console';host.innerHTML='<div class="settings-loading">Checking originality and rights status...</div>';detail.appendChild(host);}
  try{
    const data=await api(`/api/projects/${projectId}/compliance`);host.innerHTML=renderComplianceConsole(data);
    host.querySelectorAll('[data-compliance-scan]').forEach(button=>button.onclick=()=>runComplianceScan(projectId,button.dataset.complianceScan,button));
    host.querySelector('#scan-all-compliance').onclick=event=>runComplianceScan(projectId,'all',event.currentTarget);
    host.querySelectorAll('[data-finding-resolution]').forEach(form=>form.addEventListener('submit',async event=>{event.preventDefault();const current=event.currentTarget,button=current.querySelector('button');button.disabled=true;button.textContent='Saving...';try{await api(`/api/projects/${projectId}/compliance/scans/${current.dataset.scanId}/findings/${encodeURIComponent(current.dataset.findingId)}/resolve`,{method:'POST',body:JSON.stringify({status:current.elements.status.value,reviewer:current.elements.reviewer.value,rationale:current.elements.rationale.value,evidence_refs:current.elements.evidence_refs.value.split(',').map(item=>item.trim()).filter(Boolean)})});await Promise.all([setupComplianceConsole(projectId),refreshProductionStatus(projectId,true)]);}catch(error){button.disabled=false;button.textContent=error.message;}}));
    host.querySelector('#asset-rights-form')?.addEventListener('submit',async event=>{event.preventDefault();const form=event.currentTarget,button=form.querySelector('button');button.disabled=true;button.textContent='Saving...';try{await api(`/api/projects/${projectId}/compliance/asset-rights`,{method:'PUT',body:JSON.stringify({asset_key:form.elements.asset_key.value,source_type:form.elements.source_type.value,rights_holder:form.elements.rights_holder.value,license_name:form.elements.license_name.value,permitted_uses:form.elements.permitted_uses.value.split(',').map(item=>item.trim()).filter(Boolean),territories:form.elements.territories.value.split(',').map(item=>item.trim()).filter(Boolean),expires_at:form.elements.expires_at.value||null,evidence_refs:form.elements.evidence_refs.value.split(',').map(item=>item.trim()).filter(Boolean),reviewer:form.elements.reviewer.value,notes:form.elements.notes.value})});await setupComplianceConsole(projectId);}catch(error){button.disabled=false;button.textContent=error.message;}});
    host.querySelector('#compliance-ack')?.addEventListener('submit',async event=>{event.preventDefault();const form=event.currentTarget;await api(`/api/projects/${projectId}/compliance/acknowledge`,{method:'POST',body:JSON.stringify({accepted:form.elements.accepted.checked,accepted_by:form.elements.accepted_by.value})});await setupComplianceConsole(projectId);});
    host.querySelector('#release-clearance')?.addEventListener('submit',async event=>{event.preventDefault();const form=event.currentTarget;await api(`/api/projects/${projectId}/compliance/release-clearance`,{method:'POST',body:JSON.stringify({confirmed_by:form.elements.confirmed_by.value,notes:form.elements.notes.value,evidence_refs:form.elements.evidence_refs.value.split(',').map(item=>item.trim()).filter(Boolean)})});await setupComplianceConsole(projectId);});
  }catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

async function runComplianceScan(projectId,stage,button){
  button.disabled=true;button.textContent=stage==='all'?'Scanning production...':'Scanning...';
  try{await api(`/api/projects/${projectId}/compliance/scan`,{method:'POST',body:JSON.stringify({stage})});await Promise.all([setupComplianceConsole(projectId),refreshProductionStatus(projectId,true)]);}catch(error){button.disabled=false;button.textContent=error.message;}
}

function mediaBytes(value){if(value<1024)return`${value} B`;if(value<1024**2)return`${(value/1024).toFixed(1)} KB`;if(value<1024**3)return`${(value/1024**2).toFixed(1)} MB`;return`${(value/1024**3).toFixed(2)} GB`;}

function renderMediaFootprint(media,storage){const policy=media.policy,summary=media.summary,nodeOptions=`<option value="">Any Hive computer</option>${media.nodes.map(node=>`<option value="${safe(node.node_key)}" ${policy.preferred_node_key===node.node_key?'selected':''}>${safe(node.name)} · ${safe(node.status)}</option>`).join('')}`;return`<section class="media-footprint"><header><div><p class="eyebrow">MEDIA FOOTPRINT</p><h4>Keep the story here, put large files where they belong</h4><p>Kizuna keeps decisions, lineage, checksums, and lightweight previews. Originals can live on Hive computers or off-server storage.</p></div><span>${summary.assets} indexed</span></header><div class="media-totals"><span><b>${mediaBytes(summary.server_original_bytes)}</b> originals on Kizuna</span><span><b>${mediaBytes(summary.hive_original_bytes)}</b> originals on Hive</span><span><b>${mediaBytes(summary.lightweight_server_bytes)}</b> previews on Kizuna</span><span><b>${summary.verified_originals}</b> verified files</span></div><div class="media-transfer-state"><span><b>${summary.working_media_jobs}</b> previews processing</span><span><b>${summary.queued_transfers}</b> transfers waiting</span><span><b>${summary.active_transfers}</b> files moving</span><span><b>${summary.completed_transfers}</b> verified transfers</span><span><b>${summary.cleanup_eligible_assets}</b> safe for future cleanup</span></div><div class="media-preview-strip">${media.assets.filter(item=>item.preview_uri).slice(0,8).map(item=>`<article><img src="${safe(item.preview_uri)}" alt=""><span>${safe(item.name)}</span><small>${item.residencies.map(place=>place.backend).filter((value,index,array)=>array.indexOf(value)===index).map(safe).join(' · ')}</small></article>`).join('')||'<div class="compute-empty">Media thumbnails will appear as artwork is created.</div>'}</div><details class="media-policy"><summary>Choose where full-resolution files live</summary><div><label>Original file home<select id="media-original-strategy"><option value="server" ${policy.original_strategy==='server'?'selected':''}>Kizuna server</option><option value="hive" ${policy.original_strategy==='hive'?'selected':''} ${media.nodes.length?'':'disabled'}>My Hive computers${media.nodes.length?'':' · connect one first'}</option><option value="s3" ${policy.original_strategy==='s3'?'selected':''} ${storage.s3.ready?'':'disabled'}>S3-compatible vault${storage.s3.ready?'':' · setup needed'}</option></select></label><label>Preferred computer<select id="media-preferred-node">${nodeOptions}</select></label><label>Verified copies before cleanup<input id="media-replicas" type="number" min="1" max="5" value="${policy.minimum_replicas}"></label><label>Thumbnail width<input id="media-thumbnail-width" type="number" min="160" max="1920" value="${policy.thumbnail_width}"></label><label>Editing proxy width<input id="media-proxy-width" type="number" min="320" max="3840" value="${policy.proxy_width}"></label><label class="storage-check"><input id="media-proxies" type="checkbox" ${policy.keep_server_proxies?'checked':''}> Keep lightweight proxies in Kizuna</label><label class="storage-check"><input id="media-evict" type="checkbox" ${policy.evict_server_originals?'checked':''}> Remove server originals only after verified copies exist</label><button id="save-media-policy" type="button">Save media policy</button><button id="queue-media-transfers" class="primary" type="button" ${policy.original_strategy==='hive'&&media.nodes.length?'':'disabled'}>Send missing copies to Hive</button></div><small>Transfers use temporary files and checksum verification. Nothing on the server is deleted by this action.</small></details></section>`;}

function renderCleanupReview(cleanup){const visible=cleanup.items.filter(item=>item.status!=='blocked').concat(cleanup.items.filter(item=>item.status==='blocked')).slice(0,12);return`<details class="cleanup-review"><summary><span>Cleanup review</span><b>${cleanup.summary.eligible} eligible · ${cleanup.summary.approved} approved</b></summary><header><div><p class="eyebrow">ORIGINAL SAFETY</p><h4>Creator approval before any original can be removed</h4><p>Replica checks must be newer than ${cleanup.verification_hours} hours. Approval is recorded, but deletion is disabled in this release.</p></div></header><div class="cleanup-list">${visible.map(item=>`<article class="${safe(item.status)}"><div><b>${safe(item.name)}</b><small>${mediaBytes(item.source_size_bytes)} · ${item.verified_replicas}/${item.required_replicas} fresh replicas</small><em>${safe(item.reason)}</em></div>${item.status==='eligible'?`<button type="button" data-cleanup-approve="${safe(item.asset_key)}">Approve</button>`:item.status==='approved'?`<button type="button" data-cleanup-revoke="${safe(item.asset_key)}">Revoke</button>`:`<span>Blocked</span>`}</article>`).join('')||'<div class="compute-empty">No server originals are indexed yet.</div>'}</div></details>`;}

async function setupStorageConsole(projectId) {
  const detail=document.querySelector('#detail');if(!detail.querySelector('#storage-console'))detail.insertAdjacentHTML('beforeend','<section id="storage-console" class="production-storage"><div class="storage-loading">Loading production storage...</div></section>');
  const host=detail.querySelector('#storage-console');
  try {
    const [policy,schedule,storage,media,cleanup,backups,links,studio]=await Promise.all([api(`/api/projects/${projectId}/storage-policy`),api(`/api/projects/${projectId}/backup-schedule`),api('/api/settings/storage'),api(`/api/projects/${projectId}/media-index`),api(`/api/projects/${projectId}/media-cleanup`),api(`/api/projects/${projectId}/backups`),api(`/api/projects/${projectId}/delivery-links`),api(`/api/projects/${projectId}/compositor`)]);
    const assets=studio.assets.filter(asset=>asset.active);
    host.innerHTML=`<header><div><p class="eyebrow">PRODUCTION VAULT</p><h3>Backups & secure delivery</h3><p>Keep a recoverable copy here or automatically send it to independent S3-compatible storage.</p></div><span>${safe(policy.backend==='s3'?'off-server':'local')} vault</span></header><div class="storage-grid"><section><h4>Backup destination</h4><label>Save copies to<select id="storage-backend"><option value="local" ${policy.backend==='local'?'selected':''}>This Kizuna server</option><option value="s3" ${policy.backend==='s3'?'selected':''} ${storage.s3.ready?'':'disabled'}>Off-server S3-compatible storage${storage.s3.ready?'':' · setup needed'}</option></select></label><div class="storage-destination ${storage.s3.ready?'ready':''}"><b>${storage.s3.ready?'Off-server vault ready':'Off-server vault not configured'}</b><span>${storage.s3.ready?`${safe(storage.s3.bucket)}${storage.s3.endpoint?' · '+safe(storage.s3.endpoint):''}`:'Add the S3 environment settings in Studio Settings or Coolify.'}</span></div><div class="storage-fields"><label>Keep for days<input id="storage-retention" type="number" min="1" max="3650" value="${policy.retention_days}"></label><label>Maximum copies<input id="storage-max" type="number" min="1" max="100" value="${policy.max_backups}"></label></div><label class="storage-check"><input id="storage-media" type="checkbox" ${policy.include_media?'checked':''}> Include generated media</label><div class="backup-schedule"><label class="storage-check"><input id="storage-schedule" type="checkbox" ${schedule.enabled?'checked':''}> Back up automatically</label><label>Every<select id="storage-interval"><option value="6" ${schedule.interval_hours===6?'selected':''}>6 hours</option><option value="12" ${schedule.interval_hours===12?'selected':''}>12 hours</option><option value="24" ${schedule.interval_hours===24?'selected':''}>day</option><option value="168" ${schedule.interval_hours===168?'selected':''}>week</option></select></label><small>${schedule.last_run_at?`Last ${safe(schedule.last_status)} · ${new Date(schedule.last_run_at).toLocaleString()}`:schedule.enabled?`First run ${new Date(schedule.next_run_at).toLocaleString()}`:'Automatic backups are off.'}${schedule.last_error?` · ${safe(schedule.last_error)}`:''}</small></div><div class="storage-actions"><button id="save-storage-policy" type="button">Save vault settings</button><button id="create-backup" class="primary" type="button">Back up now</button></div><div class="vault-list">${backups.length?backups.map(item=>`<a href="${item.download_url}"><b>${safe(item.filename)}</b><small>${safe(item.backend==='s3'?'off-server':'local')} · ${item.asset_count} assets · ${(item.size_bytes/1024).toFixed(1)} KB · ${safe(item.checksum_sha256.slice(0,10))}</small></a>`).join(''):'<span>No backups yet.</span>'}</div></section><section><h4>Expiring delivery link</h4><label>Approved asset<select id="delivery-asset">${assets.length?assets.map(asset=>`<option value="${safe(asset.uri)}">${safe(asset.name)} · v${asset.version}</option>`).join(''):'<option value="">Approve an asset first</option>'}</select></label><label>Label<input id="delivery-label" value="Studio review"></label><div class="storage-fields"><label>Expires in hours<input id="delivery-hours" type="number" min="1" max="720" value="72"></label><label>Download limit<input id="delivery-limit" type="number" min="1" max="10000" value="10"></label></div><button id="create-delivery" type="button" ${assets.length?'':'disabled'}>Create secure link</button><div id="delivery-result"></div><div class="vault-list">${links.length?links.map(link=>`<span><b>${safe(link.label)}</b><small>${link.download_count}/${link.max_downloads} downloads · ${link.revoked?'revoked':'expires '+new Date(link.expires_at).toLocaleDateString()}</small></span>`).join(''):'<span>No delivery links yet.</span>'}</div></section></div>`;
    host.querySelector('.storage-grid').insertAdjacentHTML('beforebegin',renderMediaFootprint(media,storage)+renderCleanupReview(cleanup));
    document.querySelector('#save-media-policy').onclick=async()=>{await api(`/api/projects/${projectId}/media-storage-policy`,{method:'PUT',body:JSON.stringify({original_strategy:document.querySelector('#media-original-strategy').value,preferred_node_key:document.querySelector('#media-preferred-node').value,keep_server_proxies:document.querySelector('#media-proxies').checked,thumbnail_width:Number(document.querySelector('#media-thumbnail-width').value),proxy_width:Number(document.querySelector('#media-proxy-width').value),minimum_replicas:Number(document.querySelector('#media-replicas').value),evict_server_originals:document.querySelector('#media-evict').checked})});await setupStorageConsole(projectId);};
    document.querySelector('#queue-media-transfers').onclick=async event=>{event.currentTarget.disabled=true;event.currentTarget.textContent='Queueing copies…';await api(`/api/projects/${projectId}/media-transfers/queue`,{method:'POST',body:'{}'});await setupStorageConsole(projectId);};
    document.querySelectorAll('[data-cleanup-approve]').forEach(button=>button.onclick=async()=>{await api(`/api/projects/${projectId}/media-cleanup`,{method:'PUT',body:JSON.stringify({asset_key:button.dataset.cleanupApprove,action:'approve',note:'Creator approved for a future guarded cleanup run.'})});await setupStorageConsole(projectId);});
    document.querySelectorAll('[data-cleanup-revoke]').forEach(button=>button.onclick=async()=>{await api(`/api/projects/${projectId}/media-cleanup`,{method:'PUT',body:JSON.stringify({asset_key:button.dataset.cleanupRevoke,action:'revoke',note:'Creator revoked cleanup approval.'})});await setupStorageConsole(projectId);});
    document.querySelector('#save-storage-policy').onclick=async()=>{await Promise.all([api(`/api/projects/${projectId}/storage-policy`,{method:'PUT',body:JSON.stringify({backend:document.querySelector('#storage-backend').value,retention_days:Number(document.querySelector('#storage-retention').value),max_backups:Number(document.querySelector('#storage-max').value),include_media:document.querySelector('#storage-media').checked})}),api(`/api/projects/${projectId}/backup-schedule`,{method:'PUT',body:JSON.stringify({enabled:document.querySelector('#storage-schedule').checked,interval_hours:Number(document.querySelector('#storage-interval').value)})})]);await setupStorageConsole(projectId);};
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

async function loadWriterScope(projectId) {
  const host=document.querySelector('#writer-scope-card');if(!host)return;host.innerHTML='<div class="settings-loading">Loading release plan...</div>';
  try{const scope=await api(`/api/projects/${projectId}/scope`);renderWriterScope(scope);const brief=projects.find(project=>project.id===projectId)?.story_brief,form=document.querySelector('#writer-form');if(!brief){form.elements.format.value={one_off:'short film',trailer:'trailer',feature_film:'feature film',ongoing_series:'episode',limited_series:'limited series'}[scope.release_format]||'short film';form.elements.target_duration_minutes.value=Math.max(1,Math.ceil(scope.target_duration_seconds/60));}}catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

function renderWriterScope(scope) {
  const host=document.querySelector('#writer-scope-card'),minutes=scope.target_duration_seconds%60===0?scope.target_duration_seconds/60:scope.target_duration_seconds,status=scope.story_status==='review_needed'?'Outline needs adaptation':scope.story_status==='aligned'?'Story aligned':'Story not started',unit=scope.target_duration_seconds%60===0?'minutes':'seconds';
  host.innerHTML=`<header><div><p class="eyebrow">RELEASE PLAN</p><b>${safe(scope.summary)}</b></div><span class="${safe(scope.story_status)}">${safe(status)}</span></header><div class="scope-guidance">${scope.writing_guidance.map(item=>`<p>${safe(item)}</p>`).join('')}</div><details><summary>Change production scope</summary><div id="writer-scope-editor" class="scope-editor"><label>Production type<select name="release_format"><option value="one_off">One-off</option><option value="trailer">Trailer / teaser</option><option value="feature_film">Feature film</option><option value="ongoing_series">Ongoing series</option><option value="limited_series">Limited series</option></select></label><label>Distribution<select name="distribution_channel"><option>YouTube</option><option>TikTok</option><option>Instagram Reels</option><option>Streaming platform</option><option>Theatrical / festival</option><option>Broadcast</option><option>Web / custom</option></select></label><label>Screen shape<select name="aspect_ratio"><option value="16:9">Landscape 16:9</option><option value="9:16">Tall 9:16</option><option value="1:1">Square 1:1</option><option value="4:3">Classic 4:3</option><option value="2.39:1">Cinema 2.39:1</option></select></label><label>Length per release<span class="duration-pair"><input name="target_length" type="number" min="1" value="${minutes}"><select name="target_unit"><option value="minutes" ${unit==='minutes'?'selected':''}>minutes</option><option value="seconds" ${unit==='seconds'?'selected':''}>seconds</option></select></span></label><div class="scope-counts"><label>Releases<input name="installment_count" type="number" min="1" max="1000" value="${scope.installment_count}"></label><label>Seasons<input name="season_count" type="number" min="1" max="100" value="${scope.season_count}"></label></div><label>Notes<textarea name="notes" rows="2">${safe(scope.notes)}</textarea></label><button class="primary" type="button">Save new scope</button></div></details>`;
  const editor=host.querySelector('#writer-scope-editor');editor.querySelector('[name="release_format"]').value=scope.release_format;editor.querySelector('[name="distribution_channel"]').value=scope.distribution_channel;editor.querySelector('[name="aspect_ratio"]').value=scope.aspect_ratio;editor.querySelector('button').onclick=()=>saveWriterScope(editor,scope.project_id);
}

async function saveWriterScope(editor,projectId) {
  const field=name=>editor.querySelector(`[name="${name}"]`),[width,height]=aspectDimensions(field('aspect_ratio').value),seconds=Math.round(Number(field('target_length').value)*(field('target_unit').value==='minutes'?60:1)),button=editor.querySelector('button');button.disabled=true;button.textContent='Updating production...';
  try{const scope=await api(`/api/projects/${projectId}/scope`,{method:'PUT',body:JSON.stringify({distribution_channel:field('distribution_channel').value,release_format:field('release_format').value,aspect_ratio:field('aspect_ratio').value,width,height,target_duration_seconds:seconds,installment_count:Number(field('installment_count').value),season_count:Number(field('season_count').value),notes:field('notes').value})});await loadProjects();fillStory(projectId);renderWriterScope(scope);refreshAssistantContext();}catch(error){button.disabled=false;button.textContent='Save new scope';editor.insertAdjacentHTML('beforeend',`<div class="job-error">${safe(error.message)}</div>`);}
}

async function openWriterRoom(projectId) {
  if (!projects.length) await loadProjects();
  if (!projects.length) { projectDialog.showModal(); return; }
  const projectSelect = document.querySelector('#writer-project');
  projectSelect.innerHTML = options(projects.map(p => ({id:String(p.id), label:p.title})), String(projectId || projects[0].id));
  projectSelect.onchange = () => {const id=Number(projectSelect.value);fillStory(id);loadWriterScope(id);};
  fillStory(Number(projectSelect.value));
  loadWriterScope(Number(projectSelect.value));
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
  renderConnectedStoryMap(result,brief);
  document.querySelector('#save-outline').onclick = saveOutline;
}

function storyMapData(project,brief) {
  return brief.beats.map((beat,index)=>{const scene=project?.scenes?.find(item=>Number(item.position)===Number(beat.position)),shots=scene?.shots||[],planned=shots.filter(shot=>shot.plan),characterIds=[...new Set(planned.flatMap(shot=>shot.plan.character_ids||[]))],locationIds=[...new Set(planned.map(shot=>shot.plan.location_id).filter(Boolean))],status=shots.length&&planned.length===shots.length?'covered':scene?'in_progress':'outline';return{beat,index,scene,shots,planned,status,characters:(project?.characters||[]).filter(item=>characterIds.includes(item.id)),locations:(project?.locations||[]).filter(item=>locationIds.includes(item.id))};});
}

function renderConnectedStoryMap(result,brief) {
  const projectId=Number(document.querySelector('#writer-project').value),project=projects.find(item=>item.id===projectId),map=storyMapData(project,brief),quarter=Math.max(1,Math.ceil(map.length/4)),groups=[{label:'SETUP',items:map.slice(0,quarter)},{label:'DEVELOPMENT',items:map.slice(quarter,map.length-quarter)},{label:'RESOLUTION',items:map.slice(map.length-quarter)}].filter(group=>group.items.length),covered=map.filter(item=>item.status==='covered').length,initial=map.find(item=>item.status!=='covered')||map[0];
  result.insertAdjacentHTML('afterbegin',`<section class="story-flow-map connected-story-map"><header><div><span>STORY MAP</span><b>See how the outline connects to production</b></div><small>${covered}/${map.length} beats camera-ready</small></header><nav class="story-map-mode" aria-label="Story map focus"><button type="button" class="active" data-story-map-mode="production">Production</button><button type="button" data-story-map-mode="characters">Character arcs</button></nav><div data-story-map-panel="production"><div class="story-map-acts">${groups.map(group=>`<section><span>${group.label}</span><div>${group.items.map(item=>`<button type="button" class="${item.status}" data-story-node="${safe(item.beat.position)}"><i>${safe(item.beat.position)}</i><b>${safe(item.beat.name)}</b><small>${item.status==='covered'?'Camera-ready':item.scene?'Needs coverage':'Outline only'}</small></button>`).join('')}</div></section>`).join('')}</div><div id="story-map-detail" class="story-map-detail"></div></div><div class="character-arc-map" data-story-map-panel="characters" hidden><div class="character-arc-loading">Reading character profiles and screen appearances...</div></div></section>`);
  const selectNode=position=>{const item=map.find(entry=>String(entry.beat.position)===String(position));if(!item)return;result.querySelectorAll('[data-story-node]').forEach(button=>button.classList.toggle('active',button.dataset.storyNode===String(position)));renderStoryMapDetail(result,project,item);};
  const setMode=mode=>{result.querySelectorAll('[data-story-map-mode]').forEach(button=>button.classList.toggle('active',button.dataset.storyMapMode===mode));result.querySelectorAll('[data-story-map-panel]').forEach(panel=>panel.hidden=panel.dataset.storyMapPanel!==mode);};
  result.querySelectorAll('[data-story-map-mode]').forEach(button=>button.onclick=()=>setMode(button.dataset.storyMapMode));result.querySelectorAll('[data-story-node]').forEach(button=>button.onclick=()=>selectNode(button.dataset.storyNode));selectNode(initial?.beat.position);hydrateCharacterArcMap(result,project,map,position=>{setMode('production');selectNode(position);});
}

async function hydrateCharacterArcMap(result,project,map,openBeat) {
  const host=result.querySelector('.character-arc-map');if(!host||!project)return;
  const development=await Promise.all((project.characters||[]).map(async character=>{const [profile,relationships]=await Promise.all([api(`/api/characters/${character.id}/story-profile`).catch(()=>null),api(`/api/characters/${character.id}/relationships`).catch(()=>[])]);return{character,profile,relationships};}));
  if(!host.isConnected)return;
  if(!development.length){host.innerHTML='<div class="character-arc-empty"><b>No cast yet</b><span>Add a character to begin tracking emotional arcs through the story.</span><button type="button" data-open-character-studio>Add a character</button></div>';host.querySelector('button').onclick=()=>openCharacterStudio(project.id);return;}
  host.innerHTML=`<div class="arc-character-picker" aria-label="Choose character">${development.map((item,index)=>`<button type="button" class="${index===0?'active':''}" data-arc-character="${item.character.id}"><i>${safe(item.character.name.slice(0,1).toUpperCase())}</i><span><b>${safe(item.character.name)}</b><small>${safe(item.character.role||'Character')}</small></span></button>`).join('')}</div><div class="arc-character-detail"></div>`;
  const selectCharacterArc=characterId=>{const item=development.find(entry=>entry.character.id===Number(characterId));if(!item)return;host.querySelectorAll('[data-arc-character]').forEach(button=>button.classList.toggle('active',Number(button.dataset.arcCharacter)===item.character.id));renderCharacterArcLane(host,item,development,map,openBeat,project.id);};
  host.querySelectorAll('[data-arc-character]').forEach(button=>button.onclick=()=>selectCharacterArc(button.dataset.arcCharacter));selectCharacterArc(development[0].character.id);
}

function renderCharacterArcLane(host,item,development,map,openBeat,projectId) {
  const detail=host.querySelector('.arc-character-detail'),appearances=map.filter(beat=>beat.characters.some(character=>character.id===item.character.id)),middle=(map.length-1)/2,turn=appearances.reduce((closest,beat)=>!closest||Math.abs(beat.index-middle)<Math.abs(closest.index-middle)?beat:closest,null),milestones={start:appearances[0],turn,end:appearances.at(-1)},profile=item.profile||{},phases=[['start','Beginning',profile.arc_start],['turn','Turning point',profile.arc_turn],['end','Ending',profile.arc_end]],relationshipRows=item.relationships.map(relationship=>{const other=development.find(entry=>entry.character.id===relationship.target_character_id),shared=other?map.filter(beat=>beat.characters.some(character=>character.id===item.character.id)&&beat.characters.some(character=>character.id===other.character.id)):[];return{relationship,shared};}),gaps=[];
  if(!item.profile)gaps.push('Story profile not written');if(!appearances.length)gaps.push('Not assigned to any planned shots');else if(new Set(appearances.map(beat=>beat.index)).size<3)gaps.push('Needs more appearances to show a full change');if(item.profile&&phases.some(phase=>!phase[2]))gaps.push('Emotional arc has unfinished phases');
  detail.innerHTML=`<header class="arc-map-head"><div><p class="eyebrow">EMOTIONAL THROUGHLINE</p><h4>${safe(item.character.name)}</h4><p>${safe(item.character.want||item.character.role||'Track this character through the story.')}</p></div><button type="button" data-edit-character-story>Edit character story</button></header><div class="arc-beat-lane">${map.map(beat=>{const visible=appearances.includes(beat),marks=Object.entries(milestones).filter(([,value])=>value===beat).map(([key])=>key[0].toUpperCase()).join('/');return`<button type="button" class="${visible?'appears':'absent'} ${marks?'milestone':''}" data-arc-beat="${safe(beat.beat.position)}" title="${safe(beat.beat.name)}"><i>${marks||safe(beat.beat.position)}</i><b>${safe(beat.beat.name)}</b><small>${visible?'On screen':'No planned appearance'}</small></button>`;}).join('')}</div><div class="arc-phase-grid">${phases.map(([key,label,copy])=>{const beat=milestones[key];return`<article class="${copy?'defined':'empty'}"><span>${safe(label)}</span><b>${beat?`Suggested at beat ${safe(beat.beat.position)}`:'No placement yet'}</b><p>${safe(copy||'Define this phase in Character Studio.')}</p>${beat?`<button type="button" data-phase-beat="${safe(beat.beat.position)}">${safe(beat.beat.name)}</button>`:''}</article>`;}).join('')}</div><section class="arc-relationships"><header><b>Relationship intersections</b><small>Shared planned appearances</small></header>${relationshipRows.length?relationshipRows.map(row=>`<article><span><b>${safe(row.relationship.target_name)}</b><small>${safe(row.relationship.relationship_type)}</small></span><p>${safe(row.relationship.tension||row.relationship.arc||'Connection defined')}</p><em>${row.shared.length?`${row.shared.length} shared beat${row.shared.length===1?'':'s'}`:'No shared beats yet'}</em></article>`).join(''):'<div class="arc-relationship-empty">No relationships defined for this character yet.</div>'}</section>${gaps.length?`<div class="arc-map-gaps"><b>Needs attention</b>${gaps.map(gap=>`<span>${safe(gap)}</span>`).join('')}</div>`:'<div class="story-map-ready">This character has a defined arc and visible story coverage.</div>'}`;
  detail.querySelector('[data-edit-character-story]').onclick=async()=>{await openCharacterStudio(projectId);selectCharacter(projectId,item.character.id);setCharacterView('story');};detail.querySelectorAll('[data-arc-beat],[data-phase-beat]').forEach(button=>button.onclick=()=>openBeat(button.dataset.arcBeat||button.dataset.phaseBeat));
}

function renderStoryMapDetail(result,project,item) {
  const host=result.querySelector('#story-map-detail'),missing=[];if(!item.scene)missing.push('Scene not built');else if(!item.shots.length)missing.push('Shot coverage not built');else if(item.planned.length<item.shots.length)missing.push(`${item.shots.length-item.planned.length} shot${item.shots.length-item.planned.length===1?'':'s'} need camera plans`);if(item.scene&&!item.characters.length)missing.push('No characters assigned');if(item.scene&&!item.locations.length)missing.push('No location assigned');
  host.innerHTML=`<div class="story-map-copy"><p class="eyebrow">BEAT ${safe(item.beat.position)}</p><h4>${safe(item.beat.name)}</h4><p>${safe(item.beat.summary)}</p><button type="button" data-open-outline="${safe(item.beat.position)}">Open outline card</button></div><div class="story-map-links"><div class="story-chain"><span><small>BEAT</small>${safe(item.beat.name)}</span><i>&rarr;</i><span><small>SCENE</small>${safe(item.scene?.title||'Not built')}</span><i>&rarr;</i><button type="button" data-open-coverage><small>SHOTS</small>${item.shots.length?`${item.planned.length}/${item.shots.length} planned`:'Not built'}</button></div><div class="story-map-resources"><span><small>CAST</small>${item.characters.length?item.characters.map(character=>`<button type="button" data-map-character="${character.id}">${safe(character.name)}</button>`).join(''):'<em>Not assigned</em>'}</span><span><small>WORLD</small>${item.locations.length?item.locations.map(location=>`<button type="button" data-map-location="${location.id}">${safe(location.name)}</button>`).join(''):'<em>Not assigned</em>'}</span></div>${missing.length?`<div class="story-map-gaps"><b>Next production needs</b>${missing.map(gap=>`<span>${safe(gap)}</span>`).join('')}</div>`:'<div class="story-map-ready">This beat has complete camera coverage.</div>'}</div>`;
  host.querySelector('[data-open-outline]').onclick=()=>result.querySelector(`.beat[data-position="${CSS.escape(String(item.beat.position))}"]`)?.scrollIntoView({behavior:'smooth',block:'center'});
  host.querySelector('[data-open-coverage]').onclick=async()=>{await openShotPlanner(project.id);if(item.shots[0])selectShot(project.id,item.shots[0].id);};
  host.querySelectorAll('[data-map-character]').forEach(button=>button.onclick=async()=>{await openCharacterStudio(project.id);selectCharacter(project.id,Number(button.dataset.mapCharacter));});
  host.querySelectorAll('[data-map-location]').forEach(button=>button.onclick=async()=>{await openWorldStudio(project.id);selectWorld(project.id,Number(button.dataset.mapLocation));});
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
  document.querySelector('#character-story-panel').innerHTML = '<div class="character-story-empty">Save or select a character to develop their history, arc, and relationships.</div>';
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
  loadCharacterStory(projectId,characterId);
}

async function loadCharacterStory(projectId,characterId) {
  const [profile,relationships]=await Promise.all([api(`/api/characters/${characterId}/story-profile`).catch(()=>null),api(`/api/characters/${characterId}/relationships`)]);renderCharacterStoryPanel(projectId,profile,relationships);
}

function renderCharacterStoryPanel(projectId,profile,relationships) {
  const project=projects.find(item=>item.id===projectId),character=project?.characters.find(item=>item.id===activeCharacterId),others=(project?.characters||[]).filter(item=>item.id!==activeCharacterId),value=key=>safe(profile?.[key]||''),host=document.querySelector('#character-story-panel');if(!character){host.innerHTML='<div class="character-story-empty">Select a character to begin.</div>';return;}
  host.innerHTML=`<header class="character-story-head"><div><p class="eyebrow">STORY LIFE</p><h3>${safe(character.name)} beyond the model sheet</h3><p>Define what shaped them, what they hide, and how the story changes them.</p></div><span>${profile?`Arc v${profile.version}`:'Not started'}</span></header><div class="character-story-grid"><label class="wide">History<textarea id="character-history" rows="3" placeholder="Where did they come from, and what kind of life shaped them?">${value('history')}</textarea></label><label>Formative event<textarea id="character-formative-event" rows="2" placeholder="The event they still organize their life around.">${value('formative_event')}</textarea></label><label>Secret<textarea id="character-secret" rows="2" placeholder="What must not be discovered?">${value('secret')}</textarea></label><label>Deep fear<textarea id="character-fear" rows="2" placeholder="The emotional consequence they avoid.">${value('fear')}</textarea></label><label>Misbelief<textarea id="character-misbelief" rows="2" placeholder="The false belief driving their choices.">${value('misbelief')}</textarea></label><label class="wide">Personal stakes<textarea id="character-stakes" rows="2" placeholder="What do they lose if they fail or refuse to change?">${value('stakes')}</textarea></label></div><section class="character-arc"><header><span>EMOTIONAL ARC</span><small>Beginning &rarr; turning point &rarr; ending</small></header><div><label>At the beginning<textarea id="character-arc-start" rows="2">${value('arc_start')}</textarea></label><label>What breaks open<textarea id="character-arc-turn" rows="2">${value('arc_turn')}</textarea></label><label>Who they become<textarea id="character-arc-end" rows="2">${value('arc_end')}</textarea></label></div></section><button id="save-character-story" class="primary" type="button">Save story profile</button><section class="relationship-builder"><header><div><p class="eyebrow">RELATIONSHIPS</p><h3>Character connections</h3></div><small>${relationships.length} connection${relationships.length===1?'':'s'}</small></header>${others.length?`<div class="relationship-form"><label>Character<select id="relationship-target">${others.map(item=>`<option value="${item.id}">${safe(item.name)}</option>`).join('')}</select></label><label>Relationship<select id="relationship-type"><option>ally</option><option>family</option><option>mentor</option><option>rival</option><option>romantic tension</option><option>uneasy alliance</option><option>antagonist</option></select></label><label>What others see<input id="relationship-public" placeholder="Professional distance"></label><label>Private truth<input id="relationship-private" placeholder="They trust each other more than they admit"></label><label class="wide">Source of tension<input id="relationship-tension" placeholder="What keeps the relationship dramatically active?"></label><label class="wide">Relationship arc<input id="relationship-arc" placeholder="How does this connection change across the story?"></label><button id="save-relationship" type="button">Save connection</button></div>`:'<div class="character-story-empty">Add another character before defining relationships.</div>'}<div id="relationship-list" class="relationship-list">${relationships.length?relationships.map(item=>`<article><div><b>${safe(item.target_name)}</b><small>${safe(item.relationship_type)}</small><p>${safe(item.tension||item.private_truth||'Connection ready to deepen.')}</p></div><button type="button" data-delete-relationship="${item.id}" aria-label="Remove relationship with ${safe(item.target_name)}">Remove</button></article>`).join(''):'<div class="character-story-empty">No relationships defined yet.</div>'}</div></section><div id="character-story-status"></div>`;
  document.querySelector('#save-character-story').onclick=()=>saveCharacterStoryProfile(projectId);const saveRelationship=document.querySelector('#save-relationship');if(saveRelationship)saveRelationship.onclick=()=>saveCharacterRelationship(projectId);document.querySelectorAll('[data-delete-relationship]').forEach(button=>button.onclick=async()=>{await api(`/api/character-relationships/${button.dataset.deleteRelationship}`,{method:'DELETE'});await loadCharacterStory(projectId,activeCharacterId);});
}

async function saveCharacterStoryProfile(projectId) {
  const fields=['history','formative-event','secret','fear','misbelief','arc-start','arc-turn','arc-end','stakes'],payload={};fields.forEach(field=>payload[field.replaceAll('-','_')]=document.querySelector(`#character-${field}`).value);const button=document.querySelector('#save-character-story');button.disabled=true;button.textContent='Saving...';try{await api(`/api/characters/${activeCharacterId}/story-profile`,{method:'PUT',body:JSON.stringify(payload)});await loadCharacterStory(projectId,activeCharacterId);}finally{button.disabled=false;button.textContent='Save story profile';}
}

async function saveCharacterRelationship(projectId) {
  const payload={target_character_id:Number(document.querySelector('#relationship-target').value),relationship_type:document.querySelector('#relationship-type').value,public_dynamic:document.querySelector('#relationship-public').value,private_truth:document.querySelector('#relationship-private').value,tension:document.querySelector('#relationship-tension').value,arc:document.querySelector('#relationship-arc').value};await api(`/api/characters/${activeCharacterId}/relationships`,{method:'PUT',body:JSON.stringify(payload)});await loadCharacterStory(projectId,activeCharacterId);
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
  if(job.watermarked)document.querySelector('#segmented-export-result .segment-export header')?.insertAdjacentHTML('afterend',`<div class="job-error">Trial export · limited to ${job.max_duration_seconds||60} seconds · Kizuna watermark included</div>`);
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
async function uploadCueAudio(event) { const file=event.target.files[0];if(!file||!activeAudioCueId)return; const csrf=(document.cookie.match(/(?:^|; )kizuna_csrf=([^;]+)/)||[])[1]||'';const response=await fetch(`/api/audio-cues/${activeAudioCueId}/upload?filename=${encodeURIComponent(file.name)}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream','X-Kizuna-CSRF':decodeURIComponent(csrf)},body:file}); if(!response.ok)throw new Error(await response.text()); const cue=await response.json(); await refreshAudioAndSelect(cue.id); }
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

let integrationSettings=null,aiRoutingSettings=null,computeSettings=null,storageSettings=null,professionalProfile=null,teamSettings=null,accountBilling=null,settingsView='compute';

async function openAccountCenter(){
  openWorkspace(accountDialog);const host=document.querySelector('#account-center');host.innerHTML='<div class="settings-loading">Loading account...</div>';try{accountBilling=await api('/api/account/billing');renderAccountCenter();}catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

function renderAccountCenter(){
  const host=document.querySelector('#account-center'),account=accountBilling.account,subscription=accountBilling.subscription,trialEnd=account.trial_ends_at?new Date(account.trial_ends_at).toLocaleDateString():null,periodEnd=subscription?.current_period_end?new Date(subscription.current_period_end).toLocaleDateString():null;
  const plan=subscription&&['active','trialing'].includes(subscription.status)?'Creator subscription':account.account_tier==='trial'?'7-day trial':account.role==='admin'?'Studio administrator':account.account_tier.replaceAll('_',' ');
  const action=accountBilling.portal_ready?'<button id="manage-subscription" class="primary" type="button">Manage subscription</button>':accountBilling.checkout_ready?'<button id="start-subscription" class="primary" type="button">Choose Creator plan</button>':'<button type="button" disabled>Subscriptions are not configured yet</button>';
  host.innerHTML=`<section class="account-overview"><header><div><p class="eyebrow">CURRENT ACCESS</p><h3>${safe(plan)}</h3><p>${safe(account.email)}</p></div><span class="account-status ${safe(subscription?.status||account.account_tier)}">${safe(subscription?.status||account.account_tier)}</span></header><div class="account-facts"><span><b>${account.email_verified?'Verified':'Verification needed'}</b>Email</span><span><b>${trialEnd||periodEnd||'Ongoing'}</b>${subscription?'Current period':'Trial ends'}</span><span><b>${account.trial_watermarked?'Yes':'No'}</b>Trial watermark</span><span><b>${account.trial_export_seconds?account.trial_export_seconds+' seconds':'Plan allowance'}</b>Export limit</span></div><div class="account-actions">${action}<small>Checkout, invoices, payment methods, and cancellation are handled by Stripe. Kizuna changes access only after a signed billing event.</small></div></section><section class="account-events"><header><div><p class="eyebrow">BILLING ACTIVITY</p><h3>Recent account events</h3></div></header>${accountBilling.events.length?accountBilling.events.map(event=>`<article><b>${safe(event.event_type.replaceAll('_',' '))}</b><span>${new Date(event.created_at).toLocaleString()}</span></article>`).join(''):'<div class="compute-empty">No billing activity yet.</div>'}</section>`;
  host.querySelector('#start-subscription')?.addEventListener('click',()=>openBillingSession('/api/account/billing/checkout'));host.querySelector('#manage-subscription')?.addEventListener('click',()=>openBillingSession('/api/account/billing/portal'));
}

async function openBillingSession(path){const button=document.querySelector('#account-center .account-actions button');button.disabled=true;button.textContent='Opening secure billing...';try{const session=await api(path,{method:'POST'});location.assign(session.url);}catch(error){button.disabled=false;button.textContent=error.message;}}

async function openSettings() {
  openWorkspace(settingsDialog);
  const host=document.querySelector('#integration-settings');host.innerHTML='<div class="settings-loading">Loading studio connections...</div>';
  try{[integrationSettings,aiRoutingSettings,computeSettings,storageSettings,professionalProfile,teamSettings]=await Promise.all([api('/api/settings/integrations'),api('/api/settings/ai-routing'),api('/api/settings/compute'),api('/api/settings/storage'),api('/api/settings/creator-profile'),api('/api/settings/team')]);renderIntegrationSettings();}catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

function integrationModeLabel(mode) {
  return {api:'Connect by API',handoff:'File handoff',disabled:'Not in use'}[mode]||mode;
}

function renderIntegrationSettings() {
  const host=document.querySelector('#integration-settings'),active=integrationSettings.integrations.filter(item=>item.configured).length,groups=Object.entries(integrationSettings.categories);
  host.innerHTML=`${renderComputeControl()}<header class="integration-summary"><div><b>${active} connected</b><span>${integrationSettings.integrations.length} available engines and tools</span></div><details class="custom-integration"><summary>Add a custom connection</summary><form id="custom-integration-form"><div class="integration-fields"><label>Name<input name="display_name" required placeholder="Studio inference server"></label><label>Type<select name="category"><option value="ai">AI engine</option><option value="generation">Generation tool</option><option value="creative">Creative application</option><option value="compliance">Compliance scanner</option></select></label><label>Connection<select name="mode"><option value="api">Connect by API</option><option value="handoff">File handoff</option></select></label><label>Endpoint<input name="endpoint" placeholder="http://render-box:8000/v1"></label><label>Default model<input name="model" placeholder="Optional model name"></label><label>Secret environment variable<input name="secret_env_var" placeholder="KIZUNA_STUDIO_AI_KEY"></label><label class="wide">Capabilities<input name="capabilities" placeholder="text, trademark, visual, audio"></label></div><button class="primary" type="submit">Add connection</button></form></details></header>${renderAIRouting()}${groups.map(([category,label])=>{const items=integrationSettings.integrations.filter(item=>item.category===category);return`<section class="integration-group"><header><div><p class="eyebrow">${safe(label)}</p><h3>${category==='ai'?'Connect the minds available to your studio':category==='generation'?'Connect the render engines':category==='compliance'?'Connect originality and rights scanners':'Keep working in familiar apps'}</h3></div><span>${items.filter(item=>item.configured).length}/${items.length} connected</span></header><div class="integration-grid">${items.map(renderIntegrationCard).join('')}</div></section>`;}).join('')}`;
  organizeSettingsViews(host);wireComputeControl();host.querySelectorAll('[data-ai-route]').forEach(select=>select.onchange=()=>saveAIRoute(select.dataset.aiRoute));host.querySelectorAll('[data-route-model]').forEach(input=>input.onchange=()=>saveAIRoute(input.dataset.routeModel));host.querySelectorAll('[data-integration-form]').forEach(form=>form.onsubmit=event=>saveIntegration(event,form.dataset.integrationForm));host.querySelectorAll('[data-delete-integration]').forEach(button=>button.onclick=()=>deleteIntegration(button.dataset.deleteIntegration));document.querySelector('#custom-integration-form').onsubmit=addCustomIntegration;
}

function renderProfessionalProfile(){
  if(!professionalProfile)return'';const profile=professionalProfile.profile,claims=professionalProfile.claims,status=profile?.verification_status||'unsubmitted';
  const claimCards=claims.map(claim=>`<article><header><div><b>${safe(claim.title)}</b><span>${safe(claim.work_type)}${claim.release_year?` · ${claim.release_year}`:''}</span></div><em class="verification-badge ${safe(claim.verification_status)}">${safe(claim.verification_status)}</em></header><p>${safe(claim.credited_role)} · ${safe(claim.authorization_scope)}</p><small>${claim.external_ids.length?`Identifiers: ${claim.external_ids.map(safe).join(', ')}`:'No external identifier'} · ${claim.evidence_refs.length} evidence reference${claim.evidence_refs.length===1?'':'s'}</small>${claim.review_notes?`<div class="verification-note">${safe(claim.review_notes)}</div>`:''}</article>`).join('')||'<div class="compute-empty">No professional work claims submitted yet.</div>';
  return `<section class="professional-profile"><div class="original-work-charter"><p class="eyebrow">KIZUNA CREATOR CHARTER</p><h3>Original stories, broader access</h3><p>${safe(professionalProfile.policy.statement)}</p><b>Verification proves identity or authorization for specific work. It never creates a general compliance exemption.</b></div><header><div><p class="eyebrow">PROFESSIONAL IDENTITY</p><h3>Verify your creative history</h3><p>Directors, artists, writers, studios, estates, and authorized representatives can document who they are and the prior work they are permitted to reuse.</p></div><span class="verification-badge ${safe(status)}">${safe(status)}</span></header><form id="professional-profile-form"><label>Public or professional name<input name="display_name" required minlength="2" value="${safe(profile?.display_name||'')}"></label><label>Legal name or organization<input name="legal_name" required minlength="2" value="${safe(profile?.legal_name||'')}"></label><label>Identity type<select name="identity_type"><option value="individual" ${profile?.identity_type==='individual'?'selected':''}>Individual professional</option><option value="studio" ${profile?.identity_type==='studio'?'selected':''}>Studio or company</option><option value="estate" ${profile?.identity_type==='estate'?'selected':''}>Estate or rights holder</option><option value="authorized_representative" ${profile?.identity_type==='authorized_representative'?'selected':''}>Authorized representative</option></select></label><label>Professional role<input name="professional_role" required minlength="2" value="${safe(profile?.professional_role||'')}" placeholder="Director, writer, artist, studio"></label><label>Official website<input name="website" type="url" value="${safe(profile?.website||'')}"></label><label>Identity evidence<input name="verification_evidence" required value="${safe(profile?.verification_evidence?.join(', ')||'')}" placeholder="Guild profile, official site, company record, secure document reference"></label><label class="wide">Professional biography<textarea name="biography" rows="3">${safe(profile?.biography||'')}</textarea></label><button class="primary" type="submit">${profile?'Resubmit for verification':'Submit for verification'}</button></form>${profile?.review_notes?`<div class="verification-note"><b>Reviewer note</b>${safe(profile.review_notes)}</div>`:''}<small class="verification-disclosure">${professionalProfile.verification_review_configured?'Verification is independently reviewed. Editing a verified profile returns it and its work claims to pending.':'Local verification review is not configured yet. Submissions will remain pending until a reviewer service is connected.'}</small><section class="work-claims"><header><div><h3>Verified work claims</h3><p>Add only work you own, created, or are contractually authorized to represent.</p></div><span>${claims.filter(item=>item.verification_status==='verified').length}/${claims.length} verified</span></header><div class="work-claim-list">${claimCards}</div>${profile?`<details><summary>Submit a work claim</summary><form id="professional-work-form"><label>Work title<input name="title" required></label><label>Type<select name="work_type"><option value="film">Film</option><option value="series">Series</option><option value="episode">Episode</option><option value="character">Character</option><option value="story">Story</option><option value="artwork">Artwork</option><option value="music">Music</option><option value="voice">Voice</option><option value="other">Other</option></select></label><label>Your credited role<input name="credited_role" required minlength="2"></label><label>Release year<input name="release_year" type="number" min="1800" max="2200"></label><label>External identifiers<input name="external_ids" placeholder="Registry ID, catalog ID, canonical provider ID"></label><label>Evidence references<input name="evidence_refs" required placeholder="Official credits, contract, registration, secure document reference"></label><label class="wide">Authorization scope<textarea name="authorization_scope" required minlength="10" rows="3" placeholder="What you own or are authorized to reuse, and any limits"></textarea></label><button type="submit">Submit work claim</button></form></details>`:'<small>Submit your identity profile before adding work claims.</small>'}</section></section>`;
}

function organizeSettingsViewsLegacy(host){
  host.insertAdjacentHTML('afterbegin',renderStorageSettings()+renderProfessionalProfile());const compute=document.createElement('div'),storage=document.createElement('div'),connections=document.createElement('div'),profile=document.createElement('div'),tabs=document.createElement('nav');compute.className=storage.className=connections.className=profile.className='settings-pane';compute.dataset.settingsPane='compute';storage.dataset.settingsPane='storage';connections.dataset.settingsPane='connections';profile.dataset.settingsPane='profile';tabs.className='settings-tabs';tabs.innerHTML='<button type="button" data-settings-view="compute">Computers & costs</button><button type="button" data-settings-view="storage">Storage & backups</button><button type="button" data-settings-view="connections">AI & connected tools</button><button type="button" data-settings-view="profile">Creator profile & rights</button>';
  [...host.children].forEach(child=>(child.matches('.compute-control,.spend-monitor')?compute:child.matches('.storage-settings')?storage:child.matches('.professional-profile')?profile:connections).appendChild(child));host.replaceChildren(tabs,compute,storage,connections,profile);const panes={compute,storage,connections,profile},show=view=>{settingsView=view;Object.entries(panes).forEach(([key,pane])=>pane.hidden=view!==key);tabs.querySelectorAll('button').forEach(button=>button.classList.toggle('active',button.dataset.settingsView===view));};tabs.querySelectorAll('button').forEach(button=>button.onclick=()=>show(button.dataset.settingsView));host.querySelector('#test-s3-storage')?.addEventListener('click',testS3Storage);host.querySelector('#professional-profile-form')?.addEventListener('submit',saveProfessionalProfile);host.querySelector('#professional-work-form')?.addEventListener('submit',saveProfessionalWorkClaim);show(settingsView);
}

function renderTeamSettings(){
  if(!teamSettings)return'';const roles={owner:'Owner',editor:'Editor',viewer:'Viewer'};
  const projects=teamSettings.projects.map(project=>{const members=teamSettings.memberships.filter(item=>item.project_id===project.id),memberIds=new Set(members.map(item=>item.user_id)),available=teamSettings.users.filter(user=>user.active&&!memberIds.has(user.id));return`<article class="team-project"><header><div><b>${safe(project.title)}</b><span>You are ${safe(roles[project.my_role]||project.my_role)}</span></div><em>${members.length} member${members.length===1?'':'s'}</em></header><div class="team-member-list">${members.map(member=>`<div><span><b>${safe(member.display_name)}</b><small>${safe(member.email)}</small></span><select data-team-member-role="${member.user_id}" data-team-project="${project.id}" ${project.my_role!=='owner'?'disabled':''}><option value="owner" ${member.role==='owner'?'selected':''}>Owner</option><option value="editor" ${member.role==='editor'?'selected':''}>Editor</option><option value="viewer" ${member.role==='viewer'?'selected':''}>Viewer</option><option value="remove">Remove access</option></select></div>`).join('')}</div>${project.my_role==='owner'&&available.length?`<form class="team-add-existing" data-team-add="${project.id}"><select name="user_id">${available.map(user=>`<option value="${user.id}">${safe(user.display_name)} · ${safe(user.email)}</option>`).join('')}</select><select name="role"><option value="editor">Editor</option><option value="viewer">Viewer</option><option value="owner">Owner</option></select><button type="submit">Add existing account</button></form>`:''}</article>`;}).join('');
  const pending=teamSettings.invitations.map(invite=>`<article><span><b>${safe(invite.display_name||invite.email)}</b><small>${safe(invite.email)} · ${invite.project_access.map(item=>`${safe(item.project_title)} (${safe(item.role)})`).join(', ')}</small></span><button type="button" data-revoke-invite="${invite.id}">Revoke</button></article>`).join('')||'<div class="compute-empty">No pending invitations.</div>';
  const owned=teamSettings.projects.filter(project=>project.my_role==='owner');
  return `<section class="team-settings"><header><div><p class="eyebrow">STUDIO TEAM</p><h3>Invite people into specific productions</h3><p>Owners can direct access. Editors can create and revise. Viewers can review but cannot change production data.</p></div><span>${teamSettings.users.length} account${teamSettings.users.length===1?'':'s'}</span></header><div class="team-project-grid">${projects}</div><div class="team-invite-grid"><form id="team-invite-form"><h3>Invite a collaborator</h3><label>Name<input name="display_name" placeholder="Optional display name"></label><label>Email<input name="email" type="email" required></label><fieldset><legend>Production access</legend>${owned.map(project=>`<div><label><input type="checkbox" name="project_id" value="${project.id}"> ${safe(project.title)}</label><select data-invite-role="${project.id}"><option value="editor">Editor</option><option value="viewer">Viewer</option><option value="owner">Owner</option></select></div>`).join('')||'<small>You need Owner access to invite collaborators.</small>'}</fieldset><button class="primary" type="submit" ${owned.length?'':'disabled'}>Create invitation</button><div id="team-invite-result"></div></form><section><h3>Pending invitations</h3><div class="pending-invites">${pending}</div></section></div></section>`;
}

function organizeSettingsViews(host){
  host.insertAdjacentHTML('afterbegin',renderTeamSettings()+renderStorageSettings()+renderProfessionalProfile());const compute=document.createElement('div'),team=document.createElement('div'),storage=document.createElement('div'),connections=document.createElement('div'),profile=document.createElement('div'),tabs=document.createElement('nav');compute.className=team.className=storage.className=connections.className=profile.className='settings-pane';compute.dataset.settingsPane='compute';team.dataset.settingsPane='team';storage.dataset.settingsPane='storage';connections.dataset.settingsPane='connections';profile.dataset.settingsPane='profile';tabs.className='settings-tabs';tabs.innerHTML='<button type="button" data-settings-view="compute">Computers & costs</button><button type="button" data-settings-view="team">Team & access</button><button type="button" data-settings-view="storage">Storage & backups</button><button type="button" data-settings-view="connections">AI & connected tools</button><button type="button" data-settings-view="profile">Creator profile & rights</button>';
  [...host.children].forEach(child=>(child.matches('.compute-control,.spend-monitor')?compute:child.matches('.team-settings')?team:child.matches('.storage-settings')?storage:child.matches('.professional-profile')?profile:connections).appendChild(child));host.replaceChildren(tabs,compute,team,storage,connections,profile);const panes={compute,team,storage,connections,profile},show=view=>{settingsView=view;Object.entries(panes).forEach(([key,pane])=>pane.hidden=view!==key);tabs.querySelectorAll('button').forEach(button=>button.classList.toggle('active',button.dataset.settingsView===view));};tabs.querySelectorAll('button').forEach(button=>button.onclick=()=>show(button.dataset.settingsView));host.querySelector('#test-s3-storage')?.addEventListener('click',testS3Storage);host.querySelector('#professional-profile-form')?.addEventListener('submit',saveProfessionalProfile);host.querySelector('#professional-work-form')?.addEventListener('submit',saveProfessionalWorkClaim);wireTeamSettings();show(settingsView);
}

function wireTeamSettings(){document.querySelector('#team-invite-form')?.addEventListener('submit',createTeamInvitation);document.querySelectorAll('[data-team-member-role]').forEach(select=>select.onchange=()=>changeTeamMembership(Number(select.dataset.teamProject),Number(select.dataset.teamMemberRole),select.value));document.querySelectorAll('[data-team-add]').forEach(form=>form.onsubmit=event=>addExistingTeamMember(event,Number(form.dataset.teamAdd)));document.querySelectorAll('[data-revoke-invite]').forEach(button=>button.onclick=()=>revokeTeamInvitation(Number(button.dataset.revokeInvite)));}
async function refreshTeamSettings(){teamSettings=await api('/api/settings/team');renderIntegrationSettings();settingsView='team';}
async function createTeamInvitation(event){event.preventDefault();const form=event.currentTarget,project_access=[...form.querySelectorAll('[name="project_id"]:checked')].map(input=>({project_id:Number(input.value),role:form.querySelector(`[data-invite-role="${input.value}"]`).value})),result=form.querySelector('#team-invite-result');if(!project_access.length){result.textContent='Choose at least one production.';return;}const invite=await api('/api/settings/team/invitations',{method:'POST',body:JSON.stringify({email:form.elements.email.value,display_name:form.elements.display_name.value,project_access})});result.innerHTML=`<label>Copy this invitation now<input readonly value="${safe(invite.acceptance_url)}"></label><button type="button" id="copy-team-invite">Copy invitation link</button>`;document.querySelector('#copy-team-invite').onclick=()=>navigator.clipboard.writeText(invite.acceptance_url);teamSettings=await api('/api/settings/team');renderPendingInvites();}
function renderPendingInvites(){const host=document.querySelector('.pending-invites');if(!host)return;host.innerHTML=teamSettings.invitations.map(invite=>`<article><span><b>${safe(invite.display_name||invite.email)}</b><small>${safe(invite.email)} · ${invite.project_access.map(item=>`${safe(item.project_title)} (${safe(item.role)})`).join(', ')}</small></span><button type="button" data-revoke-invite="${invite.id}">Revoke</button></article>`).join('')||'<div class="compute-empty">No pending invitations.</div>';host.querySelectorAll('[data-revoke-invite]').forEach(button=>button.onclick=()=>revokeTeamInvitation(Number(button.dataset.revokeInvite)));}
async function changeTeamMembership(projectId,userId,role){await api(`/api/settings/team/projects/${projectId}/members/${userId}`,{method:'PUT',body:JSON.stringify({role})});await refreshTeamSettings();}
async function addExistingTeamMember(event,projectId){event.preventDefault();await api(`/api/settings/team/projects/${projectId}/members/${Number(event.currentTarget.elements.user_id.value)}`,{method:'PUT',body:JSON.stringify({role:event.currentTarget.elements.role.value})});await refreshTeamSettings();}
async function revokeTeamInvitation(invitationId){await api(`/api/settings/team/invitations/${invitationId}`,{method:'DELETE'});await refreshTeamSettings();}

async function saveProfessionalProfile(event){event.preventDefault();const form=event.currentTarget,button=form.querySelector('button');button.disabled=true;button.textContent='Submitting...';try{professionalProfile=await api('/api/settings/creator-profile',{method:'PUT',body:JSON.stringify({display_name:form.elements.display_name.value,legal_name:form.elements.legal_name.value,identity_type:form.elements.identity_type.value,professional_role:form.elements.professional_role.value,website:form.elements.website.value,biography:form.elements.biography.value,verification_evidence:form.elements.verification_evidence.value.split(',').map(item=>item.trim()).filter(Boolean)})});renderIntegrationSettings();}catch(error){button.disabled=false;button.textContent=error.message;}}
async function saveProfessionalWorkClaim(event){event.preventDefault();const form=event.currentTarget,button=form.querySelector('button');button.disabled=true;button.textContent='Submitting...';try{professionalProfile=await api('/api/settings/creator-profile/work-claims',{method:'POST',body:JSON.stringify({title:form.elements.title.value,work_type:form.elements.work_type.value,credited_role:form.elements.credited_role.value,release_year:form.elements.release_year.value?Number(form.elements.release_year.value):null,external_ids:form.elements.external_ids.value.split(',').map(item=>item.trim()).filter(Boolean),evidence_refs:form.elements.evidence_refs.value.split(',').map(item=>item.trim()).filter(Boolean),authorization_scope:form.elements.authorization_scope.value})});renderIntegrationSettings();}catch(error){button.disabled=false;button.textContent=error.message;}}

function renderStorageSettings(){if(!storageSettings)return'';const s3=storageSettings.s3;return`<section class="storage-settings"><header><div><p class="eyebrow">PRODUCTION VAULT</p><h3>Keep productions recoverable</h3><p>Local storage is ready automatically. Add any S3-compatible service for an independent off-server copy.</p></div><span class="${s3.ready?'ready':''}">${s3.ready?'Off-server ready':'Local only'}</span></header><div class="storage-provider-grid"><article class="ready"><b>This Kizuna server</b><span>${safe(storageSettings.local.directory)}</span><p>Fast local backups stored with this deployment.</p></article><article class="${s3.ready?'ready':''}"><b>S3-compatible vault</b><span>${s3.ready?safe(s3.bucket):'Setup needed'}</span><p>${s3.ready?`${safe(s3.endpoint||'AWS S3')} · ${safe(s3.region||'automatic region')}`:'Works with AWS S3, Cloudflare R2, MinIO, Backblaze, and compatible providers.'}</p></article></div><details class="storage-setup" ${s3.ready?'':'open'}><summary>${s3.ready?'View server setup':'Connect off-server storage'}</summary><p>Add these environment variables to Kizuna in Coolify or your server. Credential values are never returned to the browser.</p><code>KIZUNA_S3_BUCKET<br>KIZUNA_S3_ENDPOINT_URL<br>KIZUNA_S3_REGION<br>KIZUNA_S3_PREFIX<br>AWS_ACCESS_KEY_ID<br>AWS_SECRET_ACCESS_KEY<br>AWS_SESSION_TOKEN (optional)</code>${s3.ready?'<button type="button" id="test-s3-storage">Test connection</button>':''}<div id="storage-test-result"></div></details></section>`;}

async function testS3Storage(event){const result=document.querySelector('#storage-test-result');event.currentTarget.disabled=true;result.textContent='Testing the off-server vault...';try{const response=await api('/api/settings/storage/s3/test',{method:'POST'});result.textContent=response.message;}catch(error){result.textContent=error.message;}finally{event.currentTarget.disabled=false;}}

function renderComputeControl(){
  if(!computeSettings)return'';const usage=computeSettings.usage,budget=usage.budget,nodeOptions=`<option value="">Any enrolled computer</option>${computeSettings.nodes.map(node=>`<option value="${safe(node.node_key)}">${safe(node.name)}</option>`).join('')}`;
  const dayNames=['M','T','W','T','F','S','S'],taskNames={master_segment:'Video rendering',character_reference:'Character images',media_replication:'Media storage'};
  const nodeCards=computeSettings.nodes.length?computeSettings.nodes.map(node=>{const hive=node.hive,metrics=hive.metrics||{},ready=node.status==='online'&&hive.accepting_work;return`<article class="compute-node ${ready?'ready':''}"><header><div><b>${safe(node.name)}</b><small>${safe(node.os_name)} · ${safe(node.architecture)}</small></div><span class="${ready?'online':safe(node.status)}">${safe(node.status==='offline'?'offline':hive.reason)}</span></header><div class="node-specs"><span>${node.logical_cores} threads</span><span>${node.ram_gb} GB RAM</span><span>${node.gpu.length?safe(node.gpu.map(gpu=>gpu.name).join(', ')):'CPU only'}</span><span>${hive.active_jobs}/${hive.max_concurrency} slots</span></div><div class="node-meter-row"><span>CPU <b>${Math.round(metrics.cpu_percent||0)}%</b></span><span>GPU <b>${Math.round(metrics.gpu_percent||0)}%</b></span><span>RAM <b>${Number(metrics.memory_used_gb||0).toFixed(1)} GB</b></span></div><div class="node-quick-actions"><button type="button" data-node-pause="${safe(node.node_key)}">${hive.paused?'Resume':'Pause'}</button><button type="button" data-node-drain="${safe(node.node_key)}" class="${hive.drain?'active':''}">${hive.drain?'Draining':'Finish jobs, then stop'}</button></div><details class="node-control"><summary>Usage limits & schedule</summary><form data-node-control="${safe(node.node_key)}"><div class="node-control-grid"><label>Parallel jobs<input name="max_concurrency" type="number" min="1" max="32" value="${hive.max_concurrency}"></label><label>CPU ceiling<input name="cpu_limit_percent" type="number" min="10" max="100" value="${hive.cpu_limit_percent}"></label><label>GPU ceiling<input name="gpu_limit_percent" type="number" min="10" max="100" value="${hive.gpu_limit_percent}"></label><label>RAM ceiling (GB)<input name="memory_limit_gb" type="number" min="0" step=".5" value="${hive.memory_limit_gb}"></label><label>Start hour<input name="start_hour" type="number" min="0" max="23" value="${hive.start_hour}"></label><label>Stop hour<input name="end_hour" type="number" min="1" max="24" value="${hive.end_hour}"></label><label>Priority<input name="priority" type="number" min="1" max="100" value="${hive.priority}"></label></div><fieldset><legend>Available days</legend><div class="day-pills">${dayNames.map((day,index)=>`<label><input name="available_days" type="checkbox" value="${index}" ${hive.available_days.includes(index)?'checked':''}><span>${day}</span></label>`).join('')}</div></fieldset><fieldset><legend>Jobs this computer may run</legend><div class="task-checks">${Object.entries(taskNames).map(([task,label])=>`<label><input name="allowed_tasks" type="checkbox" value="${task}" ${hive.allowed_tasks.includes(task)?'checked':''}> ${safe(label)}</label>`).join('')}</div></fieldset><button class="primary" type="submit">Save computer</button></form></details><details><summary>Detected creative tools · ${node.software.length}</summary><div class="software-list">${node.software.map(name=>`<span>${safe(name)}</span>`).join('')||'<span>None shared</span>'}</div></details></article>`;}).join(''):'<div class="compute-empty"><b>No local computers connected yet.</b><span>Cloud-only production still works. Add a computer when you want private AI, local previews, or rendering.</span></div>';
  const workloads=computeSettings.workloads.map(item=>`<article class="workload-policy"><div><b>${safe(item.label)}</b><small>${safe(item.description)}</small></div><label>Run<select data-workload-placement="${safe(item.task)}"><option value="auto" ${item.placement==='auto'?'selected':''}>Let Kizuna decide</option><option value="local" ${item.placement==='local'?'selected':''}>On my computer</option><option value="cloud" ${item.placement==='cloud'?'selected':''}>In the cloud</option></select></label><label>Preferred computer<select data-workload-node="${safe(item.task)}">${nodeOptions.replace(`value="${safe(item.node_key)}"`,`value="${safe(item.node_key)}" selected`)}</select></label><label>Cloud connection<input data-workload-cloud="${safe(item.task)}" value="${safe(item.cloud_provider)}" placeholder="Use routed provider"></label></article>`).join('');
  const modelRows=usage.by_model.length?usage.by_model.map(row=>`<tr><td>${safe(row.provider_key)}</td><td>${safe(row.model)}</td><td>${row.requests}</td><td>${(row.input_tokens+row.output_tokens).toLocaleString()}</td><td>${row.pricing_known?`$${row.estimated_cost.toFixed(4)}`:'Rate needed'}</td></tr>`).join(''):'<tr><td colspan="5">No routed AI usage recorded this month.</td></tr>';
  const hive=computeSettings.hive;return `<section class="compute-control"><header><div><p class="eyebrow">KIZUNA HIVE</p><h3>One studio across every computer</h3><p>Mix Windows, Mac, and Linux devices. Kizuna only sends new work when a computer is online, within schedule, and below its usage limits.</p></div><button id="enroll-node" class="primary" type="button">Add a computer</button></header><div class="hive-summary"><span><b>${hive.online}/${hive.devices}</b> online</span><span><b>${hive.accepting_work}</b> ready</span><span><b>${hive.active_jobs}/${hive.capacity}</b> slots used</span><span><b>${hive.queued_jobs}</b> waiting</span><span><b>${hive.platforms.length}</b> platforms</span></div><div id="node-enrollment"></div><div class="compute-layout"><section><div class="section-title"><b>Hive computers</b><span>${safe(hive.platforms.join(' · ')||'No devices')}</span></div><div class="compute-nodes">${nodeCards}</div><details class="privacy-disclosure"><summary>What the companion can see</summary><div><p><b>Shared only with approval</b>${computeSettings.privacy.sent.map(item=>`<span>✓ ${safe(item)}</span>`).join('')}</p><p><b>Never collected</b>${computeSettings.privacy.never_sent.map(item=>`<span>— ${safe(item)}</span>`).join('')}</p></div></details></section><section><div class="section-title"><b>Local or cloud</b><span>Creator controlled</span></div><div class="workload-grid">${workloads}</div></section></div></section><section class="spend-monitor"><header><div><p class="eyebrow">AI USAGE & BUDGET</p><h3>Know what every model costs</h3></div><div class="spend-total"><b>${usage.unpriced_requests?'Partial estimate':`$${usage.estimated_cost.toFixed(2)}`}</b><span>${usage.requests} request${usage.requests===1?'':'s'} · ${usage.month}</span></div></header><div class="spend-grid"><form id="spend-budget"><label>Monthly budget (USD)<input name="monthly_budget" type="number" min="0" step="1" value="${budget.monthly_budget}"></label><label>Warn me at<input name="warning_percent" type="number" min="1" max="100" value="${budget.warning_percent}"></label><label class="budget-stop"><input name="hard_stop" type="checkbox" ${budget.hard_stop?'checked':''}> Use local guidance after the limit</label><button type="submit">Save budget</button></form><div class="usage-totals"><span><b>${usage.input_tokens.toLocaleString()}</b> input tokens</span><span><b>${usage.cached_input_tokens.toLocaleString()}</b> cached</span><span><b>${usage.output_tokens.toLocaleString()}</b> output tokens</span><span><b>${usage.unpriced_requests}</b> unpriced requests</span></div></div><div class="usage-table"><table><thead><tr><th>Provider</th><th>Model</th><th>Requests</th><th>Tokens</th><th>Estimate</th></tr></thead><tbody>${modelRows}</tbody></table></div><div class="savings-list">${usage.suggestions.map(item=>`<p>${safe(item)}</p>`).join('')}</div><details class="rate-editor"><summary>Add or update a model rate</summary><form id="rate-form"><label>Provider key<input name="provider_key" required placeholder="openai"></label><label>Model<input name="model" required placeholder="Exact model ID"></label><label>Input / 1M<input name="input_per_million" type="number" min="0" step="0.0001" value="0"></label><label>Cached input / 1M<input name="cached_input_per_million" type="number" min="0" step="0.0001" value="0"></label><label>Output / 1M<input name="output_per_million" type="number" min="0" step="0.0001" value="0"></label><label>Official pricing link<input name="source_url" type="url" placeholder="https://..."></label><button class="primary" type="submit">Save verified rate</button></form></details></section>`;
}

function wireComputeControl(){
  document.querySelector('#enroll-node').onclick=createNodeEnrollment;document.querySelectorAll('[data-node-control]').forEach(form=>form.onsubmit=event=>saveNodeControl(event,form.dataset.nodeControl));document.querySelectorAll('[data-node-pause]').forEach(button=>button.onclick=()=>quickNodeControl(button.dataset.nodePause,'paused'));document.querySelectorAll('[data-node-drain]').forEach(button=>button.onclick=()=>quickNodeControl(button.dataset.nodeDrain,'drain'));document.querySelectorAll('[data-workload-placement],[data-workload-node],[data-workload-cloud]').forEach(control=>control.onchange=()=>saveWorkload(control.dataset.workloadPlacement||control.dataset.workloadNode||control.dataset.workloadCloud));document.querySelector('#spend-budget').onsubmit=saveSpendBudget;document.querySelector('#rate-form').onsubmit=saveModelRate;
}

function nodeControlPayload(node,form){const hive=node.hive;return{paused:hive.paused,drain:hive.drain,max_concurrency:Number(form?.elements.max_concurrency.value||hive.max_concurrency),cpu_limit_percent:Number(form?.elements.cpu_limit_percent.value||hive.cpu_limit_percent),gpu_limit_percent:Number(form?.elements.gpu_limit_percent.value||hive.gpu_limit_percent),memory_limit_gb:Number(form?.elements.memory_limit_gb.value||hive.memory_limit_gb),available_days:form?[...form.querySelectorAll('[name="available_days"]:checked')].map(input=>Number(input.value)):hive.available_days,start_hour:Number(form?.elements.start_hour.value??hive.start_hour),end_hour:Number(form?.elements.end_hour.value??hive.end_hour),priority:Number(form?.elements.priority.value||hive.priority),allowed_tasks:form?[...form.querySelectorAll('[name="allowed_tasks"]:checked')].map(input=>input.value):hive.allowed_tasks};}
async function saveNodeControl(event,nodeKey){event.preventDefault();const node=computeSettings.nodes.find(item=>item.node_key===nodeKey);await api(`/api/settings/compute/nodes/${encodeURIComponent(nodeKey)}/control`,{method:'PUT',body:JSON.stringify(nodeControlPayload(node,event.currentTarget))});await refreshComputeSettings();}
async function quickNodeControl(nodeKey,field){const node=computeSettings.nodes.find(item=>item.node_key===nodeKey),payload=nodeControlPayload(node);payload[field]=!payload[field];await api(`/api/settings/compute/nodes/${encodeURIComponent(nodeKey)}/control`,{method:'PUT',body:JSON.stringify(payload)});await refreshComputeSettings();}

async function refreshComputeSettings(){computeSettings=await api('/api/settings/compute');renderIntegrationSettings();}

async function createNodeEnrollment(){
  const host=document.querySelector('#node-enrollment');host.innerHTML='<div class="settings-loading">Creating a private enrollment code...</div>';try{const setup=await api('/api/settings/compute/enrollment',{method:'POST'});host.innerHTML=`<section class="enrollment-steps"><header><div><b>Connect a computer in three steps</b><span>This code expires in 20 minutes and works once.</span></div><strong>${safe(setup.code)}</strong></header><ol><li><a class="primary" href="${safe(setup.download_url)}" download>Download Kizuna Node</a></li><li><span>Preview what will be shared</span><code>${safe(setup.commands.preview)}</code></li><li><span>Approve and connect</span><code>${safe(setup.commands.enroll)}</code></li></ol><button type="button" id="copy-enroll-command">Copy connect command</button><small>After enrollment, run <code>${safe(setup.commands.monitor)}</code> while you want this computer available.</small></section>`;document.querySelector('#copy-enroll-command').onclick=async()=>{await navigator.clipboard.writeText(setup.commands.enroll);document.querySelector('#copy-enroll-command').textContent='Copied';};}catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

async function saveWorkload(task){const placement=document.querySelector(`[data-workload-placement="${task}"]`).value,node_key=document.querySelector(`[data-workload-node="${task}"]`).value,cloud_provider=document.querySelector(`[data-workload-cloud="${task}"]`).value.trim();await api(`/api/settings/compute/workloads/${encodeURIComponent(task)}`,{method:'PUT',body:JSON.stringify({placement,node_key,cloud_provider})});await refreshComputeSettings();}

async function saveSpendBudget(event){event.preventDefault();const form=event.currentTarget;await api('/api/settings/spend',{method:'PUT',body:JSON.stringify({monthly_budget:Number(form.elements.monthly_budget.value),warning_percent:Number(form.elements.warning_percent.value),hard_stop:form.elements.hard_stop.checked})});await refreshComputeSettings();}

async function saveModelRate(event){event.preventDefault();const form=event.currentTarget;await api('/api/settings/ai-rates',{method:'POST',body:JSON.stringify({provider_key:form.elements.provider_key.value.trim(),model:form.elements.model.value.trim(),input_per_million:Number(form.elements.input_per_million.value),cached_input_per_million:Number(form.elements.cached_input_per_million.value),output_per_million:Number(form.elements.output_per_million.value),currency:'USD',source_url:form.elements.source_url.value.trim()})});await refreshComputeSettings();}

function renderAIRouting(){
  if(!aiRoutingSettings)return'';const providerOptions=route=>aiRoutingSettings.providers.map(provider=>`<option value="${safe(provider.key)}" ${route.provider_key===provider.key?'selected':''}>${safe(provider.name)}${provider.ready?'':' · setup needed'}</option>`).join('');
  return `<section class="ai-routing"><header><div><p class="eyebrow">AI ROLE ROUTING</p><h3>Choose who helps with each craft</h3><p>Keep any role private and local, or give it to a connected AI engine. The Studio Assistant is live now; department assignments are saved for the next adapter passes.</p></div><span>${aiRoutingSettings.routes.filter(route=>route.provider_key!=='local').length} customized</span></header><div class="ai-route-grid">${aiRoutingSettings.routes.map(route=>`<article class="ai-route ${route.ready?'ready':'needs-setup'}"><div><b>${safe(route.label)}</b><small>${safe(route.description)}</small></div><label>Engine<select data-ai-route="${safe(route.task)}">${providerOptions(route)}</select></label><details><summary>Model override</summary><input data-route-model="${safe(route.task)}" value="${safe(route.model_override)}" placeholder="Use connection default"></details><span>${safe(route.provider_name)} · ${safe(route.readiness_note)}</span></article>`).join('')}</div></section>`;
}

async function saveAIRoute(task){
  const select=document.querySelector(`[data-ai-route="${task}"]`),model=document.querySelector(`[data-route-model="${task}"]`),card=select.closest('.ai-route');card.classList.add('saving');
  try{await api(`/api/settings/ai-routing/${encodeURIComponent(task)}`,{method:'PUT',body:JSON.stringify({provider_key:select.value,model_override:model.value.trim()})});aiRoutingSettings=await api('/api/settings/ai-routing');renderIntegrationSettings();}catch(error){card.classList.remove('saving');card.insertAdjacentHTML('beforeend',`<div class="job-error">${safe(error.message)}</div>`);}
}

function renderIntegrationCard(item) {
  const state=item.configured?(item.mode==='handoff'?'Handoff ready':'Connected'):'Available',modes=item.modes.length?item.modes:['api','handoff','disabled'];
  return `<article class="integration-card ${item.configured?'connected':''}"><header><i>${safe(item.display_name.slice(0,2).toUpperCase())}</i><div><h4>${safe(item.display_name)}</h4><span class="integration-state">${safe(state)}</span></div></header><p>${safe(item.description||'Custom studio connection.')}</p><div class="integration-capabilities">${item.capabilities.map(capability=>`<span>${safe(capability)}</span>`).join('')}</div><details><summary>${item.configured?'Connection settings':'Set up'}</summary><form data-integration-form="${safe(item.key)}"><div class="integration-fields"><label>Use it through<select name="mode">${modes.map(mode=>`<option value="${safe(mode)}" ${item.mode===mode?'selected':''}>${safe(integrationModeLabel(mode))}</option>`).join('')}</select></label><label>Endpoint<input name="endpoint" value="${safe(item.endpoint)}" placeholder="Local or hosted API address"></label><label>Default model<input name="model" value="${safe(item.model)}" placeholder="Optional model or workflow"></label><label>Secret environment variable<input name="secret_env_var" value="${safe(item.secret_env_var)}" placeholder="No secret required"></label></div><div class="integration-secret-note">${item.secret_env_var?(item.secret_available?'Secret detected on the server.':'Add this variable to the server before using the connection.'):'No API secret is currently required.'}</div><div class="integration-actions"><button class="primary" type="submit">Save connection</button>${item.custom?`<button type="button" data-delete-integration="${safe(item.key)}">Remove</button>`:''}</div></form></details></article>`;
}

async function saveIntegration(event,key) {
  event.preventDefault();const form=event.currentTarget,item=integrationSettings.integrations.find(entry=>entry.key===key),button=form.querySelector('button[type="submit"]');button.disabled=true;button.textContent='Saving...';
  try{await api(`/api/settings/integrations/${encodeURIComponent(key)}`,{method:'PUT',body:JSON.stringify({display_name:item.display_name,category:item.category,mode:form.elements.mode.value,endpoint:form.elements.endpoint.value.trim(),model:form.elements.model.value.trim(),secret_env_var:form.elements.secret_env_var.value.trim(),configuration:item.configuration||{}})});[integrationSettings,aiRoutingSettings]=await Promise.all([api('/api/settings/integrations'),api('/api/settings/ai-routing')]);renderIntegrationSettings();}catch(error){button.disabled=false;button.textContent='Save connection';form.insertAdjacentHTML('beforeend',`<div class="job-error">${safe(error.message)}</div>`);}
}

async function addCustomIntegration(event) {
  event.preventDefault();const form=event.currentTarget,name=form.elements.display_name.value.trim(),key=`custom-${name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')}-${Date.now().toString(36)}`,capabilities=form.elements.capabilities.value.split(',').map(value=>value.trim()).filter(Boolean);
  await api(`/api/settings/integrations/${key}`,{method:'PUT',body:JSON.stringify({display_name:name,category:form.elements.category.value,mode:form.elements.mode.value,endpoint:form.elements.endpoint.value.trim(),model:form.elements.model.value.trim(),secret_env_var:form.elements.secret_env_var.value.trim(),configuration:{description:'Custom connection managed by this studio.',capabilities}})});[integrationSettings,aiRoutingSettings]=await Promise.all([api('/api/settings/integrations'),api('/api/settings/ai-routing')]);renderIntegrationSettings();
}

async function deleteIntegration(key) {
  await api(`/api/settings/integrations/${encodeURIComponent(key)}`,{method:'DELETE'});[integrationSettings,aiRoutingSettings]=await Promise.all([api('/api/settings/integrations'),api('/api/settings/ai-routing')]);renderIntegrationSettings();
}

let activeAssistantProjectId=null;

function assistantPage() {
  const openDialog=workspaceDialogs.find(dialog=>dialog.hasAttribute('open'));return workspaceKeys.get(openDialog)||'productions';
}

function assistantScreenContext() {
  const openDialog=workspaceDialogs.find(dialog=>dialog.hasAttribute('open')),root=openDialog||document.querySelector('#dashboard-home'),heading=root?.querySelector('h2,h1')?.textContent?.trim()||'Productions',selection=root?.querySelector('.active h3,.active b,.timeline-clip.active b,.cue-item.active b,.character-pill.active b')?.textContent?.trim()||heading;return{heading,selection,workspace:assistantPage()};
}

function refreshAssistantContext() {
  const host=document.querySelector('#assistant-context');if(!host)return;const context=assistantScreenContext(),project=projects.find(item=>item.id===Number(document.querySelector('#assistant-project')?.value))||currentFlowProject();host.innerHTML=`<span>${safe(context.heading)}</span><b>${safe(project?.title||'Choose a production')}</b>`;
}

async function openAssistant() {
  const panel=document.querySelector('#assistant-panel'),select=document.querySelector('#assistant-project');panel.hidden=false;document.querySelector('#assistant-launch').setAttribute('aria-expanded','true');if(!projects.length){document.querySelector('#assistant-messages').innerHTML='<div class="assistant-empty">Create a production first so I have story and workflow context to work from.</div>';select.innerHTML='';refreshAssistantContext();return;}const preferred=currentFlowProject()?.id||activeAssistantProjectId||projects[0].id;select.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(preferred));activeAssistantProjectId=Number(select.value);select.onchange=()=>{activeAssistantProjectId=Number(select.value);loadAssistantHistory();refreshAssistantContext();};refreshAssistantContext();await loadAssistantHistory();document.querySelector('#assistant-input').focus();
}

function closeAssistant() { document.querySelector('#assistant-panel').hidden=true;document.querySelector('#assistant-launch').setAttribute('aria-expanded','false'); }

async function loadAssistantHistory() {
  if(!activeAssistantProjectId)return;const host=document.querySelector('#assistant-messages');host.innerHTML='<div class="assistant-thinking">Reading the production...</div>';try{const messages=await api(`/api/projects/${activeAssistantProjectId}/assistant/messages`);host.innerHTML=messages.length?messages.map(message=>assistantMessageHtml(message)).join(''):`<div class="assistant-welcome"><b>I can see where you are and what this production has completed.</b><span>Ask me to co-write, co-direct, check continuity, explain the workflow, or identify the most useful next step.</span></div>`;host.scrollTop=host.scrollHeight;}catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

function assistantMessageHtml(message,actions=[]) {
  return `<article class="assistant-message ${safe(message.role)}"><small>${message.role==='assistant'?'Kizuna':'You'} · ${safe(message.page.replaceAll('_',' '))}</small><p>${safe(message.content).replaceAll('\n','<br>')}</p>${actions.length?`<div class="assistant-actions">${actions.map(action=>`<button type="button" data-assistant-workspace="${safe(action.workspace)}">${safe(action.label)}</button>`).join('')}</div>`:''}</article>`;
}

function assistantMessageWithEngine(message,actions=[]) {
  const engine=message.role==='assistant'&&message.context?.provider_name?` · ${safe(message.context.provider_name)}`:'';
  return `<article class="assistant-message ${safe(message.role)}"><small>${message.role==='assistant'?'Kizuna':'You'}${engine} · ${safe(message.page.replaceAll('_',' '))}</small><p>${safe(message.content).replaceAll('\n','<br>')}</p>${message.context?.fallback_reason?`<span class="assistant-fallback">Used local guidance because ${safe(message.context.fallback_reason)}</span>`:''}${actions.length?`<div class="assistant-actions">${actions.map(action=>`<button type="button" data-assistant-workspace="${safe(action.workspace)}">${safe(action.label)}</button>`).join('')}</div>`:''}</article>`;
}

assistantMessageHtml=assistantMessageWithEngine;

async function askAssistant(event) {
  event.preventDefault();const input=document.querySelector('#assistant-input'),message=input.value.trim();if(!message||!activeAssistantProjectId)return;const host=document.querySelector('#assistant-messages'),page=assistantPage();host.insertAdjacentHTML('beforeend',assistantMessageHtml({role:'user',page,content:message}));input.value='';host.insertAdjacentHTML('beforeend','<div class="assistant-thinking">Thinking with the production context...</div>');host.scrollTop=host.scrollHeight;try{const reply=await api(`/api/projects/${activeAssistantProjectId}/assistant`,{method:'POST',body:JSON.stringify({message,page,screen_context:assistantScreenContext()})});host.querySelector('.assistant-thinking:last-of-type')?.remove();host.insertAdjacentHTML('beforeend',assistantMessageHtml(reply.message,reply.actions));wireAssistantActions();host.scrollTop=host.scrollHeight;}catch(error){host.querySelector('.assistant-thinking:last-of-type')?.remove();host.insertAdjacentHTML('beforeend',`<div class="job-error">${safe(error.message)}</div>`);}
}

function wireAssistantActions() {
  document.querySelectorAll('[data-assistant-workspace]').forEach(button=>button.onclick=()=>{const key=button.dataset.assistantWorkspace,id=activeAssistantProjectId,openers={writer:openWriterRoom,crew:openCrewStudio,style:openStyleLab,characters:openCharacterStudio,worlds:openWorldStudio,assets:id=>window.openAssetLibraryReady?.(id),shots:openShotPlanner,timeline:openTimeline,audio:openAudioStudio,compositor:openCompositor,render:openRenderFarm,settings:openSettings,productions:showDashboard};openers[key]?.(id);refreshAssistantContext();});
}

function collectStory(form) {
  return {premise:form.elements.premise.value, format:form.elements.format.value, target_duration_minutes:Number(form.elements.target_duration_minutes.value), genre:form.elements.genre.value, audience:form.elements.audience.value, themes:form.elements.themes.value.split(',').map(value => value.trim()).filter(Boolean)};
}

function collectNewProduction(form) {
  const [width,height]=aspectDimensions(form.elements.aspect_ratio.value),seconds=Math.round(Number(form.elements.target_length.value)*(form.elements.target_unit.value==='minutes'?60:1));return{title:form.elements.title.value,logline:form.elements.logline.value,scope:{distribution_channel:form.elements.distribution_channel.value,release_format:form.elements.release_format.value,aspect_ratio:form.elements.aspect_ratio.value,width,height,target_duration_seconds:seconds,installment_count:Number(form.elements.installment_count.value),season_count:Number(form.elements.season_count.value),notes:form.elements.scope_notes.value}};
}

document.querySelector('#new-project').onclick = () => projectDialog.showModal();
document.querySelector('#productions-nav').onclick = showDashboard;
document.querySelector('#crew-nav').onclick = () => openCrewStudio();
document.querySelector('.brand').onclick = event => { event.preventDefault(); if(document.body.classList.contains('popout-mode'))window.close();else showDashboard(); };
document.querySelector('#style-lab-nav').onclick = () => openStyleLab();
document.querySelector('#writer-nav').onclick = () => openWriterRoom();
document.querySelector('#characters-nav').onclick = () => openCharacterStudio();
document.querySelector('#render-nav').onclick = () => openRenderFarm();
document.querySelector('#worlds-nav').onclick = () => openWorldStudio();
document.querySelector('#shots-nav').onclick = () => openShotPlanner();
document.querySelector('#timeline-nav').onclick = () => openTimeline();
document.querySelector('#audio-nav').onclick = () => openAudioStudio();
document.querySelector('#compositor-nav').onclick = () => openCompositor();
document.querySelector('#settings-nav').onclick = openSettings;
document.querySelector('#account-nav').onclick = openAccountCenter;
document.querySelector('.close').onclick = () => projectDialog.close();
document.querySelector('#style-close').onclick = closeWorkspace;
document.querySelector('#crew-close').onclick = closeWorkspace;
document.querySelector('#writer-close').onclick = closeWorkspace;
document.querySelector('#character-close').onclick = closeWorkspace;
document.querySelector('#render-close').onclick = closeWorkspace;
document.querySelector('#world-close').onclick = closeWorkspace;
document.querySelector('#shot-close').onclick = closeWorkspace;
document.querySelector('#timeline-close').onclick = closeWorkspace;
document.querySelector('#audio-close').onclick = closeWorkspace;
document.querySelector('#compositor-close').onclick = closeWorkspace;
document.querySelector('#settings-close').onclick = closeWorkspace;
document.querySelector('#account-close').onclick = closeWorkspace;
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
document.querySelector('#build-timeline').onclick = async () => { const projectId=Number(document.querySelector('#timeline-project').value); try { const scope=await api(`/api/projects/${projectId}/scope`);activeTimeline=await api(`/api/projects/${projectId}/timeline/build`,{method:'POST',body:JSON.stringify({fps:24,width:scope.width,height:scope.height})}); renderTimeline(); } catch(error) { document.querySelector('#timeline-clips').innerHTML=`<div class="job-error">${safe(error.message)}</div>`; } };
document.querySelector('#clip-form').onsubmit = async event => { event.preventDefault(); const form=event.target; activeTimeline=await api(`/api/timeline-clips/${activeClipId}`,{method:'PUT',body:JSON.stringify({duration_seconds:Number(form.elements.clip_duration.value),transition:form.elements.clip_transition.value,transition_duration:Number(form.elements.clip_transition_duration.value),audio_cue:form.elements.clip_audio_cue.value})}); renderTimeline(); };
document.querySelector('#clip-earlier').onclick = () => moveClip(-1);
document.querySelector('#clip-later').onclick = () => moveClip(1);
document.querySelector('#render-animatic').onclick = async () => { if(!activeTimeline)return; const button=document.querySelector('#render-animatic'); button.disabled=true; button.textContent='Rendering proxy…'; document.querySelector('#animatic-result').innerHTML='<div class="render-progress">Preparing frames and encoding the edit…</div>'; try { const result=await api(`/api/timelines/${activeTimeline.id}/render`,{method:'POST'}); document.querySelector('#animatic-result').innerHTML=result.status==='completed'?`<video controls src="${safe(result.uri)}"></video><p><a href="${safe(result.uri)}" download>Download proxy MP4</a></p>`:`<div class="job-error">${safe(result.error)}</div>`; await loadTimeline(activeTimeline.project_id); } catch(error) { document.querySelector('#animatic-result').innerHTML=`<div class="job-error">${safe(error.message)}</div>`; } finally { button.disabled=false; button.textContent='Render proxy animatic'; } };
document.querySelector('#render-master').onclick = async () => { if(!activeTimeline)return;const button=document.querySelector('#render-master'),profile=document.querySelector('#master-profile').value;button.disabled=true;button.textContent='Exporting master…';document.querySelector('#animatic-result').innerHTML=`<div class="render-progress">Assembling motion clips, transitions, fallback frames, and the audio mix at ${safe(profile)}…</div>`;try{const result=await api(`/api/timelines/${activeTimeline.id}/render-master`,{method:'POST',body:JSON.stringify({profile})});if(result.status==='completed'){const settings=result.render_settings;document.querySelector('#animatic-result').innerHTML=`<video controls src="${safe(result.uri)}"></video><div class="master-manifest"><b>${safe(settings.profile.toUpperCase())} MASTER</b><span>${settings.width} × ${settings.height} · ${settings.fps} fps</span><span>${settings.motion_clips} motion clip${settings.motion_clips===1?'':'s'} · ${settings.fallback_clips} fallback clip${settings.fallback_clips===1?'':'s'} · ${settings.audio_cues} audio cue${settings.audio_cues===1?'':'s'}</span><a href="${safe(result.uri)}" download>Download continuous master</a></div>`;}else document.querySelector('#animatic-result').innerHTML=`<div class="job-error">${safe(result.error)}</div>`;await loadTimeline(activeTimeline.project_id);}catch(error){document.querySelector('#animatic-result').innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}finally{button.disabled=false;button.textContent='Export continuous master';} };
document.querySelector('#plan-segmented-export').onclick = async () => { if(!activeTimeline)return;const button=document.querySelector('#plan-segmented-export');button.disabled=true;button.textContent='Starting farm…';try{renderSegmentedExport(await api(`/api/timelines/${activeTimeline.id}/master-exports/distributed`,{method:'POST',body:JSON.stringify({profile:document.querySelector('#master-profile').value,segment_size:Number(document.querySelector('#segment-size').value)})}));}catch(error){document.querySelector('#segmented-export-result').innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}finally{button.disabled=false;button.textContent='Start farm export';} };
document.querySelector('#expand-story').onclick = async () => { const projectId = Number(document.querySelector('#shot-project').value); try { await api(`/api/projects/${projectId}/expand-story`, {method:'POST',body:JSON.stringify({shots_per_beat:Number(document.querySelector('#shots-per-beat').value)})}); await loadProjects(); renderShotTree(projectId); } catch(error) { document.querySelector('#shot-tree').innerHTML = `<div class="job-error">${safe(error.message)}</div>`; } };
document.querySelector('#refresh-farm').onclick = () => refreshRenderFarm();
document.querySelector('#project-form').onsubmit = async event => { event.preventDefault();const policy=event.target.querySelector('.original-work-policy'),message=policy.querySelector('span'),original=message.textContent;message.style.color='';try{await api('/api/projects', {method:'POST', body:JSON.stringify(collectNewProduction(event.target))});event.target.reset();projectDialog.close();await loadProjects();showDashboard();}catch(error){message.textContent=error.message;message.style.color='#f1a08e';setTimeout(()=>{message.textContent=original;message.style.color='';},8000);} };
document.querySelector('#style-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#style-project').value); await api(`/api/projects/${projectId}/style`, {method:'PUT', body:JSON.stringify(collectStyle(event.target))}); styleDialog.close(); await loadProjects(); openProject(projectId); };
document.querySelector('#writer-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#writer-project').value); const brief = await api(`/api/projects/${projectId}/story`, {method:'PUT', body:JSON.stringify(collectStory(event.target))}); await loadProjects(); renderStory(brief); };
document.querySelector('#character-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#character-project').value); const character = activeCharacterId ? await api(`/api/characters/${activeCharacterId}`, {method:'PUT', body:JSON.stringify(collectCharacter(event.target))}) : await api(`/api/projects/${projectId}/characters`, {method:'POST', body:JSON.stringify(collectCharacter(event.target))}); activeCharacterId = character.id; const design = await api(`/api/characters/${character.id}/design`, {method:'PUT', body:JSON.stringify(collectCharacterDesign(event.target))}); await loadProjects(); renderCharacterRoster(projectId); renderCharacterDesign(character, design); loadCharacterStory(projectId,character.id); };
document.querySelector('#world-form').onsubmit = async event => { event.preventDefault(); const projectId = Number(document.querySelector('#world-project').value); const location = activeLocationId ? await api(`/api/locations/${activeLocationId}`, {method:'PUT', body:JSON.stringify(collectWorld(event.target))}) : await api(`/api/projects/${projectId}/locations`, {method:'POST', body:JSON.stringify(collectWorld(event.target))}); activeLocationId = location.id; const design = await api(`/api/locations/${location.id}/design`, {method:'PUT', body:JSON.stringify(collectWorldDesign(event.target))}); await loadProjects(); renderWorldRoster(projectId); renderWorldDesign(location, design); };
document.querySelector('#shot-form').onsubmit = async event => { event.preventDefault(); const project = currentShotProject(); const found = findShot(project, activeShotId); if (!found) return; const form = event.target; await api(`/api/shots/${activeShotId}`, {method:'PUT',body:JSON.stringify({title:form.elements.shot_title.value,description:form.elements.shot_description.value,position:found.shot.position,duration_seconds:Number(form.elements.shot_duration.value)})}); const plan = await api(`/api/shots/${activeShotId}/plan`, {method:'PUT',body:JSON.stringify(collectShotPlan(form))}); await loadProjects(); selectShot(project.id, activeShotId); renderShotPlan(plan); };
document.querySelector('#timeline-zoom').oninput=event=>document.querySelector('#timeline-clips').style.setProperty('--timeline-clip-width',`${event.target.value}px`);
document.querySelector('#audio-zoom').oninput=()=>{if(activeAudioStudio)renderAudioStudio(activeAudioStudio.project_id);};
document.querySelector('#audio-snap').onchange=()=>{if(activeAudioStudio)renderAudioStudio(activeAudioStudio.project_id);};
document.querySelector('#audio-playhead').onchange=()=>{if(activeAudioStudio)renderAudioStudio(activeAudioStudio.project_id);};
document.querySelector('#split-audio-region').onclick=splitSelectedAudioRegion;
document.querySelector('#duplicate-audio-region').onclick=duplicateSelectedAudioRegion;
document.querySelector('#delete-audio-region').onclick=deleteSelectedAudioRegion;
document.querySelector('#assistant-launch').onclick=openAssistant;
document.querySelector('#assistant-close').onclick=closeAssistant;
document.querySelector('#assistant-form').onsubmit=askAssistant;
document.querySelectorAll('.assistant-prompts button').forEach(button=>button.onclick=()=>{document.querySelector('#assistant-input').value=button.textContent;document.querySelector('#assistant-input').focus();});
setupCraftWorkspaces();
setupWorkspacePopouts();
loadAccountIdentity().catch(()=>{});
loadProjects().then(openRequestedWorkspace).catch(error => projectsEl.innerHTML = `<div class="empty">Could not load the studio: ${safe(error.message)}</div>`);
