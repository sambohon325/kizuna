let writerV2Stage='concept';
let writerV2SceneId=null;

function setupWriterRoomV2(){
  const form=document.querySelector('#writer-form');
  if(!form||form.querySelector('.writer-v2'))return;
  form.innerHTML=`<div class="writer-v2">
    <header class="writer-v2-header">
      <div class="writer-v2-heading"><p class="eyebrow">STORY DEVELOPMENT</p><h2>Writer's Room</h2><p>Shape the idea, draft the pages, and prepare the story for production.</p></div>
      <label class="writer-v2-project"><span>Production</span><select id="writer-project" required></select></label>
      <button type="button" class="close" id="writer-close">&larr; Productions</button>
    </header>
    <nav class="writer-v2-stages" aria-label="Writing stages">
      <button type="button" data-writer-stage="concept"><span>01</span><b>Concept</b></button>
      <button type="button" data-writer-stage="structure"><span>02</span><b>Structure</b></button>
      <button type="button" data-writer-stage="scenes"><span>03</span><b>Scenes</b></button>
      <button type="button" data-writer-stage="screenplay"><span>04</span><b>Screenplay</b></button>
      <button type="button" data-writer-stage="revision"><span>05</span><b>Revision</b></button>
    </nav>
    <div class="writer-v2-workspace">
      <aside class="writer-v2-navigator"><h4>Story navigator</h4><p>Your production stays connected from premise to final scene.</p><div id="writer-v2-scene-list" class="writer-v2-scene-list"></div><div id="writer-v2-guide" class="writer-v2-help-card"></div></aside>
      <main class="writer-v2-canvas">
        <section class="writer-v2-panel" data-writer-panel="concept">
          <div class="writer-v2-section-title"><p class="eyebrow">START WITH THE HEART</p><h3>What is this story really about?</h3><p>Write the dramatic promise in plain language. Kizuna will use it as the north star for every later creative decision.</p></div>
          <div class="writer-v2-fields"><label class="wide">Central premise<textarea name="premise" rows="6" placeholder="Who must act, what do they want, what stands in their way, and what happens if they fail?"></textarea></label><label>Format<select name="format"><option>short film</option><option>trailer</option><option>feature film</option><option>episode</option><option>limited series</option></select></label><label>Target minutes<input name="target_duration_minutes" type="number" min="1" max="240" value="5"></label><label>Genre<input name="genre" value="science fantasy"></label><label>Audience<input name="audience" value="general"></label><label class="wide">Themes<input name="themes" placeholder="identity, found family, memory"></label></div>
          <div class="writer-v2-primary-row"><button class="primary" type="submit">Develop story foundation</button><button type="button" data-next-writer-stage="structure">Continue to structure</button></div>
          <div class="writer-v2-scope"><section id="writer-scope-card" class="writer-scope-card"><div class="settings-loading">Loading release plan...</div></section></div>
        </section>
        <section class="writer-v2-panel" data-writer-panel="structure"><div class="writer-v2-section-title"><p class="eyebrow">SHAPE THE JOURNEY</p><h3>Structure the emotional turns</h3><p>Review the synopsis and beat map. Each beat should cause the next—not simply happen after it.</p></div><div id="story-result" class="story-result"></div><div id="writer-structure-empty" class="writer-empty"><h4>No structure yet</h4><p>Develop the concept first, or ask the AI Writer for a complete proposal you can approve.</p><button type="button" data-next-writer-stage="concept">Return to concept</button></div></section>
        <section class="writer-v2-panel" data-writer-panel="scenes"><div class="writer-v2-section-title"><p class="eyebrow">FROM BEATS TO DRAMA</p><h3>Build the scene plan</h3><p>Turn structural beats into playable scenes. These cards become the bridge between writing and shot planning.</p></div><div id="writer-scene-board" class="writer-scene-board"></div></section>
        <section class="writer-v2-panel" data-writer-panel="screenplay"><div class="writer-v2-section-title"><p class="eyebrow">WRITE THE PAGES</p><h3>Draft the selected scene</h3><p>Keep action visual, dialogue playable, and every scene pointed toward a meaningful change.</p></div><div id="writer-screenplay-editor"></div></section>
        <section class="writer-v2-panel" data-writer-panel="revision"><div class="writer-v2-section-title"><p class="eyebrow">MAKE IT PRODUCTION READY</p><h3>Revision desk</h3><p>See what is strong, what is missing, and what must be cleared before the story moves into boards.</p></div><div id="writer-revision-grid" class="revision-grid"></div><div class="writer-v2-primary-row"><button type="button" id="writer-handoff" class="primary">Open Storyboard & Shot Planner</button><button type="button" id="writer-run-compliance">Run story compliance scan</button></div><div id="writer-revision-result"></div></section>
      </main>
      <aside class="writer-v2-copilot"><section class="writer-agent-panel"><div><p class="eyebrow">AI WRITER</p><h3>Your writing partner</h3><p>Give the Writer a goal. It proposes a complete story pass and waits for your approval.</p></div><div class="writer-agent-controls"><button id="ask-writer" type="button">Ask Writer</button><details class="advanced-settings writer-agent-settings"><summary>Writer settings</summary><div><label>Engine<select id="writer-provider"><option value="simulation">Local story planner</option><option value="openai">OpenAI Writer</option></select></label><label>Assignment<textarea id="writer-objective" rows="5">Develop a production-ready story foundation with strong visual causality and an emotionally decisive climax.</textarea></label></div></details></div><div id="writer-ai-result"></div></section></aside>
    </div>
  </div>`;
  form.querySelector('#writer-close').onclick=closeWorkspace;
  form.querySelector('#ask-writer').onclick=askWriter;
  form.querySelectorAll('[data-writer-stage]').forEach(button=>button.onclick=()=>setWriterV2Stage(button.dataset.writerStage));
  form.querySelectorAll('[data-next-writer-stage]').forEach(button=>button.onclick=()=>setWriterV2Stage(button.dataset.nextWriterStage));
  form.querySelector('#writer-project').onchange=()=>{const id=Number(form.querySelector('#writer-project').value);fillStory(id);loadWriterScope(id);};
  form.querySelector('#writer-handoff').onclick=()=>openShotPlanner(Number(form.querySelector('#writer-project').value));
  form.querySelector('#writer-run-compliance').onclick=runWriterCompliance;
  setupWorkspacePopouts();
  const popout=form.querySelector('.workspace-popout');if(popout)form.querySelector('.writer-v2-header').insertBefore(popout,form.querySelector('#writer-close'));
  setWriterV2Stage('concept');
}

function currentWriterV2Project(){const id=Number(document.querySelector('#writer-project')?.value);return projects.find(project=>project.id===id)||null;}

function setWriterV2Stage(stage){
  writerV2Stage=stage;
  document.querySelectorAll('[data-writer-stage]').forEach(button=>button.classList.toggle('active',button.dataset.writerStage===stage));
  document.querySelectorAll('[data-writer-panel]').forEach(panel=>panel.classList.toggle('active',panel.dataset.writerPanel===stage));
  refreshWriterRoomV2();
}

function writerStageCompletion(project){const brief=project?.story_brief,scenes=project?.scenes||[];return{concept:Boolean(brief?.premise),structure:Boolean(brief?.synopsis&&brief?.beats?.length),scenes:Boolean(scenes.length),screenplay:Boolean(scenes.length&&scenes.every(scene=>scene.script?.trim())),revision:Boolean(scenes.length&&scenes.every(scene=>scene.draft_status==='locked'))};}

function refreshWriterRoomV2(){
  const project=currentWriterV2Project(),brief=project?.story_brief,scenes=[...(project?.scenes||[])].sort((a,b)=>a.position-b.position),complete=writerStageCompletion(project);
  document.querySelectorAll('[data-writer-stage]').forEach(button=>button.classList.toggle('complete',complete[button.dataset.writerStage]));
  const list=document.querySelector('#writer-v2-scene-list');
  if(list)list.innerHTML=scenes.length?scenes.map(scene=>`<button type="button" class="${scene.id===writerV2SceneId?'active':''}" data-writer-scene="${scene.id}"><i>${String(scene.position).padStart(2,'0')}</i><span><b>${safe(scene.title)}</b><small>${safe(scene.draft_status||'outline')}</small></span></button>`).join(''):'<div class="writer-empty" style="padding:18px 12px"><p>No scenes yet.</p></div>';
  list?.querySelectorAll('[data-writer-scene]').forEach(button=>button.onclick=()=>{writerV2SceneId=Number(button.dataset.writerScene);setWriterV2Stage('screenplay');});
  const guidance={concept:['Find the dramatic promise','Name the central conflict','Choose audience and scope'],structure:['Test cause and effect','Track the emotional turn','Make the ending answer the premise'],scenes:['Enter late, leave early','Give each scene a change','Keep locations production-aware'],screenplay:['Write what can be seen or heard','Give each voice a distinct rhythm','Use notes for direction, not action'],revision:['Read for continuity','Resolve compliance findings','Lock only production-ready scenes']}[writerV2Stage];
  const guide=document.querySelector('#writer-v2-guide');if(guide)guide.innerHTML=`<b>${writerV2Stage[0].toUpperCase()+writerV2Stage.slice(1)} focus</b><p>${guidance.join(' · ')}</p>`;
  const empty=document.querySelector('#writer-structure-empty');if(empty)empty.hidden=Boolean(brief?.synopsis);
  renderWriterSceneBoard(project,scenes,brief);
  renderWriterScreenplay(project,scenes);
  renderWriterRevision(project,scenes,brief);
}

function renderWriterSceneBoard(project,scenes,brief){
  const host=document.querySelector('#writer-scene-board');if(!host)return;
  if(!brief?.beats?.length){host.innerHTML='<div class="writer-empty"><h4>Structure comes first</h4><p>Develop and approve the story beats before building the scene plan.</p><button type="button" data-go-structure>Open structure</button></div>';host.querySelector('button').onclick=()=>setWriterV2Stage('structure');return;}
  if(!scenes.length){host.innerHTML='<div class="writer-empty"><h4>Your beats are ready to become scenes</h4><p>Kizuna will create a scene for each approved beat and add lightweight coverage placeholders for the storyboard team.</p><button type="button" class="primary" id="writer-build-scenes">Build scene plan</button></div>';host.querySelector('button').onclick=buildWriterScenes;return;}
  host.innerHTML=scenes.map(scene=>`<article class="writer-scene-card" data-scene-card="${scene.id}"><span>SCENE ${String(scene.position).padStart(2,'0')} · ${safe(scene.draft_status||'outline')}</span><h4>${safe(scene.title)}</h4><p>${safe(scene.summary||'No scene summary yet.')}</p><footer>${scene.script?.trim()?`${scene.script.trim().split(/\s+/).length} script words`:'Screenplay not drafted'}</footer></article>`).join('');
  host.querySelectorAll('[data-scene-card]').forEach(card=>card.onclick=()=>{writerV2SceneId=Number(card.dataset.sceneCard);setWriterV2Stage('screenplay');});
}

async function buildWriterScenes(){
  const project=currentWriterV2Project(),button=document.querySelector('#writer-build-scenes');if(!project||!button)return;button.disabled=true;button.textContent='Building scene plan...';
  try{await api(`/api/projects/${project.id}/expand-story`,{method:'POST',body:JSON.stringify({shots_per_beat:2})});await loadProjects();writerV2SceneId=currentWriterV2Project()?.scenes?.[0]?.id||null;setWriterV2Stage('scenes');refreshProductionStatus(project.id,true);}catch(error){button.disabled=false;button.textContent='Build scene plan';button.insertAdjacentHTML('afterend',`<div class="job-error">${safe(error.message)}</div>`);}
}

function renderWriterScreenplay(project,scenes){
  const host=document.querySelector('#writer-screenplay-editor');if(!host)return;let scene=scenes.find(item=>item.id===writerV2SceneId)||scenes[0];if(scene&&!writerV2SceneId)writerV2SceneId=scene.id;
  if(!scene){host.innerHTML='<div class="writer-empty"><h4>No scene selected</h4><p>Build the scene plan first, then choose a scene from the navigator.</p><button type="button">Open scenes</button></div>';host.querySelector('button').onclick=()=>setWriterV2Stage('scenes');return;}
  host.innerHTML=`<div class="screenplay-sheet"><div id="writer-scene-form"><div class="screenplay-meta"><label>Scene title<input name="scene_title" value="${safe(scene.title)}" required></label><label>Draft status<select name="scene_status"><option value="outline">Outline</option><option value="draft">Draft</option><option value="review">Ready for review</option><option value="locked">Locked</option></select></label></div><label>Scene heading<input name="scene_slugline" value="${safe(scene.slugline||'')}" placeholder="INT. LISTENING ROOM - NIGHT"></label><label>Screenplay<textarea name="scene_script" spellcheck="true" placeholder="Describe only what the audience can see or hear.\n\nCHARACTER\nWrite playable dialogue here.">${safe(scene.script||'')}</textarea></label><label>Writer / director notes<textarea name="scene_notes" rows="4" placeholder="Intent, performance questions, continuity concerns...">${safe(scene.notes||'')}</textarea></label><div class="writer-v2-primary-row"><button class="primary" type="button">Save scene draft</button><span id="writer-scene-save-state"></span></div></div></div>`;
  host.querySelector('[name=scene_status]').value=scene.draft_status||'outline';host.querySelector('#writer-scene-form button').onclick=()=>saveWriterScene(scene);
}

async function saveWriterScene(scene){
  const form=document.querySelector('#writer-scene-form'),field=name=>form.querySelector(`[name="${name}"]`),state=form.querySelector('#writer-scene-save-state'),button=form.querySelector('button');button.disabled=true;state.textContent='Saving...';
  try{await api(`/api/scenes/${scene.id}`,{method:'PUT',body:JSON.stringify({title:field('scene_title').value,summary:scene.summary,position:scene.position,slugline:field('scene_slugline').value,script:field('scene_script').value,notes:field('scene_notes').value,draft_status:field('scene_status').value})});await loadProjects();refreshWriterRoomV2();refreshProductionStatus(scene.project_id,true);}catch(error){state.textContent=error.message;button.disabled=false;}
}

function renderWriterRevision(project,scenes,brief){
  const host=document.querySelector('#writer-revision-grid');if(!host)return;const scripted=scenes.filter(scene=>scene.script?.trim()),locked=scenes.filter(scene=>scene.draft_status==='locked'),checks=[['Story foundation',brief?.synopsis?'pass':'warn',brief?.synopsis?'Synopsis and structure are in place.':'Develop and approve the story foundation.'],['Scene coverage',scenes.length?'pass':'warn',scenes.length?`${scenes.length} production scenes are connected to the outline.`:'Build the scene plan.'],['Screenplay draft',scenes.length&&scripted.length===scenes.length?'pass':'warn',scenes.length?`${scripted.length} of ${scenes.length} scenes have screenplay pages.`:'No screenplay scenes exist yet.'],['Production lock',scenes.length&&locked.length===scenes.length?'pass':'warn',scenes.length?`${locked.length} of ${scenes.length} scenes are locked.`:'Scenes must be reviewed before lock.']];
  host.innerHTML=checks.map(([title,state,copy])=>`<article class="revision-check ${state}"><span>${state==='pass'?'READY':'NEEDS ATTENTION'}</span><h4>${title}</h4><p>${copy}</p></article>`).join('');
}

async function runWriterCompliance(){const project=currentWriterV2Project(),host=document.querySelector('#writer-revision-result'),button=document.querySelector('#writer-run-compliance');if(!project)return;button.disabled=true;host.innerHTML='<div class="render-progress">Scanning the story, scene summaries, and script text...</div>';try{const result=await api(`/api/projects/${project.id}/compliance/scan`,{method:'POST',body:JSON.stringify({stage:'story'})});host.innerHTML=`<div class="${result.passed?'story-map-ready':'job-error'}">${result.passed?'Story compliance scan passed.':'The scan found issues that must be resolved before handoff.'}</div>`;refreshProductionStatus(project.id,true);}catch(error){host.innerHTML=`<div class="job-error">${safe(error.message)}</div>`;}finally{button.disabled=false;}}

const writerV2BaseFill=fillStory;
fillStory=function(projectId){writerV2BaseFill(projectId);refreshWriterRoomV2();};
const writerV2BaseRender=renderStory;
renderStory=function(brief){writerV2BaseRender(brief);refreshWriterRoomV2();};

setupWriterRoomV2();
