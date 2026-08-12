/* Scene Compositor V2 keeps the existing API and editing behavior, but presents it
   as a familiar shot, canvas, layer-stack, and inspector workflow. */
(function setupCompositorStudioV2(){
  const dialog=document.querySelector('#compositor-dialog');
  if(!dialog||dialog.dataset.compositorV2)return;
  dialog.dataset.compositorV2='ready';

  const panel=dialog.querySelector('.compositor-panel');
  const title=dialog.querySelector('.compositor-title');
  const workspace=dialog.querySelector('.compositor-workspace');
  const shotBrowser=document.querySelector('#compositor-shots');
  const stageColumn=dialog.querySelector('.stage-column');
  const editor=document.querySelector('#composition-editor');
  const stage=document.querySelector('#composition-stage');
  const layers=document.querySelector('#composition-layers');
  const assetAdder=dialog.querySelector('.asset-adder');
  const legacyInspector=dialog.querySelector('.layer-inspector');
  const layerEmpty=document.querySelector('#layer-empty');
  const layerForm=document.querySelector('#layer-form');
  const camera=dialog.querySelector('.camera-controls');
  const animator=dialog.querySelector('.animator-agent-panel');
  const assetReview=dialog.querySelector('.asset-review-board');
  const result=document.querySelector('#composite-result');

  title.querySelector('h2').textContent='Scene Compositor';
  title.querySelector('.form-intro').textContent='Combine approved artwork into one camera-ready shot, then add motion without flattening the layers.';
  document.querySelector('#build-composition').textContent='Create layer stack';
  document.querySelector('#render-composition').textContent='Render still';
  document.querySelector('#render-motion').textContent='Render motion';

  const browserShell=document.createElement('aside');
  browserShell.className='comp-shot-browser';
  workspace.insertBefore(browserShell,shotBrowser);
  browserShell.innerHTML='<header class="comp-browser-head"><div><span>SHOT BROWSER</span><b>Finishing queue</b></div><small id="comp-shot-count">0 shots</small></header>';
  browserShell.appendChild(shotBrowser);
  stageColumn.insertAdjacentHTML('afterbegin','<header class="comp-monitor-head"><div><span id="comp-scene-label">PROGRAM MONITOR</span><h3 id="comp-shot-title">Select a shot</h3></div><div class="comp-monitor-meta"><span id="comp-shot-duration">--</span><span id="comp-version-status">Not built</span></div></header>');
  stage.parentNode.insertBefore(Object.assign(document.createElement('div'),{className:'comp-canvas-frame'}),stage).appendChild(stage);
  stage.insertAdjacentHTML('afterbegin','<div class="comp-safe-frame" aria-hidden="true"></div>');
  result.insertAdjacentHTML('beforebegin','<details class="comp-preview-drawer" open><summary><span>RENDER REVIEW</span><b>Still and motion previews</b></summary><div id="comp-preview-home"></div></details>');
  document.querySelector('#comp-preview-home').appendChild(result);

  const inspector=document.createElement('aside');
  inspector.className='comp-inspector';
  inspector.innerHTML='<nav class="comp-inspector-tabs" aria-label="Compositor inspector"><button type="button" class="active" data-comp-view="layers">Layers</button><button type="button" data-comp-view="camera">Camera & grade</button><button type="button" data-comp-view="ai">AI Animator</button></nav><section class="comp-inspector-panel active" data-comp-panel="layers"><header class="comp-panel-head"><div><span>LAYER STACK</span><b>Front to back</b></div><small id="comp-layer-count">0 layers</small></header><div id="comp-layer-home"></div><details class="comp-layer-properties" open><summary>Selected layer</summary><div id="comp-layer-form-home"></div></details></section><section class="comp-inspector-panel" data-comp-panel="camera"><div id="comp-camera-home"></div></section><section class="comp-inspector-panel" data-comp-panel="ai"><div id="comp-ai-home"></div></section>';
  workspace.appendChild(inspector);
  document.querySelector('#comp-layer-home').append(layers,assetAdder);
  document.querySelector('#comp-layer-form-home').append(layerEmpty,layerForm);
  document.querySelector('#comp-camera-home').appendChild(camera);
  camera.querySelector('.eyebrow').insertAdjacentHTML('afterend','<p class="comp-camera-intro">Frame the movement, then balance the finished image.</p>');
  document.querySelector('#comp-ai-home').appendChild(animator);
  legacyInspector.remove();

  animator.querySelector('h3').textContent='Direct the motion with me';
  animator.querySelector('.visual-agent-head p:not(.eyebrow)').textContent='Describe the performance or camera feeling. Kizuna proposes editable motion before changing the shot.';
  const animatorControls=animator.querySelector('.visual-agent-controls');
  const objective=animator.querySelector('#animator-objective').closest('label');
  objective.classList.add('comp-ai-objective');
  animatorControls.insertAdjacentHTML('afterbegin','<div class="comp-motion-prompts"><button type="button" data-motion-prompt="Add subtle performance motion while preserving the character model and composition.">Subtle performance</button><button type="button" data-motion-prompt="Strengthen the camera movement around the emotional turn without becoming distracting.">Stronger camera move</button><button type="button" data-motion-prompt="Polish layer motion and preserve screen direction, eyelines, and continuity.">Protect continuity</button></div>');
  const aiSettings=document.createElement('details');
  aiSettings.className='comp-ai-settings';
  aiSettings.innerHTML='<summary>Engine & output settings</summary><div></div>';
  [...animatorControls.querySelectorAll(':scope > label:not(.comp-ai-objective)')].forEach(label=>aiSettings.lastElementChild.appendChild(label));
  animatorControls.insertBefore(aiSettings,document.querySelector('#ask-animator'));
  document.querySelector('#ask-animator').classList.add('primary');
  document.querySelector('#ask-animator').textContent='Propose motion';
  dialog.querySelectorAll('[data-motion-prompt]').forEach(button=>button.onclick=()=>{document.querySelector('#animator-objective').value=button.dataset.motionPrompt;document.querySelector('#animator-objective').focus();});

  const reviewDrawer=document.createElement('details');
  reviewDrawer.className='comp-asset-review-drawer';
  reviewDrawer.innerHTML='<summary><span><small>VERSIONS & APPROVALS</small><b>Approved art feeding this shot</b></span><i id="comp-review-badge">Review assets</i></summary><div class="comp-asset-review-home"></div>';
  reviewDrawer.querySelector('.comp-asset-review-home').appendChild(assetReview);
  panel.appendChild(reviewDrawer);

  dialog.querySelectorAll('[data-comp-view]').forEach(button=>button.onclick=()=>setCompositorViewV2(button.dataset.compView));

  function setCompositorViewV2(view){
    dialog.querySelectorAll('[data-comp-view]').forEach(button=>{const active=button.dataset.compView===view;button.classList.toggle('active',active);button.setAttribute('aria-current',active?'page':'false');});
    dialog.querySelectorAll('[data-comp-panel]').forEach(section=>section.classList.toggle('active',section.dataset.compPanel===view));
  }
  window.setCompositorViewV2=setCompositorViewV2;
  dialog.querySelectorAll('[data-comp-view]').forEach(button=>button.addEventListener('click',event=>{
    if(document.documentElement.dataset.workspaceDepth!=='guided')return;
    event.stopImmediatePropagation();
    setCompositorViewV2(button.dataset.compView);
  },true));

  function syncCompositorExperienceV2(){
    if(document.documentElement.dataset.workspaceDepth!=='guided')return;
    setCompositorViewV2('layers');
    const properties=dialog.querySelector('.comp-layer-properties');
    if(properties)properties.open=false;
  }
  document.addEventListener('kizuna:workspace-depth',syncCompositorExperienceV2);

  function decorateCompositorV2(){
    const studio=typeof activeCompositorStudio==='undefined'?null:activeCompositorStudio;
    const composition=typeof activeComposition==='undefined'?null:activeComposition;
    const shotId=typeof activeCompositorShotId==='undefined'?null:activeCompositorShotId;
    const shot=studio?.shots?.find(item=>item.id===shotId);
    const shots=studio?.shots||[];
    document.querySelector('#comp-shot-count').textContent=`${shots.length} shot${shots.length===1?'':'s'}`;
    document.querySelector('#comp-scene-label').textContent=shot?.scene_title?shot.scene_title.toUpperCase():'PROGRAM MONITOR';
    document.querySelector('#comp-shot-title').textContent=shot?.title||'Select a shot';
    document.querySelector('#comp-shot-duration').textContent=shot?`${Number(shot.duration_seconds||0).toFixed(1)} sec`:'--';
    document.querySelector('#comp-version-status').textContent=composition?`Composition v${composition.version}`:(shot?'Layer stack needed':'Not built');
    document.querySelector('#comp-layer-count').textContent=`${composition?.layers?.length||0} layer${composition?.layers?.length===1?'':'s'}`;
    if(composition&&!stage.querySelector('.comp-safe-frame'))stage.insertAdjacentHTML('afterbegin','<div class="comp-safe-frame" aria-hidden="true"></div>');
    document.querySelector('#build-composition').disabled=!shot;
    document.querySelector('#render-composition').disabled=!composition;
    document.querySelector('#render-motion').disabled=!composition;
    document.querySelector('#ask-animator').disabled=!composition;
    document.querySelector('#composition-empty').innerHTML=shot?'<span class="comp-empty-icon">◇</span><b>This shot has no layer stack yet</b><small>Create one from the approved background and character art. Every layer stays editable.</small>':'<span class="comp-empty-icon">▣</span><b>Choose a shot to begin</b><small>The selected shot will appear here with its artwork, layers, camera, and motion controls.</small>';

    shotBrowser.querySelectorAll('[data-compositor-shot]').forEach((button,index)=>{
      const item=shots.find(value=>value.id===Number(button.dataset.compositorShot));
      if(!item)return;
      const built=Boolean(item.composition_id);
      button.innerHTML=`<span class="comp-shot-thumb"><i>${String(index+1).padStart(2,'0')}</i><em>${built?'LAYERS':'EMPTY'}</em></span><span class="comp-shot-copy"><b>${safe(item.title)}</b><small>${safe(item.scene_title||'Scene')} · ${Number(item.duration_seconds||0).toFixed(1)} sec</small></span><span class="comp-shot-state ${built?'ready':''}">${built?'Built':'Set up'}</span>`;
    });

    layers.querySelectorAll('[data-layer-id]').forEach(button=>{
      const layer=composition?.layers?.find(item=>item.id===Number(button.dataset.layerId));
      if(!layer)return;
      const kind=String(layer.kind||'asset').replace(/_/g,' ');
      button.innerHTML=`<span class="comp-layer-grip">⋮⋮</span><span class="comp-layer-icon">${layer.source_uri?'▧':'◇'}</span><span class="comp-layer-copy"><b>${safe(layer.name)}</b><small>${safe(kind)} · ${Math.round(Number(layer.opacity||0)*100)}% · ${safe(layer.blend_mode||'normal')}</small></span><span class="comp-layer-visible">${layer.visible?'◉':'○'}</span><em>${layer.z_index}</em>`;
      button.title=`Edit ${layer.name}`;
    });
    if(!composition){layers.innerHTML='<div class="comp-no-layers"><b>No layers yet</b><small>Create the layer stack for this shot first.</small></div>';layerForm.style.display='none';layerEmpty.style.display='block';}
    const counts={pending:(studio?.assets||[]).filter(item=>item.review_status==='pending').length,approved:(studio?.assets||[]).filter(item=>item.review_status==='approved').length};
    document.querySelector('#comp-review-badge').textContent=counts.pending?`${counts.pending} need review`:`${counts.approved} approved`;
  }

  const baseLoad=loadCompositorStudio;
  loadCompositorStudio=async function(projectId){const value=await baseLoad(projectId);decorateCompositorV2();return value;};
  const baseShots=renderCompositorShots;
  renderCompositorShots=function(){const value=baseShots();decorateCompositorV2();return value;};
  const baseSelectShot=selectCompositorShot;
  selectCompositorShot=async function(shotId){const value=await baseSelectShot(shotId);decorateCompositorV2();return value;};
  const baseEditor=renderCompositionEditor;
  renderCompositionEditor=function(){const value=baseEditor();decorateCompositorV2();return value;};
  const baseSelectLayer=selectCompositionLayer;
  selectCompositionLayer=function(layerId){const value=baseSelectLayer(layerId);setCompositorViewV2('layers');decorateCompositorV2();return value;};
  decorateCompositorV2();
  syncCompositorExperienceV2();
})();
