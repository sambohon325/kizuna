(() => {
  const panel = document.querySelector('.audio-panel');
  if (!panel || panel.classList.contains('audio-v2')) return;

  panel.classList.add('audio-v2');
  const title = panel.querySelector('.audio-title');
  title.classList.add('audio-v2-header');
  title.querySelector('h2').textContent = 'Audio & Voice Studio';
  title.querySelector('.form-intro').textContent = 'Build dialogue, music, ambience, and effects on one synchronized multitrack canvas.';

  const voice = panel.querySelector('.voice-bible');
  const voiceWrapper = voice?.closest('.voice-setup');
  const summary = panel.querySelector('#audio-summary');
  const toolbar = panel.querySelector('.audio-edit-toolbar');
  const workspace = panel.querySelector('.audio-workspace');
  const tracks = panel.querySelector('#audio-tracks');
  const editor = panel.querySelector('.cue-editor');
  const empty = panel.querySelector('#cue-empty');
  const form = panel.querySelector('#cue-form');
  const cueResult = panel.querySelector('#cue-result');

  const shell = document.createElement('div');
  shell.className = 'audio-v2-shell';
  const guidance = document.createElement('section');
  guidance.id = 'audio-craft-guidance';

  const transport = document.createElement('section');
  transport.className = 'audio-transport-v2';
  transport.innerHTML = '<div class="audio-transport-buttons-v2"><button type="button" id="audio-rewind-v2" aria-label="Return playhead to start">|&larr;</button><button type="button" id="audio-play-v2" aria-label="Play selected region">&#9654;</button><button type="button" id="audio-stop-v2" aria-label="Stop playback">&#9632;</button></div><span id="audio-timecode-v2">00:00.0</span><div class="audio-transport-tools-v2"></div>';
  transport.querySelector('.audio-transport-tools-v2').appendChild(toolbar);

  const arrangement = document.createElement('section');
  arrangement.className = 'audio-arrangement-v2';
  arrangement.innerHTML = '<header><div><p class="eyebrow">ARRANGEMENT</p><h3>Production mix</h3></div><span>Drag regions to move · pull the right edge to resize</span></header>';
  arrangement.append(summary, tracks);

  const inspector = document.createElement('section');
  inspector.className = 'audio-inspector-v2';
  inspector.innerHTML = '<nav aria-label="Audio inspector"><button type="button" class="active" data-audio-view="region">Region</button><button type="button" data-audio-view="producer">Sound Producer</button><button type="button" data-audio-view="voice">Voice & rights</button></nav><div class="audio-inspector-panel-v2" data-audio-panel="region"></div><div class="audio-inspector-panel-v2 audio-producer-v2" data-audio-panel="producer" hidden><header><p class="eyebrow">AI SOUND PRODUCER</p><h3>Create or place the performance</h3><p>Select a region, describe what should be heard, then generate a reviewable performance, timing slate, or upload authorized audio.</p></header><div id="audio-producer-guide-v2"><span>DIALOGUE · direct delivery and pronunciation</span><span>MUSIC · brief the composition and upload or connect a generator</span><span>SOUND · place effects and ambience against picture time</span></div></div><div class="audio-inspector-panel-v2 audio-voice-v2" data-audio-panel="voice" hidden><header><p class="eyebrow">VOICE DIRECTION</p><h3>Performance identity & permission</h3><p>Lock the vocal character, provider, pronunciation, consent, and disclosure before generating dialogue.</p></header></div>';
  inspector.querySelector('[data-audio-panel="region"]').append(empty, form);
  inspector.querySelector('[data-audio-panel="producer"]').appendChild(cueResult);
  inspector.querySelector('[data-audio-panel="voice"]').appendChild(voice);

  shell.append(transport, arrangement, inspector);
  title.after(guidance, shell);
  workspace.remove();
  editor.remove();
  voiceWrapper?.remove();

  inspector.querySelectorAll('[data-audio-view]').forEach(button => button.onclick = () => setAudioStudioViewV2(button.dataset.audioView));
  document.querySelector('#audio-rewind-v2').onclick = rewindAudioStudioV2;
  document.querySelector('#audio-play-v2').onclick = playAudioStudioV2;
  document.querySelector('#audio-stop-v2').onclick = stopAudioStudioV2;

  const originalRenderAudioStudioV2 = renderAudioStudio;
  const originalSelectAudioCueV2 = selectAudioCue;
  const originalNewAudioCueV2 = newAudioCue;
  const originalLoadAudioStudioV2 = loadAudioStudio;
  const originalRenderCueResultV2 = renderCueResult;

  renderAudioStudio = function renderAudioStudioWithV2(projectId) {
    originalRenderAudioStudioV2(projectId);
    refreshAudioStudioV2();
  };

  selectAudioCue = function selectAudioCueWithV2(cueId, rerender = true) {
    originalSelectAudioCueV2(cueId, rerender);
    setAudioStudioViewV2('region');
    refreshAudioStudioV2();
  };

  newAudioCue = function newAudioCueWithV2(trackId) {
    originalNewAudioCueV2(trackId);
    setAudioStudioViewV2('region');
    refreshAudioStudioV2();
  };

  loadAudioStudio = async function loadAudioStudioWithV2(projectId) {
    await originalLoadAudioStudioV2(projectId);
    renderCraftGuidance('#audio-craft-guidance', projectId, 'sound');
    refreshAudioStudioV2();
  };

  renderCueResult = function renderCueResultWithV2(cue) {
    originalRenderCueResultV2(cue);
    refreshAudioProducerV2(cue);
  };
})();

function setAudioStudioViewV2(view) {
  document.querySelectorAll('[data-audio-view]').forEach(button => button.classList.toggle('active', button.dataset.audioView === view));
  document.querySelectorAll('[data-audio-panel]').forEach(panel => panel.hidden = panel.dataset.audioPanel !== view);
}

function audioTimecodeV2(seconds) {
  const value = Math.max(0, Number(seconds || 0));
  const minutes = Math.floor(value / 60);
  const remainder = value % 60;
  return `${String(minutes).padStart(2, '0')}:${remainder.toFixed(1).padStart(4, '0')}`;
}

function refreshAudioStudioV2() {
  const studio = activeAudioStudio;
  const host = document.querySelector('#audio-tracks');
  if (!host) return;
  const duration = Math.max(Number(studio?.total_duration_seconds || 0), 10);
  const zoom = Number(document.querySelector('#audio-zoom')?.value || 900);
  const playhead = Math.min(duration, Number(document.querySelector('#audio-playhead')?.value || 0));
  document.querySelector('#audio-timecode-v2').textContent = audioTimecodeV2(playhead);

  const step = duration > 600 ? 120 : duration > 180 ? 60 : duration > 60 ? 30 : 10;
  const marks = [];
  for (let value = 0; value <= Math.max(duration, step); value += step) marks.push(value);
  host.querySelectorAll('.audio-ruler-v2').forEach(existing => existing.remove());
  const ruler = document.createElement('div');
  ruler.className = 'audio-ruler-v2';
  ruler.style.width = `${142 + zoom}px`;
  ruler.innerHTML = marks.map(value => `<span style="left:${142 + value / duration * zoom}px">${audioTimecodeV2(value)}</span>`).join('');
  host.prepend(ruler);

  (studio?.tracks || []).forEach((track, index) => {
    const group = host.querySelectorAll('.track-group')[index];
    if (!group) return;
    group.dataset.audioKind = track.kind;
    const head = group.querySelector('.track-head');
    const name = head.querySelector('b');
    name.innerHTML = `<i>${audioTrackIconV2(track.kind)}</i><span>${safe(track.name)}<small>${safe(track.kind)}</small></span>`;
    const add = head.querySelector('[data-new-cue]');
    add.textContent = '+ Add';
    add.setAttribute('aria-label', `Add region to ${track.name}`);
  });

  const selected = findAudioCue(activeAudioCueId);
  document.querySelector('#split-audio-region').disabled = !selected;
  document.querySelector('#duplicate-audio-region').disabled = !selected;
  document.querySelector('#delete-audio-region').disabled = !selected;
  document.querySelector('#audio-play-v2').disabled = !selected;
  refreshAudioProducerV2(selected?.cue);
}

function audioTrackIconV2(kind) {
  return {dialogue:'VO', music:'♪', sfx:'FX', ambience:'AM'}[kind] || 'AU';
}

function refreshAudioProducerV2(cue) {
  const guide = document.querySelector('#audio-producer-guide-v2');
  if (!guide) return;
  const found = cue ? findAudioCue(cue.id) : null;
  const labels = {
    dialogue:['Direct the actor or AI voice','Confirm voice rights and disclosure','Generate a timing slate before the final take'],
    music:['Describe emotion, tempo, structure, and edit points','Connect a music generator or upload licensed stems','Keep originality scans attached to the selected version'],
    sfx:['Describe the action, material, distance, and perspective','Generate or upload an authorized effect','Place and resize the region against the picture'],
    ambience:['Describe the room, weather, era, and emotional pressure','Build a seamless bed that supports dialogue','Use subtle layers instead of one loud loop']
  };
  const items = labels[found?.track?.kind] || ['Select a region on the multitrack canvas','Describe what the audience should hear','Review and approve generated or uploaded audio'];
  guide.innerHTML = `<b>${found ? safe(found.track.name) : 'Choose a region'}</b>${items.map(item => `<span>${safe(item)}</span>`).join('')}`;
  const ask = document.querySelector('#ask-sound-producer');
  if (ask) ask.textContent = found?.track?.kind === 'dialogue' ? 'Ask Voice Producer' : 'Ask Sound Producer';
}

function rewindAudioStudioV2() {
  const playhead = document.querySelector('#audio-playhead');
  playhead.value = 0;
  if (activeAudioStudio) renderAudioStudio(activeAudioStudio.project_id);
}

function playAudioStudioV2() {
  const selected = findAudioCue(activeAudioCueId);
  if (!selected) return;
  setAudioStudioViewV2('producer');
  const audio = document.querySelector('#cue-result audio');
  if (audio) {
    audio.play();
    document.querySelector('#audio-play-v2').innerHTML = '&#10074;&#10074;';
  } else {
    const guide = document.querySelector('#audio-producer-guide-v2');
    guide.insertAdjacentHTML('beforeend', '<em>Generate a timing slate, ask the Sound Producer, or upload a performance to hear this region.</em>');
  }
}

function stopAudioStudioV2() {
  const audio = document.querySelector('#cue-result audio');
  if (audio) {
    audio.pause();
    audio.currentTime = 0;
  }
  document.querySelector('#audio-play-v2').innerHTML = '&#9654;';
}
