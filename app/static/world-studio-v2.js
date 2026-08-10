var worldStudioAssetsV2=[];
var worldStudioViewV2='story';

function setupWorldStudioV2(){
  const form=document.querySelector('#world-form');
  if(!form||form.classList.contains('world-v2'))return;
  form.classList.add('world-v2');
  const close=form.querySelector(':scope > .close');
  const eyebrow=form.querySelector(':scope > .eyebrow');
  const title=form.querySelector(':scope > h2');
  const intro=form.querySelector(':scope > .form-intro');
  const projectLabel=[...form.querySelectorAll(':scope > label')].find(label=>label.querySelector('#world-project'));
  const roster=form.querySelector('#world-roster');
  const sections=[...form.querySelectorAll(':scope > .world-section')];
  const agent=roster.nextElementSibling;
  const saveButton=form.querySelector(':scope > button.primary');
  const result=form.querySelector('#world-result');

  const header=document.createElement('header');header.className='world-v2-header';
  const heading=document.createElement('div');heading.className='world-v2-heading';[eyebrow,title,intro].forEach(node=>node&&heading.appendChild(node));
  const controls=document.createElement('div');controls.className='world-v2-project';if(projectLabel)controls.appendChild(projectLabel);header.append(heading,controls);

  const shell=document.createElement('div');shell.className='world-v2-shell';
  const atlas=document.createElement('aside');atlas.className='world-v2-atlas';
  atlas.innerHTML='<header><div><p class="eyebrow">WORLD ATLAS</p><h3>Story locations</h3></div><span id="world-count-v2">0</span></header><div class="world-map-v2" aria-hidden="true"><i></i><i></i><i></i><b>K</b></div>';
  atlas.appendChild(roster);

  const workspace=document.createElement('main');workspace.className='world-v2-workspace';
  const tabs=document.createElement('nav');tabs.className='world-v2-tabs';tabs.setAttribute('aria-label','World development stages');
  tabs.innerHTML='<button type="button" class="active" data-world-view="story">Story role</button><button type="button" data-world-view="place">Place & staging</button><button type="button" data-world-view="visual">Visual system</button><button type="button" data-world-view="production">Layers & light</button><button type="button" data-world-view="assets">Assets</button>';
  const panels=document.createElement('div');panels.className='world-v2-panels';
  const panel=(key,kicker,titleText,description)=>{const node=document.createElement('section');node.className='world-v2-panel';node.dataset.worldPanel=key;node.innerHTML=`<header><p class="eyebrow">${kicker}</p><h3>${titleText}</h3><p>${description}</p></header>`;return node;};
  const story=panel('story','WHY THIS PLACE EXISTS','Give the world a dramatic purpose','Start with what happens here and how the location changes the people who enter it.');
  const place=panel('place','MAKE IT NAVIGABLE','Build geography and staging','Define where people can move, where the camera can stand, and how scale affects the drama.');
  const visual=panel('visual','MAKE IT RECOGNIZABLE','Choose the visual construction','Architecture, materials, atmosphere, and palette should make the place identifiable in a single frame.');
  const production=panel('production','MAKE IT REUSABLE','Plan layers, light, and continuity','Break the environment into production layers and lighting variants that can survive every shot.');
  const assets=panel('assets','LOCATION LIBRARY','References & production assets','Upload your own environment art or compare generated versions, then select the source used by new shots.');assets.id='world-assets-v2';
  const moveField=(name,target)=>{const field=form.elements[name];const label=field?.closest('label');if(label)target.appendChild(label);};
  ['name','narrative_function','description'].forEach(name=>moveField(name,story));
  const placeGrid=document.createElement('div');placeGrid.className='world-v2-grid';place.appendChild(placeGrid);['geography','time_period','scale','perspective'].forEach(name=>moveField(name,placeGrid));moveField('staging_zones',place);
  const visualGrid=document.createElement('div');visualGrid.className='world-v2-grid';visual.appendChild(visualGrid);['architecture','materials','atmosphere'].forEach(name=>moveField(name,visualGrid));moveField('world_palette',visual);
  ['layers','lighting_variants','continuity_anchors'].forEach(name=>moveField(name,production));production.appendChild(result);
  panels.append(story,place,visual,production,assets);workspace.append(tabs,panels,saveButton);
  saveButton.classList.add('world-v2-save');saveButton.textContent='Save story location';

  const copilot=document.createElement('aside');copilot.className='world-v2-copilot';agent.classList.add('world-ai-v2');copilot.appendChild(agent);decorateBackgroundArtistV2(agent);
  shell.append(atlas,workspace,copilot);form.append(header,shell);form.prepend(close);
  sections.forEach(section=>section.remove());
  tabs.querySelectorAll('[data-world-view]').forEach(button=>button.onclick=()=>setWorldViewV2(button.dataset.worldView));
  setWorldViewV2('story');
}

function decorateBackgroundArtistV2(agent){
  if(!agent||agent.classList.contains('world-ai-ready'))return;agent.classList.add('world-ai-ready');
  agent.querySelector('.visual-agent-head .eyebrow').textContent='AI BACKGROUND ARTIST';
  agent.querySelector('.visual-agent-head h3').textContent='Build the world together';
  agent.querySelector('.visual-agent-head p:not(.eyebrow)').textContent='Describe the feeling, story problem, or practical production need. The Artist uses the story and Creative DNA, then returns a proposal for review.';
  const controls=agent.querySelector('.visual-agent-controls'),objective=controls.querySelector('#background-agent-objective'),ask=controls.querySelector('#ask-background-artist');
  objective.placeholder='Try: Make this sanctuary feel subtly unsafe before the reveal.';ask.textContent='Send to Artist';
  const prompts=document.createElement('div');prompts.className='world-ai-prompts';prompts.innerHTML='<button type="button">Connect the location to the story</button><button type="button">Improve staging and camera access</button><button type="button">Create reusable parallax layers</button>';
  prompts.querySelectorAll('button').forEach(button=>button.onclick=()=>{objective.value=button.textContent;objective.focus();});
  const settings=document.createElement('details');settings.className='advanced-settings world-ai-settings';settings.innerHTML='<summary>Artist settings</summary>';const body=document.createElement('div');
  [...controls.querySelectorAll('label')].filter(label=>!label.contains(objective)).forEach(label=>body.appendChild(label));settings.appendChild(body);
  const message=objective.closest('label');message.classList.add('world-ai-message');controls.replaceChildren(prompts,message,ask,settings);
}

function setWorldViewV2(view){
  worldStudioViewV2=view;const form=document.querySelector('#world-form');form.dataset.worldView=view;
  form.querySelectorAll('[data-world-view]').forEach(button=>button.classList.toggle('active',button.dataset.worldView===view));
  form.querySelectorAll('[data-world-panel]').forEach(panel=>panel.hidden=panel.dataset.worldPanel!==view);
  const save=form.querySelector('.world-v2-save');save.hidden=view==='assets';
  save.textContent=view==='story'?(activeLocationId?'Save story location':'Create story location'):view==='place'?'Save geography & staging':view==='visual'?'Save visual system':'Save layers & lighting';
  if(view==='assets')renderWorldAssetsV2();
  renderWorldCompassV2();
}

async function refreshWorldAssetsV2(projectId){
  if(!projectId){worldStudioAssetsV2=[];return;}
  const library=await api(`/api/projects/${projectId}/asset-reviews`).catch(()=>({assets:[]}));worldStudioAssetsV2=(library.assets||[]).filter(item=>item.asset_type==='background');
}
function worldAssetsForV2(locationId){return worldStudioAssetsV2.filter(item=>Number(item.group_id)===Number(locationId)).sort((a,b)=>b.version-a.version);}
function worldThumbnailV2(location){const asset=worldAssetsForV2(location.id)[0];return asset?`<img src="${safe(asset.uri)}" alt="${safe(location.name)} reference">`:'<span>◇</span>';}

async function openWorldStudio(projectId){
  setupWorldStudioV2();if(!projects.length)await loadProjects();if(!projects.length){projectDialog.showModal();return;}if(!generationProviders.length)generationProviders=(await api('/api/generation/providers')).providers;
  const select=document.querySelector('#world-project'),selected=projectId||Number(select.value)||projects[0].id;select.innerHTML=options(projects.map(project=>({id:String(project.id),label:project.title})),String(selected));
  select.onchange=async()=>{activeLocationId=null;clearWorldForm();await refreshWorldAssetsV2(Number(select.value));const locations=projects.find(project=>project.id===Number(select.value))?.locations||[];if(locations.length)activeLocationId=locations[0].id;renderWorldRoster(Number(select.value));if(activeLocationId)selectWorld(Number(select.value),activeLocationId);setWorldViewV2('story');};
  await refreshWorldAssetsV2(Number(select.value));const locations=projects.find(project=>project.id===Number(select.value))?.locations||[];if(!activeLocationId&&locations.length)activeLocationId=locations[0].id;renderWorldRoster(Number(select.value));if(activeLocationId)selectWorld(Number(select.value),activeLocationId);else clearWorldForm();setWorldViewV2('story');openWorkspace(worldDialog);
}

function renderWorldRoster(projectId){
  const locations=projects.find(project=>project.id===projectId)?.locations||[],host=document.querySelector('#world-roster');document.querySelector('#world-count-v2').textContent=String(locations.length);
  host.innerHTML=`<button type="button" class="world-card-v2 new ${activeLocationId===null?'active':''}" data-new-world><span>＋</span><b>New location</b><small>Start with its purpose in the story</small></button>${locations.map(location=>`<button type="button" class="world-card-v2 ${activeLocationId===location.id?'active':''}" data-location-id="${location.id}"><figure>${worldThumbnailV2(location)}</figure><div><b>${safe(location.name)}</b><small>${safe(location.narrative_function||location.geography||'Story purpose open')}</small><em>${location.design?'Bible v'+location.design.version:'Design open'}</em></div></button>`).join('')}`;
  host.querySelector('[data-new-world]').onclick=()=>{activeLocationId=null;clearWorldForm();renderWorldRoster(projectId);setWorldViewV2('story');};host.querySelectorAll('[data-location-id]').forEach(button=>button.onclick=()=>{selectWorld(projectId,Number(button.dataset.locationId));setWorldViewV2('story');});
}

var clearWorldFormBeforeV2=clearWorldForm;clearWorldForm=function(){clearWorldFormBeforeV2();renderWorldAssetsV2();renderWorldCompassV2();};
var selectWorldBeforeV2=selectWorld;selectWorld=function(projectId,locationId){selectWorldBeforeV2(projectId,locationId);renderWorldAssetsV2();renderWorldCompassV2();setWorldViewV2(worldStudioViewV2);};

function renderWorldCompassV2(){
  const map=document.querySelector('.world-map-v2');if(!map)return;const project=projects.find(item=>item.id===Number(document.querySelector('#world-project')?.value)),location=project?.locations.find(item=>item.id===activeLocationId);
  map.querySelector('b').textContent=location?safe(location.name.slice(0,1).toUpperCase()):'K';map.title=location?`${location.name} · ${location.geography||'geography open'}`:'World atlas';
}

function renderWorldAssetsV2(){
  const host=document.querySelector('#world-assets-v2');if(!host)return;
  if(!activeLocationId){host.innerHTML='<div class="world-v2-empty"><span>LOCATION LIBRARY</span><h3>Create or select a location</h3><p>Concept art, layouts, matte paintings, lighting variants, and approved production backgrounds will live here.</p></div>';return;}
  const project=projects.find(item=>item.id===Number(document.querySelector('#world-project').value)),location=project?.locations.find(item=>item.id===activeLocationId),assets=worldAssetsForV2(activeLocationId);
  host.innerHTML=`<header><div><p class="eyebrow">${safe(location?.name||'LOCATION')} LIBRARY</p><h3>References & production backgrounds</h3><p>Upload art you own or compare generated versions. Selecting one makes it the background source used by new shots.</p></div><label class="world-upload-v2">Upload reference<input id="world-reference-upload" type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"></label></header>${assets.length?`<div class="world-assets-grid">${assets.map(asset=>`<article class="world-asset-card ${asset.active?'active':''}"><figure><img src="${safe(asset.uri)}" alt="${safe(location?.name||'Location')} asset version ${asset.version}"></figure><div><b>Background v${asset.version}</b><span>${asset.active?'Active in production':safe(asset.review_status||'pending')}</span><small>${safe(asset.mime_type||'image')}</small>${asset.active?'':`<button type="button" data-use-world-asset="${asset.id}">Use in production</button>`}</div></article>`).join('')}</div>`:'<div class="world-upload-empty"><b>No visual references yet</b><p>Upload an existing environment design, or generate the first concept from Layers & light.</p></div>'}<div id="world-upload-status"></div>`;
  document.querySelector('#world-reference-upload').onchange=uploadWorldReferenceV2;host.querySelectorAll('[data-use-world-asset]').forEach(button=>button.onclick=()=>selectWorldAssetV2(Number(button.dataset.useWorldAsset)));
}

async function uploadWorldReferenceV2(event){
  const file=event.target.files[0],statusHost=document.querySelector('#world-upload-status');if(!file||!activeLocationId)return;statusHost.innerHTML='<div class="render-progress">Checking and adding the background…</div>';
  try{const csrf=(document.cookie.match(/(?:^|; )kizuna_csrf=([^;]+)/)||[])[1]||'',response=await fetch(`/api/locations/${activeLocationId}/assets/upload?filename=${encodeURIComponent(file.name)}`,{method:'POST',headers:{'Content-Type':file.type||'application/octet-stream','X-Kizuna-CSRF':decodeURIComponent(csrf)},body:file});if(!response.ok)throw new Error(await response.text());await refreshWorldAssetsV2(Number(document.querySelector('#world-project').value));renderWorldRoster(Number(document.querySelector('#world-project').value));renderWorldAssetsV2();}catch(error){statusHost.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}
}
async function selectWorldAssetV2(assetId){await api(`/api/assets/background/${assetId}/review`,{method:'PUT',body:JSON.stringify({status:'approved',notes:'Selected in Worlds & Backgrounds',selected:true})});await refreshWorldAssetsV2(Number(document.querySelector('#world-project').value));renderWorldRoster(Number(document.querySelector('#world-project').value));renderWorldAssetsV2();}

setupWorldStudioV2();
