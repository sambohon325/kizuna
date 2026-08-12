(() => {
  const panel = document.querySelector('.timeline-panel');
  if (!panel || panel.classList.contains('timeline-v2')) return;

  panel.classList.add('timeline-v2');
  const title = panel.querySelector('.timeline-title');
  title.classList.add('timeline-v2-header');
  title.querySelector('h2').textContent = 'Timeline & Animatic';
  title.querySelector('.form-intro').textContent = 'Cut the story, shape its rhythm, and review the film before committing final render resources.';

  const agent = panel.querySelector('.editor-agent-panel');
  const toolbar = panel.querySelector('.timeline-edit-toolbar');
  const summary = panel.querySelector('#timeline-summary');
  const segmented = panel.querySelector('#segmented-export-result');
  const workspace = panel.querySelector('.timeline-workspace');
  const clips = panel.querySelector('#timeline-clips');
  const legacyEditor = panel.querySelector('.clip-editor');
  const empty = panel.querySelector('#clip-empty');
  const form = panel.querySelector('#clip-form');
  const frame = panel.querySelector('#clip-frame');
  const animatic = panel.querySelector('#animatic-result');

  const shell = document.createElement('div');
  shell.className = 'timeline-v2-shell';
  const guidance = document.createElement('section');
  guidance.id = 'timeline-craft-guidance';

  const upper = document.createElement('section');
  upper.className = 'timeline-v2-upper';

  const source = document.createElement('aside');
  source.className = 'timeline-source-v2';
  source.innerHTML = '<header><div><p class="eyebrow">MEDIA</p><h3>Shots</h3></div><span id="timeline-source-count-v2">0</span></header><div class="timeline-source-list-v2" id="timeline-source-list-v2"><div class="timeline-v2-empty compact">Build the timeline to load shots.</div></div>';

  const viewer = document.createElement('main');
  viewer.className = 'timeline-viewer-v2';
  viewer.innerHTML = '<header><div><p class="eyebrow">PROGRAM</p><h3 id="timeline-viewer-title-v2">Select a clip</h3></div><span id="timeline-timecode-v2">00:00:00</span></header><div class="timeline-screen-v2"><div id="timeline-viewer-empty-v2"><b>Ready for picture</b><span>Choose a shot or build the sequence.</span></div></div><div class="timeline-transport-v2"><button type="button" id="timeline-prev-v2" aria-label="Previous clip">|&larr;</button><button type="button" id="timeline-play-v2" aria-label="Play review">&#9654;</button><button type="button" id="timeline-next-v2" aria-label="Next clip">&rarr;|</button><span id="timeline-viewer-meta-v2">No clip selected</span></div>';
  viewer.querySelector('.timeline-screen-v2').appendChild(frame);

  const inspector = document.createElement('aside');
  inspector.className = 'timeline-inspector-v2';
  inspector.innerHTML = '<nav aria-label="Editor inspector"><button type="button" class="active" data-timeline-inspector="clip">Clip timing</button><button type="button" data-timeline-inspector="ai">Ask AI Editor</button></nav><section data-timeline-inspector-panel="clip" class="timeline-inspector-panel-v2"></section><section data-timeline-inspector-panel="ai" class="timeline-inspector-panel-v2" hidden></section>';
  inspector.querySelector('[data-timeline-inspector-panel="clip"]').append(empty, form);
  inspector.querySelector('[data-timeline-inspector-panel="ai"]').appendChild(agent);
  upper.append(source, viewer, inspector);

  const sequence = document.createElement('section');
  sequence.className = 'timeline-sequence-v2';
  sequence.innerHTML = '<header><div><p class="eyebrow">SEQUENCE</p><h3>Picture edit</h3></div><span>Drag clips to change story order</span></header>';
  sequence.appendChild(toolbar);
  const ruler = document.createElement('div');
  ruler.id = 'timeline-ruler-v2';
  ruler.className = 'timeline-ruler-v2';
  const lane = document.createElement('div');
  lane.className = 'timeline-lane-v2';
  lane.innerHTML = '<span class="timeline-track-label-v2"><b>V1</b><small>Picture</small></span>';
  lane.appendChild(clips);
  sequence.append(ruler, lane, summary);

  const deliveries = document.createElement('details');
  deliveries.className = 'timeline-deliveries-v2';
  deliveries.innerHTML = '<summary><span><b>Reviews & exports</b><small>Proxy playback, masters, and render-farm progress</small></span><em>Open</em></summary><div class="timeline-deliveries-body-v2"></div>';
  deliveries.querySelector('div').append(segmented, animatic);

  shell.append(upper, sequence, deliveries);
  title.after(guidance, shell);
  workspace.remove();
  legacyEditor.remove();

  decorateEditorV2(agent);
  inspector.querySelectorAll('[data-timeline-inspector]').forEach(button => button.onclick = () => setTimelineInspectorV2(button.dataset.timelineInspector));
  document.querySelector('#timeline-prev-v2').onclick = () => moveTimelineSelectionV2(-1);
  document.querySelector('#timeline-next-v2').onclick = () => moveTimelineSelectionV2(1);
  document.querySelector('#timeline-play-v2').onclick = toggleTimelinePlaybackV2;
  document.querySelector('#timeline-zoom').addEventListener('input', event => {
    document.querySelector('.timeline-v2-shell')?.style.setProperty('--timeline-clip-width', `${event.target.value}px`);
  });

  const originalRenderTimelineV2 = renderTimeline;
  const originalSelectClipV2 = selectClip;
  const originalLoadTimelineV2 = loadTimeline;
  const originalHideClipEditorV2 = hideClipEditor;

  renderTimeline = function renderTimelineWithStudioV2() {
    originalRenderTimelineV2();
    if (activeTimeline?.clips?.length && !activeClipId) originalSelectClipV2(activeTimeline.clips[0].id, false);
    refreshTimelineStudioV2();
  };

  selectClip = function selectClipWithStudioV2(clipId, rerender = true) {
    originalSelectClipV2(clipId, rerender);
    refreshTimelineStudioV2();
  };

  loadTimeline = async function loadTimelineWithStudioV2(projectId) {
    await originalLoadTimelineV2(projectId);
    renderCraftGuidance('#timeline-craft-guidance', projectId, 'edit');
    refreshTimelineStudioV2();
  };

  hideClipEditor = function hideClipEditorWithStudioV2() {
    originalHideClipEditorV2();
    refreshTimelineStudioV2();
  };
})();

function decorateEditorV2(agent) {
  if (!agent || agent.classList.contains('editor-v2-ready')) return;
  agent.classList.add('editor-v2-ready');
  agent.querySelector('h3').textContent = 'Shape the cut with me';
  agent.querySelector('.visual-agent-head p:not(.eyebrow)').textContent = 'Ask for a reviewable edit plan. Nothing changes until you approve it.';
  const controls = agent.querySelector('.visual-agent-controls');
  const objective = agent.querySelector('#editor-objective');
  objective.rows = 4;
  objective.placeholder = 'Try: Tighten the opening without losing the loneliness.';
  const prompts = document.createElement('div');
  prompts.className = 'editor-prompts-v2';
  prompts.innerHTML = '<button type="button">Tighten the pacing</button><button type="button">Protect the emotional beats</button><button type="button">Find continuity problems</button>';
  prompts.querySelectorAll('button').forEach(button => button.onclick = () => {
    objective.value = button.textContent;
    objective.focus();
  });
  const settings = document.createElement('details');
  settings.className = 'advanced-settings editor-settings-v2';
  settings.innerHTML = '<summary>Editor settings</summary><div></div>';
  [...controls.querySelectorAll('label')].filter(label => !label.contains(objective)).forEach(label => settings.querySelector('div').appendChild(label));
  const ask = controls.querySelector('#ask-editor');
  ask.textContent = 'Send to Editor';
  controls.replaceChildren(prompts, objective.closest('label'), ask, settings);
}

function setTimelineInspectorV2(view) {
  document.querySelectorAll('[data-timeline-inspector]').forEach(button => {const active=button.dataset.timelineInspector === view;button.classList.toggle('active',active);button.setAttribute('aria-current',active?'step':'false');});
  document.querySelectorAll('[data-timeline-inspector-panel]').forEach(panel => panel.hidden = panel.dataset.timelineInspectorPanel !== view);
}

function syncTimelineExperienceV2(){if(window.kizunaExperience?.getMode()==='guided')setTimelineInspectorV2('clip');}
document.addEventListener('kizuna:workspace-depth',syncTimelineExperienceV2);

function timelineClipStartV2(clipId) {
  let elapsed = 0;
  for (const clip of activeTimeline?.clips || []) {
    if (clip.id === clipId) return elapsed;
    elapsed += Number(clip.duration_seconds || 0);
  }
  return elapsed;
}

function timelineTimecodeV2(seconds) {
  const value = Math.max(0, Number(seconds || 0));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const whole = Math.floor(value % 60);
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(whole).padStart(2, '0')}`;
}

function timelineThumbV2(clip) {
  if (clip.storyboard_uri) return `<img src="${safe(clip.storyboard_uri)}" alt="">`;
  return `<span class="timeline-source-slate-v2"><i></i><b>${clip.motion_uri ? 'MOTION' : 'FRAME'}</b></span>`;
}

function refreshTimelineStudioV2() {
  const timeline = activeTimeline;
  const source = document.querySelector('#timeline-source-list-v2');
  const count = document.querySelector('#timeline-source-count-v2');
  const ruler = document.querySelector('#timeline-ruler-v2');
  if (!source || !count || !ruler) return;

  const clips = timeline?.clips || [];
  count.textContent = String(clips.length);
  source.innerHTML = clips.length ? clips.map(clip => `<button type="button" class="timeline-source-card-v2 ${clip.id === activeClipId ? 'active' : ''}" data-source-clip-id="${clip.id}">${timelineThumbV2(clip)}<span><small>${safe(clip.scene_title)}</small><b>${safe(clip.shot_title)}</b><em>${Number(clip.duration_seconds).toFixed(1)}s</em></span></button>`).join('') : '<div class="timeline-v2-empty compact"><b>No clips yet</b><span>Build the sequence from approved shots.</span></div>';
  source.querySelectorAll('[data-source-clip-id]').forEach(button => button.onclick = () => selectClip(Number(button.dataset.sourceClipId)));

  const duration = Number(timeline?.total_duration_seconds || 0);
  const step = duration > 600 ? 120 : duration > 180 ? 60 : duration > 60 ? 30 : 10;
  const markers = [];
  for (let value = 0; value <= Math.max(duration, step); value += step) markers.push(value);
  ruler.innerHTML = markers.map(value => `<span style="left:${duration ? Math.min(100, value / duration * 100) : 0}%">${timelineTimecodeV2(value)}</span>`).join('');
  document.querySelector('.timeline-v2-shell')?.style.setProperty('--timeline-count', String(Math.max(1, clips.length)));
  updateTimelineViewerV2();
}

function updateTimelineViewerV2() {
  const clip = activeTimeline?.clips?.find(item => item.id === activeClipId);
  const title = document.querySelector('#timeline-viewer-title-v2');
  const meta = document.querySelector('#timeline-viewer-meta-v2');
  const timecode = document.querySelector('#timeline-timecode-v2');
  const empty = document.querySelector('#timeline-viewer-empty-v2');
  const frame = document.querySelector('#clip-frame');
  const clips = activeTimeline?.clips || [];
  const index = clips.findIndex(item => item.id === activeClipId);
  if (!clip) {
    title.textContent = 'Select a clip';
    meta.textContent = 'No clip selected';
    timecode.textContent = '00:00:00';
    empty.hidden = false;
  } else {
    title.textContent = clip.shot_title;
    meta.textContent = `${clip.scene_title} · ${Number(clip.duration_seconds).toFixed(1)} seconds · ${clip.transition}`;
    timecode.textContent = timelineTimecodeV2(timelineClipStartV2(clip.id));
    empty.hidden = Boolean(frame.querySelector('img'));
    if (!frame.querySelector('img')) empty.querySelector('span').textContent = clip.motion_uri ? 'Motion is ready for the review render.' : 'This clip is using its framing slate until a storyboard is approved.';
  }
  document.querySelector('#timeline-prev-v2').disabled = index <= 0;
  document.querySelector('#timeline-next-v2').disabled = index < 0 || index >= clips.length - 1;
}

function moveTimelineSelectionV2(delta) {
  const clips = activeTimeline?.clips || [];
  const index = clips.findIndex(item => item.id === activeClipId);
  const target = clips[index + delta];
  if (target) selectClip(target.id);
}

function toggleTimelinePlaybackV2() {
  const video = document.querySelector('#animatic-result video');
  const button = document.querySelector('#timeline-play-v2');
  if (!video) {
    document.querySelector('.timeline-deliveries-v2').open = true;
    document.querySelector('#animatic-result').innerHTML = '<div class="timeline-review-note-v2">Render a proxy animatic to watch the current sequence.</div>';
    return;
  }
  if (video.paused) {
    video.play();
    button.innerHTML = '&#10074;&#10074;';
  } else {
    video.pause();
    button.innerHTML = '&#9654;';
  }
}
