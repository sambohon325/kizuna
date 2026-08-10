const helpDialog=document.querySelector('#help-dialog');
const helpArticles=[
  {id:'start',category:'Getting started',title:'Create your first production',summary:'Set the format, audience, screen shape, and release plan before creative work begins.',steps:['Select New production in the upper-right corner.','Give the production a working title and an original logline.','Choose whether it is a one-off, trailer, feature, or series.','Set its distribution channel, screen shape, length, and number of releases.','Create the production. Kizuna will use this scope to guide every department.'],tip:'You can change the release plan later. The Writer’s Room will show what needs to be reconsidered when scope changes.'},
  {id:'workflow',category:'Getting started',title:'Understand the production workflow',summary:'Kizuna connects every craft without pretending unfinished work is complete.',steps:['Develop the premise and structure in the Writer’s Room.','Lock an original visual direction in Style Lab.','Build character cards and reusable worlds.','Turn story beats into storyboard shots.','Shape picture and sound in Timeline and Audio.','Composite, review compliance, then create the master.'],tip:'The bar above each workspace reports saved milestones. It does not mark a stage complete just because you visited it.'},
  {id:'ai-help',category:'AI & automation',title:'Build and direct your AI Crew',summary:'Work manually, customize individual creative partners, or let the crew coordinate reviewable steps.',steps:['Open AI Crew from the left rail.','Choose Guided for proposals you approve, Autopilot for delegated execution, or Manual.','Select a department, then name the agent and choose personality traits that help its craft.','Set its standing direction, AI route, model, responsibilities, and level of independence.','Review every proposed action in Approvals & activity.'],tip:'Guided is the safest starting point. Agent profiles are saved with the production, and every action records which profile performed the work.'},
  {id:'writing',category:'Story',title:'Develop a story and story map',summary:'Move from premise to beats, then keep the linear outline and visual story map synchronized.',steps:['Open the Writer’s Room and select a production.','Write the central dramatic premise, genre, audience, and themes.','Ask the Writer for a proposal or develop the story manually.','Edit the generated synopsis and beats rather than treating them as final.','Switch to Story map to inspect flow, dependencies, and character movement.'],tip:'When the project changes from a short to a series or feature, update its release plan first so the Writer can reshape the structure.'},
  {id:'characters',category:'Design',title:'Build a production-ready character card',summary:'Connect narrative history, emotional arc, relationships, and visual continuity anchors.',steps:['Open Characters and create the narrative identity first.','Define the character’s want, need, and contradiction.','Use Story & arc for history, change, and relationships.','Use Visual model for silhouette, face, palette, wardrobe, and immutable anchors.','Approve a reference version before generating shots that use the character.'],tip:'Strong “Never change” anchors are more useful for visual consistency than long prose descriptions.'},
  {id:'storyboard',category:'Directing',title:'Turn the story into storyboard shots',summary:'Build scenes from story beats, then direct composition, action, camera, and continuity.',steps:['Finish a usable story outline in the Writer’s Room.','Open Shots and select Build from story.','Choose a scene and shot from the story tree.','Set location, cast, action, dialogue intent, and camera choices.','Save continuity notes for screen direction, eyelines, props, and emotional carryover.'],tip:'Storyboard at proxy quality first. Expensive generation should happen only after timing and coverage are approved.'},
  {id:'edit',category:'Post-production',title:'Build the timeline and audio mix',summary:'Create an animatic, shape pacing, and layer dialogue, music, ambience, and effects.',steps:['Open Timeline and build it from approved shots.','Drag clips to reorder and tune duration and transitions.','Render a proxy animatic to review pacing.','Open Audio and build tracks from the timeline.','Cut, duplicate, and place regions; then direct voices and mix levels.'],tip:'A strong animatic prevents costly full-resolution renders from being spent on shots that will be cut.'},
  {id:'render',category:'Finishing',title:'Render locally, in the cloud, or across the Hive',summary:'Use connected Windows, Mac, and Linux computers while controlling schedules and load.',steps:['Open Settings and connect computers under Kizuna Hive.','Choose which workloads stay local and which may use cloud services.','Set device schedules, CPU/GPU limits, and allowed job types.','Review the master profile and compliance status.','Start a farm export, monitor segments, and assemble the approved master.'],tip:'Kizuna stores lightweight project records and previews centrally while large source and render files can remain on user-controlled devices.'},
  {id:'compliance',category:'Safety & rights',title:'Pass originality and rights checks',summary:'Kizuna blocks unresolved story, image, music, voice, and ownership risks from advancing.',steps:['Create only original productions—not fan fiction based on known properties.','Use eras, techniques, and art-direction traits rather than copying a living artist or specific title.','Review every compliance finding and its suggested change.','Document licenses, consent, and professional identity when using work you control.','Export only after all required gates pass; the audit trail stays attached to the output.'],tip:'A clear result is risk reduction, not a legal guarantee. Creators remain responsible for the rights and final work they publish.'},
  {id:'connections',category:'Studio setup',title:'Connect AI engines and creative tools',summary:'Use Kizuna’s built-in workflow with OpenAI, Claude, Gemini, Ollama, or custom services.',steps:['Open Settings and find the connection you want.','Store provider secrets only in the server environment variable named by Kizuna.','Set the endpoint and model, then save the connection.','Assign different engines to writing, visual, audio, or assistant roles.','Keep external creative applications in the loop through import, export, and companion-device workflows.'],tip:'You are never locked to one AI provider. Each studio role can be routed separately.'}
];
let helpCategory='All',activeHelpArticle='start';

function openHelpCenter(articleId){
  if(!workspaceDialogs.includes(helpDialog))workspaceDialogs.push(helpDialog);
  workspaceNav.set(helpDialog,'help-nav');workspaceKeys.set(helpDialog,'help');
  activeHelpArticle=articleId||activeHelpArticle;openWorkspace(helpDialog);renderHelpCenter();
}

function renderHelpCenter(){
  const query=document.querySelector('#help-search').value.trim().toLowerCase(),categories=['All',...new Set(helpArticles.map(article=>article.category))];
  document.querySelector('#help-categories').innerHTML=categories.map(category=>`<button type="button" class="${category===helpCategory?'active':''}" data-help-category="${safe(category)}">${safe(category)}</button>`).join('');
  const matches=helpArticles.filter(article=>(helpCategory==='All'||article.category===helpCategory)&&(!query||`${article.title} ${article.summary} ${article.steps.join(' ')} ${article.category}`.toLowerCase().includes(query)));
  if(!matches.some(article=>article.id===activeHelpArticle))activeHelpArticle=matches[0]?.id||'';
  document.querySelector('#help-article-list').innerHTML=matches.length?matches.map(article=>`<button type="button" class="${article.id===activeHelpArticle?'active':''}" data-help-article="${article.id}"><b>${safe(article.title)}</b><small>${safe(article.summary)}</small></button>`).join(''):'<div class="help-empty">No articles match that search.</div>';
  const article=helpArticles.find(item=>item.id===activeHelpArticle),host=document.querySelector('#help-article');
  host.innerHTML=article?`<span class="article-category">${safe(article.category)}</span><h3>${safe(article.title)}</h3><p class="article-summary">${safe(article.summary)}</p><ol class="help-steps">${article.steps.map(step=>`<li>${safe(step)}</li>`).join('')}</ol><div class="help-tip"><b>Studio note</b>${safe(article.tip)}</div>`:'<div class="help-no-results"><b>Nothing found</b><p>Try a broader word such as story, character, audio, AI, or render.</p></div>';
  document.querySelectorAll('[data-help-category]').forEach(button=>button.onclick=()=>{helpCategory=button.dataset.helpCategory;renderHelpCenter();});
  document.querySelectorAll('[data-help-article]').forEach(button=>button.onclick=()=>{activeHelpArticle=button.dataset.helpArticle;renderHelpCenter();});
}

const tourSteps=[
  {selector:'.brand',title:'Welcome to Kizuna',body:'This is your connected anime studio. The tour will show you where a production begins, how each craft connects, and where to get help.'},
  {selector:'#new-project',title:'Start with the release plan',body:'Create a production and tell Kizuna what you are making—short, feature, trailer, or series—plus its platform, screen shape, and target length.'},
  {selector:'.rail',title:'Every craft has its own workspace',body:'Move through story, visual development, shots, editing, sound, finishing, and render. You stay in control of any craft you want to direct.'},
  {selector:'#production-flow',title:'Follow real production progress',body:'This status bar reads saved work. Visiting a page never marks it complete, and blocked stages explain what is still needed.'},
  {selector:'#assistant-launch',title:'Your copilot understands the current page',body:'Open the AI assistant anywhere to co-write, co-direct, check continuity, explain a tool, or suggest the next useful step.'},
  {selector:'#help-nav',title:'Help is always here',body:'Search the user manual by task, revisit any workflow, or restart this tour whenever you need a refresher.'}
];
let tourIndex=0;

function tourMarkup(){
  if(document.querySelector('#tour-layer'))return;document.body.insertAdjacentHTML('beforeend','<section id="tour-layer" class="tour-layer" hidden aria-label="Kizuna studio tour"><div class="tour-shade"></div><div class="tour-focus"></div><article class="tour-card" role="dialog" aria-modal="true" aria-labelledby="tour-title"><header><span>QUICK STUDIO TOUR</span><button id="tour-skip" type="button">Skip tour</button></header><h2 id="tour-title"></h2><p id="tour-body"></p><footer class="tour-actions"><span id="tour-dots"></span><div class="tour-buttons"><button id="tour-back" class="tour-back" type="button">Back</button><button id="tour-next" class="tour-next" type="button">Next</button></div></footer></article></section>');
  document.querySelector('#tour-skip').onclick=()=>finishTour(true);document.querySelector('#tour-back').onclick=()=>showTourStep(tourIndex-1);document.querySelector('#tour-next').onclick=()=>tourIndex===tourSteps.length-1?finishTour(true):showTourStep(tourIndex+1);window.addEventListener('resize',()=>{if(!document.querySelector('#tour-layer').hidden)positionTour();});
}

function startTour(){
  closeAssistant();if(helpDialog.hasAttribute('open'))showDashboard();tourMarkup();document.querySelector('#tour-layer').hidden=false;showTourStep(0);
}

function showTourStep(index){tourIndex=Math.max(0,Math.min(index,tourSteps.length-1));const step=tourSteps[tourIndex];document.querySelector('#tour-title').textContent=step.title;document.querySelector('#tour-body').textContent=step.body;document.querySelector('#tour-dots').innerHTML=tourSteps.map((_,i)=>`<i class="tour-dot ${i===tourIndex?'active':''}"></i>`).join('');document.querySelector('#tour-back').hidden=tourIndex===0;document.querySelector('#tour-next').textContent=tourIndex===tourSteps.length-1?'Finish':'Next';positionTour();}

function positionTour(){
  const step=tourSteps[tourIndex],target=document.querySelector(step.selector),focus=document.querySelector('.tour-focus'),card=document.querySelector('.tour-card');if(!target)return;
  const rect=target.getBoundingClientRect(),pad=8;focus.style.left=`${Math.max(6,rect.left-pad)}px`;focus.style.top=`${Math.max(6,rect.top-pad)}px`;focus.style.width=`${Math.min(innerWidth-12,rect.width+pad*2)}px`;focus.style.height=`${Math.min(innerHeight-12,rect.height+pad*2)}px`;
  const cardWidth=Math.min(370,innerWidth-28),cardHeight=card.offsetHeight||260;let left=Math.min(Math.max(14,rect.left),innerWidth-cardWidth-14),top=rect.bottom+22;if(top+cardHeight>innerHeight-14)top=Math.max(14,rect.top-cardHeight-22);if(rect.width>innerWidth*.65){left=innerWidth-cardWidth-28;top=Math.min(innerHeight-cardHeight-24,Math.max(84,rect.top+28));}card.style.left=`${left}px`;card.style.top=`${top}px`;
}

function finishTour(remember){document.querySelector('#tour-layer').hidden=true;if(remember)localStorage.setItem('kizuna-studio-tour-v1','complete');document.querySelector('#help-nav').focus();}

document.querySelector('#help-nav').onclick=()=>openHelpCenter();
document.querySelector('#help-close').onclick=closeWorkspace;
document.querySelector('#help-search').oninput=renderHelpCenter;
document.querySelector('#restart-tour').onclick=startTour;
tourMarkup();
if(new URLSearchParams(location.search).get('popout')!=='1'&&localStorage.getItem('kizuna-studio-tour-v1')!=='complete')window.addEventListener('load',()=>setTimeout(startTour,650),{once:true});
