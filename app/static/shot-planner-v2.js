var shotPlannerAssetsV2=[];
var activeSceneIdV2=null;
var shotInspectorViewV2='story';

function setupShotPlannerV2(){
  const panel=document.querySelector('.shot-panel');
  if(!panel||panel.classList.contains('shot-v2'))return;
  panel.classList.add('shot-v2');
  const close=panel.querySelector(':scope > .close'),eyebrow=panel.querySelector(':scope > .eyebrow'),title=panel.querySelector(':scope > .shot-title'),director=panel.querySelector(':scope > .director-agent-panel'),legacyWorkspace=panel.querySelector(':scope > .shot-workspace'),tree=legacyWorkspace.querySelector('#shot-tree'),editor=legacyWorkspace.querySelector('.shot-editor'),empty=editor.querySelector('#shot-editor-empty'),form=editor.querySelector('#shot-form');
  title.classList.add('shot-v2-header');title.querySelector('h2').textContent='Storyboard & Shot Planner';title.querySelector('.form-intro').textContent='Turn story beats into visual coverage, then direct one understandable shot at a time.';
  const guidance=document.createElement('section');guidance.id='shot-craft-guidance';
  const shell=document.createElement('div');shell.className='shot-v2-shell';
  const scenes=document.createElement('aside');scenes.className='shot-v2-scenes';scenes.innerHTML='<header><div><p class="eyebrow">STORY FLOW</p><h3>Scenes & beats</h3></div><span id="shot-scene-count-v2">0</span></header>';scenes.appendChild(tree);
  const main=document.createElement('main');main.className='shot-v2-main';
  const board=document.createElement('section');board.className='shot-board-v2';board.innerHTML='<div class="shot-v2-empty"><span>SHOT BOARD</span><h3>Build scenes from the story</h3><p>Kizuna will create an editable coverage skeleton. Nothing becomes final until you direct and approve it.</p></div>';
  const inspector=document.createElement('section');inspector.className='shot-inspector-v2';inspector.append(empty,form);main.append(board,inspector);
  const copilot=document.createElement('aside');copilot.className='shot-director-v2';copilot.appendChild(director);decorateDirectorV2(director);
  shell.append(scenes,main,copilot);legacyWorkspace.remove();panel.append(guidance,shell);panel.prepend(close,eyebrow,title);
  setupShotInspectorV2(form);
}

function setupShotInspectorV2(form){
  if(form.classList.contains('shot-form-v2'))return;form.classList.add('shot-form-v2');
  const core=form.querySelector('.shot-core-grid'),description=form.elements.shot_description.closest('label'),locationGrid=form.elements.shot_location.closest('.shot-core-grid'),characters=form.querySelector('fieldset'),action=form.elements.shot_action.closest('label'),dialogue=form.elements.shot_dialogue.closest('label'),camera=form.querySelector('.camera-section'),continuity=form.elements.shot_continuity.closest('label'),save=form.querySelector(':scope > button.primary'),result=form.querySelector('#shot-result');
  const header=document.createElement('header');header.className='shot-inspector-head-v2';header.innerHTML='<div><p class="eyebrow">SELECTED SHOT</p><h3 id="shot-inspector-title-v2">Direct the frame</h3><p id="shot-inspector-context-v2">Choose a shot card above.</p></div><span id="shot-inspector-status-v2">OPEN</span>';
  const tabs=document.createElement('nav');tabs.className='shot-inspector-tabs-v2';tabs.setAttribute('aria-label','Shot planning views');tabs.innerHTML='<button type="button" class="active" data-shot-view="story">Story & action</button><button type="button" data-shot-view="camera">Camera</button><button type="button" data-shot-view="continuity">Continuity & frame</button>';
  const panels=document.createElement('div');panels.className='shot-inspector-panels-v2';
  const story=document.createElement('section');story.dataset.shotPanel='story';story.className='shot-inspector-panel-v2';story.append(core,description,locationGrid,characters,action,dialogue);
  const cameraPanel=document.createElement('section');cameraPanel.dataset.shotPanel='camera';cameraPanel.className='shot-inspector-panel-v2';cameraPanel.append(camera);
  const continuityPanel=document.createElement('section');continuityPanel.dataset.shotPanel='continuity';continuityPanel.className='shot-inspector-panel-v2';continuityPanel.append(continuity,result);
  panels.append(story,cameraPanel,continuityPanel);form.append(header,tabs,panels,save);tabs.querySelectorAll('[data-shot-view]').forEach(button=>button.onclick=()=>setShotInspectorViewV2(button.dataset.shotView));setShotInspectorViewV2('story');
}

function decorateDirectorV2(director){
  if(!director||director.classList.contains('director-v2-ready'))return;director.classList.add('director-v2-ready');
  const intro=director.querySelector('.director-agent-intro'),heading=intro.firstElementChild,controls=director.querySelector('.director-agent-controls');heading.querySelector('.eyebrow').textContent='AI DIRECTOR';heading.querySelector('h3').textContent='Plan coverage together';heading.querySelector('p:not(.eyebrow)').textContent='Ask for coverage, performance, or pacing help. The Director proposes a complete package and waits for your approval.';
  const objective=controls.querySelector('#director-objective'),ask=controls.querySelector('#ask-director');objective.placeholder='Try: Cover this scene intimately without losing the geography.';ask.textContent='Send to Director';
  const prompts=document.createElement('div');prompts.className='director-prompts-v2';prompts.innerHTML='<button type="button">Find the essential coverage</button><button type="button">Strengthen visual storytelling</button><button type="button">Check screen direction and eyelines</button>';
  prompts.querySelectorAll('button').forEach(button=>button.onclick=()=>{objective.value=button.textContent;objective.focus();});
  const settings=document.createElement('details');settings.className='advanced-settings director-settings-v2';settings.innerHTML='<summary>Coverage settings</summary>';const body=document.createElement('div');[...controls.querySelectorAll('label')].filter(label=>!label.contains(objective)).forEach(label=>body.appendChild(label));settings.appendChild(body);
  const message=objective.closest('label');message.classList.add('director-message-v2');controls.replaceChildren(prompts,message,ask,settings);intro.replaceChildren(heading,controls);
}

function setShotInspectorViewV2(view){
  shotInspectorViewV2=view;const form=document.querySelector('#shot-form');if(!form)return;form.querySelectorAll('[data-shot-view]').forEach(button=>button.classList.toggle('active',button.dataset.shotView===view));form.querySelectorAll('[data-shot-panel]').forEach(panel=>panel.hidden=panel.dataset.shotPanel!==view);
}

async function refreshShotAssetsV2(projectId){
  if(!projectId){shotPlannerAssetsV2=[];return;}const library=await api(`/api/projects/${projectId}/asset-reviews`).catch(()=>({assets:[]}));shotPlannerAssetsV2=(library.assets||[]).filter(item=>item.asset_type==='storyboard');
}
function storyboardForShotV2(shotId){return shotPlannerAssetsV2.filter(item=>Number(item.group_id)===Number(shotId)).sort((a,b)=>Number(b.active)-Number(a.active)||b.version-a.version)[0];}

async function openShotPlanner(projectId){
  setupShotPlannerV2();if(!projects.length)await loadProjects();if(!projects.length){projectDialog.showModal();return;}if(!generationProviders.length)generationProviders=(await api('/api/generation/providers')).providers;
  const select=document.querySelector('#shot-project'),selected=projectId||Number(select.value)||projects[0].id;select.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(selected));
  select.onchange=async()=>{activeShotId=null;activeSceneIdV2=null;await refreshShotAssetsV2(Number(select.value));renderShotTree(Number(select.value));selectFirstShotV2(Number(select.value));renderCraftGuidance('#shot-craft-guidance',Number(select.value),'shots');};
  await refreshShotAssetsV2(Number(select.value));const project=projects.find(item=>item.id===Number(select.value));if(!activeShotId)activeShotId=project?.scenes?.[0]?.shots?.[0]?.id||null;renderShotTree(Number(select.value));if(activeShotId)selectShot(Number(select.value),activeShotId);else hideShotEditor();renderCraftGuidance('#shot-craft-guidance',Number(select.value),'shots');openWorkspace(shotDialog);
}

function selectFirstShotV2(projectId){const project=projects.find(item=>item.id===projectId),shot=project?.scenes?.[0]?.shots?.[0];if(shot)selectShot(projectId,shot.id);else hideShotEditor();}

function shotSceneV2(project){return project?.scenes.find(scene=>scene.id===activeSceneIdV2)||project?.scenes.find(scene=>scene.shots.some(shot=>shot.id===activeShotId))||project?.scenes[0];}

function renderShotTree(projectId){
  const project=projects.find(item=>item.id===projectId),tree=document.querySelector('#shot-tree'),expand=document.querySelector('#expand-story'),scenes=project?.scenes||[];document.querySelector('#shot-scene-count-v2').textContent=String(scenes.length);expand.disabled=Boolean(scenes.length);expand.textContent=scenes.length?'Story scenes ready':'Build scenes from story';
  const activeScene=shotSceneV2(project);activeSceneIdV2=activeScene?.id||null;
  tree.innerHTML=scenes.length?scenes.map(scene=>{const duration=scene.shots.reduce((total,shot)=>total+Number(shot.duration_seconds||0),0);return `<button type="button" class="scene-card-v2 ${activeSceneIdV2===scene.id?'active':''}" data-scene-id="${scene.id}"><span>${String(scene.position).padStart(2,'0')}</span><div><b>${safe(scene.title)}</b><small>${scene.shots.length} shot${scene.shots.length===1?'':'s'} · ${duration.toFixed(1)}s</small></div><em>${scene.shots.filter(shot=>shot.plan).length}/${scene.shots.length}</em></button>`;}).join(''):'<div class="shot-v2-empty compact"><b>No scenes yet</b><span>Develop the story, then build its initial coverage.</span></div>';
  tree.querySelectorAll('[data-scene-id]').forEach(button=>button.onclick=()=>chooseSceneV2(projectId,Number(button.dataset.sceneId)));renderShotBoardV2(projectId);
}

function chooseSceneV2(projectId,sceneId){const project=projects.find(item=>item.id===projectId),scene=project?.scenes.find(item=>item.id===sceneId);if(!scene)return;activeSceneIdV2=sceneId;renderShotTree(projectId);if(scene.shots.length)selectShot(projectId,scene.shots[0].id);else hideShotEditor();}

function renderShotBoardV2(projectId){
  const project=projects.find(item=>item.id===projectId),scene=shotSceneV2(project),host=document.querySelector('.shot-board-v2');if(!scene){host.innerHTML='<div class="shot-v2-empty"><span>SHOT BOARD</span><h3>No coverage yet</h3><p>Build scenes from the approved story to create the first editable shot skeleton.</p></div>';return;}
  host.innerHTML=`<header><div><p class="eyebrow">SCENE ${String(scene.position).padStart(2,'0')}</p><h3>${safe(scene.title)}</h3><p>${safe(scene.summary||scene.purpose||'Direct the visual progression of this scene.')}</p></div><span>${scene.shots.length} SHOTS</span></header><div class="shot-card-grid-v2">${scene.shots.map(shot=>{const asset=storyboardForShotV2(shot.id),camera=shot.plan?.camera||{},size=camera.shot_size||'unplanned';return `<button type="button" class="shot-card-v2 ${activeShotId===shot.id?'active':''}" data-shot-id="${shot.id}"><figure>${asset?`<img src="${safe(asset.uri)}" alt="Storyboard for ${safe(shot.title)}">`:`<div class="shot-slate-v2"><i></i><b>${safe(size==='unplanned'?'PLAN':size.split(' ').map(word=>word[0]).join('').toUpperCase())}</b></div>`}<span>${Number(shot.duration_seconds).toFixed(1)}s</span></figure><div><small>SHOT ${String(shot.position).padStart(2,'0')} · ${safe(size)}</small><b>${safe(shot.title)}</b><p>${safe(shot.description||shot.plan?.action||'Action ready to direct.')}</p></div><em>${shot.plan?'PLANNED':'OPEN'}</em></button>`;}).join('')}</div>`;
  host.querySelectorAll('[data-shot-id]').forEach(button=>button.onclick=()=>selectShot(projectId,Number(button.dataset.shotId)));
}

var selectShotBeforeV2=selectShot;selectShot=function(projectId,shotId){const project=projects.find(item=>item.id===projectId),found=findShot(project,shotId);if(found)activeSceneIdV2=found.scene.id;selectShotBeforeV2(projectId,shotId);renderShotBoardV2(projectId);const title=document.querySelector('#shot-inspector-title-v2'),context=document.querySelector('#shot-inspector-context-v2'),status=document.querySelector('#shot-inspector-status-v2');if(found&&title){title.textContent=found.shot.title;context.textContent=`Scene ${found.scene.position} · Shot ${found.shot.position} · ${Number(found.shot.duration_seconds).toFixed(1)} seconds`;status.textContent=found.shot.plan?'PLANNED':'OPEN';}setShotInspectorViewV2(shotInspectorViewV2);};

var hideShotEditorBeforeV2=hideShotEditor;hideShotEditor=function(){hideShotEditorBeforeV2();const board=document.querySelector('.shot-board-v2');if(board&&!currentShotProject()?.scenes.length)renderShotBoardV2(Number(document.querySelector('#shot-project').value));};

var renderStoryboardJobBeforeV2=renderStoryboardJob;renderStoryboardJob=function(job){renderStoryboardJobBeforeV2(job);if(job.assets?.length){const projectId=Number(document.querySelector('#shot-project').value);refreshShotAssetsV2(projectId).then(()=>renderShotBoardV2(projectId));}};

setupShotPlannerV2();
