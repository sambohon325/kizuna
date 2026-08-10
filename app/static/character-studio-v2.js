var characterStudioAssetsV2=[];
var characterStudioViewV2='identity';

function setupCharacterStudioV2(){
  const form=document.querySelector('#character-form');
  if(!form||form.classList.contains('character-v2'))return;
  form.classList.add('character-v2');
  const close=form.querySelector(':scope > .close');
  const eyebrow=form.querySelector(':scope > .eyebrow');
  const title=form.querySelector(':scope > h2');
  const intro=form.querySelector(':scope > .form-intro');
  const projectLabel=[...form.querySelectorAll(':scope > label')].find(label=>label.querySelector('#character-project'));
  const roster=form.querySelector('#character-roster');
  const tabs=form.querySelector('.character-view-tabs');
  const story=form.querySelector('#character-story-panel');
  const identity=form.querySelector('.character-identity-section');
  const visual=form.querySelector('.character-visual-section');
  const agent=form.querySelector('.character-ai-panel');
  const saveButton=form.querySelector(':scope > button.primary');
  const result=form.querySelector('#character-result');

  const header=document.createElement('header');
  header.className='character-v2-header';
  const heading=document.createElement('div');
  heading.className='character-v2-heading';
  [eyebrow,title,intro].forEach(node=>node&&heading.appendChild(node));
  const controls=document.createElement('div');
  controls.className='character-v2-project';
  if(projectLabel)controls.appendChild(projectLabel);
  header.append(heading,controls);

  const shell=document.createElement('div');
  shell.className='character-v2-shell';
  const cast=document.createElement('aside');
  cast.className='character-v2-cast';
  cast.innerHTML='<header><div><p class="eyebrow">YOUR CAST</p><h3>Character cards</h3></div><span id="character-cast-count">0</span></header>';
  cast.appendChild(roster);

  const workspace=document.createElement('main');
  workspace.className='character-v2-workspace';
  tabs.innerHTML='<button type="button" class="active" data-character-view="identity">Identity</button><button type="button" data-character-view="story">Story & arc</button><button type="button" data-character-view="visual">Visual design</button><button type="button" data-character-view="model">Model sheet</button><button type="button" data-character-view="assets">Assets</button>';
  tabs.classList.add('character-v2-tabs');
  const panels=document.createElement('div');
  panels.className='character-v2-panels';
  identity.classList.add('character-v2-panel');identity.dataset.characterPanel='identity';
  story.classList.add('character-v2-panel');story.dataset.characterPanel='story';
  visual.classList.add('character-v2-panel');visual.dataset.characterPanel='visual';
  const model=document.createElement('section');
  model.className='character-v2-panel character-v2-model';model.dataset.characterPanel='model';
  model.innerHTML='<div class="character-v2-empty"><span>MODEL SHEET</span><h3>Build a reusable performance model</h3><p>Save the identity and visual anchors first. Kizuna will track the views, expressions, wardrobe, and consistency references needed for production.</p></div>';
  model.appendChild(result);
  const assets=document.createElement('section');
  assets.id='character-assets-v2';assets.className='character-v2-panel character-v2-assets';assets.dataset.characterPanel='assets';
  panels.append(identity,story,visual,model,assets);
  saveButton.classList.add('character-v2-save');
  saveButton.textContent='Save character identity';
  workspace.append(tabs,panels,saveButton);

  const copilot=document.createElement('aside');
  copilot.className='character-v2-copilot';
  copilot.appendChild(agent);
  decorateCharacterDesignerV2(agent);
  shell.append(cast,workspace,copilot);
  form.append(header,shell);
  form.prepend(close);
  tabs.querySelectorAll('[data-character-view]').forEach(button=>button.onclick=()=>setCharacterView(button.dataset.characterView));
  setCharacterView('identity');
}

function decorateCharacterDesignerV2(agent){
  if(!agent||agent.classList.contains('character-ai-v2'))return;
  agent.classList.add('character-ai-v2');
  agent.querySelector('.visual-agent-head .eyebrow').textContent='AI CHARACTER DESIGNER';
  agent.querySelector('.visual-agent-head h3').textContent='Design together';
  agent.querySelector('.visual-agent-head p:not(.eyebrow)').textContent='Describe the person, their story, or what feels wrong. Your designer uses the production context and keeps every change reviewable.';
  const controls=agent.querySelector('.visual-agent-controls');
  const objective=controls.querySelector('#character-agent-objective');
  objective.placeholder='Try: Make the silhouette feel guarded without making them look villainous.';
  const ask=controls.querySelector('#ask-character-designer');
  ask.textContent='Send to Designer';
  const suggestions=document.createElement('div');
  suggestions.className='character-ai-prompts';
  suggestions.innerHTML='<button type="button">Find a stronger silhouette</button><button type="button">Connect the design to their history</button><button type="button">Create animation-friendly identity locks</button>';
  suggestions.querySelectorAll('button').forEach(button=>button.onclick=()=>{objective.value=button.textContent;objective.focus();});
  const settings=document.createElement('details');
  settings.className='advanced-settings character-ai-settings';
  settings.innerHTML='<summary>Designer settings</summary>';
  const settingsBody=document.createElement('div');
  [...controls.querySelectorAll('label')].filter(label=>!label.contains(objective)).forEach(label=>settingsBody.appendChild(label));
  settings.appendChild(settingsBody);
  const promptLabel=objective.closest('label');
  promptLabel.classList.add('character-ai-message');
  controls.replaceChildren(suggestions,promptLabel,ask,settings);
}

function setCharacterView(view){
  characterStudioViewV2=view;
  const form=document.querySelector('#character-form');
  form.dataset.characterView=view;
  form.querySelectorAll('[data-character-view]').forEach(button=>button.classList.toggle('active',button.dataset.characterView===view));
  form.querySelectorAll('[data-character-panel]').forEach(panel=>panel.hidden=panel.dataset.characterPanel!==view);
  const save=form.querySelector('.character-v2-save');
  save.hidden=['story','model','assets'].includes(view);
  save.textContent=view==='visual'?'Save visual model':activeCharacterId?'Save character identity':'Create character card';
  if(view==='assets')renderCharacterAssetsV2();
  if(view==='model')renderCharacterModelCoverageV2();
}

async function refreshCharacterAssetsV2(projectId){
  if(!projectId){characterStudioAssetsV2=[];return;}
  const library=await api(`/api/projects/${projectId}/asset-reviews`).catch(()=>({assets:[]}));
  characterStudioAssetsV2=(library.assets||[]).filter(item=>item.asset_type==='character');
}

function characterAssetsForV2(characterId){
  return characterStudioAssetsV2.filter(item=>Number(item.group_id)===Number(characterId)).sort((a,b)=>b.version-a.version);
}

function characterPortraitV2(character){
  const asset=characterAssetsForV2(character.id)[0];
  return asset?`<img src="${safe(asset.uri)}" alt="${safe(character.name)} reference">`:`<span>${safe(character.name.slice(0,1).toUpperCase())}</span>`;
}

async function openCharacterStudio(projectId){
  setupCharacterStudioV2();
  if(!projects.length)await loadProjects();
  if(!projects.length){projectDialog.showModal();return;}
  if(!generationProviders.length)generationProviders=(await api('/api/generation/providers')).providers;
  const projectSelect=document.querySelector('#character-project');
  const selected=projectId||Number(projectSelect.value)||projects[0].id;
  projectSelect.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(selected));
  projectSelect.onchange=async()=>{activeCharacterId=null;clearCharacterForm();await refreshCharacterAssetsV2(Number(projectSelect.value));renderCharacterRoster(Number(projectSelect.value));setCharacterView('identity');};
  await refreshCharacterAssetsV2(Number(projectSelect.value));
  const cast=projects.find(project=>project.id===Number(projectSelect.value))?.characters||[];
  if(!activeCharacterId&&cast.length)activeCharacterId=cast[0].id;
  renderCharacterRoster(Number(projectSelect.value));
  if(activeCharacterId)selectCharacter(Number(projectSelect.value),activeCharacterId);
  else{clearCharacterForm();setCharacterView('identity');}
  openWorkspace(characterDialog);
}

function renderCharacterRoster(projectId){
  const roster=projects.find(project=>project.id===projectId)?.characters||[];
  const host=document.querySelector('#character-roster');
  document.querySelector('#character-cast-count').textContent=String(roster.length);
  host.innerHTML=`<button type="button" class="character-card-v2 new ${activeCharacterId===null?'active':''}" data-new-character><span>＋</span><b>New character</b><small>Start with their role in the story</small></button>${roster.map(character=>`<button type="button" class="character-card-v2 ${activeCharacterId===character.id?'active':''}" data-character-id="${character.id}"><figure>${characterPortraitV2(character)}</figure><div><b>${safe(character.name)}</b><small>${safe(character.role)}</small><em>${character.design?'Model v'+character.design.version:'Identity open'}</em></div></button>`).join('')}`;
  host.querySelector('[data-new-character]').onclick=()=>{activeCharacterId=null;clearCharacterForm();renderCharacterRoster(projectId);setCharacterView('identity');};
  host.querySelectorAll('[data-character-id]').forEach(button=>button.onclick=()=>{selectCharacter(projectId,Number(button.dataset.characterId));setCharacterView('identity');});
}

var clearCharacterFormBeforeV2=clearCharacterForm;
clearCharacterForm=function(){
  clearCharacterFormBeforeV2();
  renderCharacterAssetsV2();
  renderCharacterModelCoverageV2();
};

var selectCharacterBeforeV2=selectCharacter;
selectCharacter=function(projectId,characterId){
  selectCharacterBeforeV2(projectId,characterId);
  renderCharacterAssetsV2();
  renderCharacterModelCoverageV2();
  setCharacterView(characterStudioViewV2);
};

function renderCharacterAssetsV2(){
  const host=document.querySelector('#character-assets-v2');
  if(!host)return;
  if(!activeCharacterId){host.innerHTML='<div class="character-v2-empty"><span>ASSET LIBRARY</span><h3>Create or select a character</h3><p>Reference images, generated sheets, wardrobe, expressions, and approved production assets will live here.</p></div>';return;}
  const project=projects.find(item=>item.id===Number(document.querySelector('#character-project').value));
  const character=project?.characters.find(item=>item.id===activeCharacterId);
  const assets=characterAssetsForV2(activeCharacterId);
  host.innerHTML=`<header class="character-assets-head"><div><p class="eyebrow">${safe(character?.name||'CHARACTER')} LIBRARY</p><h3>References & production assets</h3><p>Upload your own design or keep generated versions together. Selecting a version makes it the reference used by new shots.</p></div><label class="character-upload-v2">Upload reference<input id="character-reference-upload" type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"></label></header>${assets.length?`<div class="character-assets-grid">${assets.map(asset=>`<article class="character-asset-card ${asset.active?'active':''}"><figure><img src="${safe(asset.uri)}" alt="${safe(character?.name||'Character')} asset version ${asset.version}"></figure><div><b>Reference v${asset.version}</b><span>${asset.active?'Active in production':safe(asset.review_status||'pending')}</span><small>${safe(asset.mime_type||'image')}</small>${asset.active?'':`<button type="button" data-use-character-asset="${asset.id}">Use in production</button>`}</div></article>`).join('')}</div>`:'<div class="character-upload-empty"><b>No visual references yet</b><p>Upload an existing design, or use Model sheet to generate the first reference from the character bible.</p></div>'}<div id="character-upload-status"></div>`;
  document.querySelector('#character-reference-upload').onchange=uploadCharacterReferenceV2;
  host.querySelectorAll('[data-use-character-asset]').forEach(button=>button.onclick=()=>selectCharacterAssetV2(Number(button.dataset.useCharacterAsset)));
}

async function uploadCharacterReferenceV2(event){
  const file=event.target.files[0],statusHost=document.querySelector('#character-upload-status');
  if(!file||!activeCharacterId)return;
  statusHost.innerHTML='<div class="render-progress">Checking and adding the reference…</div>';
  try{
    const csrf=(document.cookie.match(/(?:^|; )kizuna_csrf=([^;]+)/)||[])[1]||'';
    const response=await fetch(`/api/characters/${activeCharacterId}/assets/upload?filename=${encodeURIComponent(file.name)}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream','X-Kizuna-CSRF':decodeURIComponent(csrf)},body:file});
    if(!response.ok)throw new Error(await response.text());
    await refreshCharacterAssetsV2(Number(document.querySelector('#character-project').value));
    renderCharacterRoster(Number(document.querySelector('#character-project').value));
    renderCharacterAssetsV2();
  }catch(error){statusHost.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}

async function selectCharacterAssetV2(assetId){
  await api(`/api/assets/character/${assetId}/review`,{method:'PUT',body:JSON.stringify({status:'approved',notes:'Selected in Character Studio',selected:true})});
  await refreshCharacterAssetsV2(Number(document.querySelector('#character-project').value));
  renderCharacterRoster(Number(document.querySelector('#character-project').value));
  renderCharacterAssetsV2();
}

function renderCharacterModelCoverageV2(){
  const host=document.querySelector('.character-v2-model');
  if(!host)return;
  let coverage=host.querySelector('.character-model-coverage-v2');
  if(!coverage){coverage=document.createElement('section');coverage.className='character-model-coverage-v2';host.prepend(coverage);}
  if(!activeCharacterId){coverage.innerHTML='<div class="character-v2-empty"><span>MODEL SHEET</span><h3>Select a character to build their views</h3><p>The finished model tracks drawing angles, expression range, wardrobe, scale, and identity locks.</p></div>';return;}
  const project=projects.find(item=>item.id===Number(document.querySelector('#character-project').value));
  const character=project?.characters.find(item=>item.id===activeCharacterId);
  const source=characterAssetsForV2(activeCharacterId)[0];
  const views=['Front','Three-quarter','Profile','Back','Expression set','Wardrobe','Scale chart'];
  coverage.innerHTML=`<header><div><p class="eyebrow">PRODUCTION COVERAGE</p><h3>${safe(character?.name||'Character')} model sheet</h3><p>${source?'A source reference is attached. Generate a sheet to fill the missing production views.':'Add a source reference or generate a first sheet from the visual bible.'}</p></div><span>${source?'1 / 7':'0 / 7'} ready</span></header><div class="character-view-grid">${views.map((view,index)=>`<article class="${source&&index===0?'ready':''}"><figure>${source&&index===0?`<img src="${safe(source.uri)}" alt="Source character reference">`:'<span>＋</span>'}</figure><b>${view}</b><small>${source&&index===0?'Source reference':'Needed'}</small></article>`).join('')}</div><div class="character-model-note"><b>Consistency lock</b><span>${safe((character?.design?.consistency_anchors||[]).join(' · ')||'Save visual anchors so every view preserves the same identity.')}</span></div>`;
}

setupCharacterStudioV2();
