(function () {
  const articleByWorkspace = {
    productions: 'start', crew: 'ai-help', writer: 'writing', style: 'craft-compass',
    characters: 'characters', worlds: 'worlds', shots: 'storyboard', timeline: 'edit',
    audio: 'audio', compositor: 'compositor', render: 'render', assets: 'assets',
    activity: 'activity', settings: 'settings', account: 'start'
  };
  const stageByWorkspace = {
    writer: 'story', style: 'style', characters: 'characters', worlds: 'worlds',
    shots: 'shots', timeline: 'timeline', audio: 'audio', compositor: 'composite', render: 'render'
  };
  const workspaceByStage = {
    story: 'writer', style: 'style', characters: 'characters', worlds: 'worlds',
    shots: 'shots', timeline: 'timeline', audio: 'audio', composite: 'compositor', render: 'render'
  };
  const guideState = new Map();
  let expanded = false;
  let renderRequest = 0;

  const deepLinkViews = {
    writer: [['Open Concept', 'concept'], ['Open Concept', 'concept'], ['Open Structure', 'structure'], ['Open Scenes', 'scenes'], ['Open Revision', 'revision']],
    style: [['Open Feeling', 'vision'], ['Open Craft Compass', 'craft'], ['Open Era Blend', 'eras'], ['Open Visual Language', 'visual'], ['Open DNA Board', 'review']],
    characters: [['Open Identity', 'identity'], ['Open Story & Arc', 'story'], ['Open Visual Design', 'visual'], ['Open Model Sheet', 'model'], ['Open Assets', 'assets']],
    worlds: [['Open Story Role', 'story'], ['Open Story Role', 'story'], ['Open Place & Staging', 'place'], ['Open Visual System', 'visual'], ['Open Layers & Light', 'production']],
    shots: [['Open Shot Board', 'story'], ['Open Story & Action', 'story'], ['Open Story & Action', 'story'], ['Open Camera', 'camera'], ['Open Continuity & Frame', 'continuity']],
    timeline: [['Open Clip Inspector', 'clip'], ['Open Clip Inspector', 'clip'], ['Open Clip Inspector', 'clip'], ['Open AI Editor', 'ai'], ['Open Clip Inspector', 'clip']],
    audio: [['Open Region Inspector', 'region'], ['Open Sound Producer', 'producer'], ['Open Region Inspector', 'region'], ['Open Sound Producer', 'producer'], ['Open Voice & Rights', 'voice']],
    compositor: [['Open Layers', 'layers'], ['Open Layers', 'layers'], ['Open Camera & Grade', 'camera'], ['Open AI Animator', 'ai'], ['Open Layers', 'layers']],
    render: [['Open Overview', 'overview'], ['Add a Computer', 'setup'], ['Open Computers', 'computers'], ['Open Render Queue', 'queue'], ['Open Render Queue', 'queue']]
  };

  function currentWorkspace() {
    return typeof assistantPage === 'function' ? assistantPage() : 'productions';
  }

  function currentArticle(workspace) {
    const id = articleByWorkspace[workspace] || 'workflow';
    return typeof helpArticles === 'undefined' ? null : helpArticles.find(article => article.id === id);
  }

  function ensureHost() {
    let host = document.querySelector('#guided-workspace');
    if (host) return host;
    host = document.createElement('section');
    host.id = 'guided-workspace';
    host.className = 'guided-workspace';
    host.setAttribute('aria-live', 'polite');
    document.querySelector('#production-flow')?.after(host);
    return host;
  }

  function recommendedStep(stage, article) {
    if (!stage) return 0;
    if (stage.state === 'complete') return article.steps.length - 1;
    if (stage.state === 'blocked') return 0;
    if (stage.state === 'in_progress') return stage.summary.toLowerCase().includes('scan') ? article.steps.length - 1 : Math.min(2, article.steps.length - 1);
    return Math.min(1, article.steps.length - 1);
  }

  function statusPresentation(workspace, status) {
    if (!status) return null;
    if (workspace === 'productions') {
      const next = status.stages.find(item => item.key === status.next_key);
      return next ? {state: next.state, label: `Next milestone · ${next.label}`, summary: next.summary, target: workspaceByStage[next.key], targetLabel: `Open ${next.label}`} : {state: 'complete', label: 'Production milestones current', summary: 'Every production milestone is complete.', target: null, targetLabel: ''};
    }
    const key = stageByWorkspace[workspace];
    const stage = status.stages.find(item => item.key === key);
    if (!stage) return null;
    const labels = {ready: 'Ready to begin', in_progress: 'Work in progress', blocked: 'Waiting on earlier work', complete: 'Milestone current'};
    const next = status.stages.find(item => item.key === status.next_key);
    const canRoute = next && next.key !== key && (stage.state === 'blocked' || stage.state === 'complete');
    return {stage, state: stage.state, label: labels[stage.state] || stage.state, summary: stage.summary, target: canRoute ? workspaceByStage[next.key] : null, targetLabel: canRoute ? `${stage.state === 'blocked' ? 'Open requirement' : 'Next milestone'} · ${next.label}` : ''};
  }

  async function openGuideTarget(workspace) {
    const projectId = currentFlowProject()?.id;
    const openers = {writer: openWriterRoom, style: openStyleLab, characters: openCharacterStudio, worlds: openWorldStudio, shots: openShotPlanner, timeline: openTimeline, audio: openAudioStudio, compositor: openCompositor, render: openRenderFarm};
    if (workspace && openers[workspace]) await openers[workspace](projectId);
  }

  function deepLinkFor(workspace, step) {
    const links = deepLinkViews[workspace];
    return links?.[Math.min(step, links.length - 1)] || null;
  }

  function activateDeepLink(workspace, view) {
    const setters = {
      writer: () => setWriterV2Stage(view), style: () => setStyleV2Step(view),
      characters: () => setCharacterView(view), worlds: () => setWorldViewV2(view),
      shots: () => setShotInspectorViewV2(view), timeline: () => setTimelineInspectorV2(view),
      audio: () => setAudioStudioViewV2(view), compositor: () => window.setCompositorViewV2?.(view),
      render: () => document.querySelector(`[data-farm-view="${view}"]`)?.click()
    };
    setters[workspace]?.();
  }

  function deepLinkSelector(workspace, view) {
    return ({
      writer: `[data-writer-panel="${view}"]`, style: `[data-style-panel="${view}"]`,
      characters: `[data-character-panel="${view}"]`, worlds: `[data-world-panel="${view}"]`,
      shots: view === 'story' ? '.shot-board-v2' : `[data-shot-panel="${view}"]`,
      timeline: `[data-timeline-inspector-panel="${view}"]`, audio: `[data-audio-panel="${view}"]`,
      compositor: `[data-comp-panel="${view}"]`, render: `[data-farm-pane="${view}"]`
    })[workspace];
  }

  async function focusDeepLink(workspace, step) {
    const link = deepLinkFor(workspace, step);
    if (!link) return;
    activateDeepLink(workspace, link[1]);
    const selector = deepLinkSelector(workspace, link[1]);
    let target = null;
    for (let attempt = 0; attempt < 24 && !target; attempt += 1) {
      target = document.querySelector(selector);
      if (!target) await new Promise(resolve => requestAnimationFrame(resolve));
    }
    if (!target) return;
    target.scrollIntoView({behavior: 'smooth', block: 'center', inline: 'nearest'});
    target.classList.remove('guided-focus-pulse');
    requestAnimationFrame(() => target.classList.add('guided-focus-pulse'));
    window.setTimeout(() => target.classList.remove('guided-focus-pulse'), 1800);
  }

  async function render() {
    const requestId = ++renderRequest;
    const host = ensureHost();
    const workspace = currentWorkspace();
    const article = currentArticle(workspace);
    if (!article) { host.hidden = true; return; }
    host.hidden = false;
    const project = currentFlowProject();
    let status = project ? productionStatusCache.get(project.id) : null;
    if (project && !status) status = await refreshProductionStatus(project.id);
    if (requestId !== renderRequest) return;
    const production = statusPresentation(workspace, status);
    const stage = production?.stage || null;
    const stateKey = `${project?.id || 'none'}:${workspace}`;
    const signature = `${stage?.state || production?.state || 'none'}:${stage?.summary || production?.summary || ''}`;
    let saved = guideState.get(stateKey);
    if (!saved || saved.signature !== signature) saved = {step: recommendedStep(stage, article), signature};
    const step = Math.max(0, Math.min(saved.step, article.steps.length - 1));
    const deepLink = deepLinkFor(workspace, step);
    guideState.set(stateKey, {...saved, step});
    const focusText = workspace === 'productions' && production ? production.summary : workspace === 'crew' ? 'Choose how much help you want from the crew.' : article.steps[step];
    const primaryLabel = production?.target ? production.targetLabel : workspace === 'crew' ? 'Choose crew mode' : deepLink?.[0] || 'Open guide';
    host.classList.toggle('expanded', expanded);
    host.innerHTML = `<div class="guided-focus"><div class="guided-focus-copy"><span>RIGHT NOW</span><b>${safe(focusText)}</b>${production ? `<small class="${safe(production.state)}"><i></i>${safe(production.label)}</small>` : ''}</div><div class="guided-focus-actions"><button class="primary" type="button" data-guide-primary>${safe(primaryLabel)}<span aria-hidden="true">&rarr;</span></button><button type="button" data-guide-expand aria-expanded="${expanded}">${expanded ? 'Close guidance' : 'More guidance'}</button></div></div><div class="guided-workspace-body"><header><div><span>BEGINNER PATH</span><b>${safe(article.title)}</b></div><button type="button" data-guide-full>Open full manual</button></header><p>${safe(article.summary)}</p>${production ? `<div class="guided-production-status ${safe(production.state)}"><span><i></i><b>${safe(production.label)}</b><small>${safe(production.summary)}</small></span>${production.target ? `<button type="button" data-guide-target="${safe(production.target)}">${safe(production.targetLabel)}</button>` : ''}</div>` : ''}<div class="guided-workspace-step"><span>STEP ${step + 1} OF ${article.steps.length}</span><b>${safe(article.steps[step])}</b></div><footer><div><div class="guided-workspace-dots" aria-label="Guide pages">${article.steps.map((_, index) => `<i class="${index === step ? 'active' : ''}"></i>`).join('')}</div><small>This guide never marks work complete.</small></div><div><button type="button" data-guide-back ${step === 0 ? 'disabled' : ''}>Back</button><button type="button" data-guide-ai>Ask AI</button><button type="button" data-guide-next>${step === article.steps.length - 1 ? 'Start again' : 'Next tip'}</button></div></footer></div>`;
    host.querySelector('[data-guide-expand]').onclick = () => { expanded = !expanded; render(); };
    host.querySelector('[data-guide-primary]').onclick = () => production?.target ? openGuideTarget(production.target) : workspace === 'crew' ? document.querySelector('.crew-v2-modes')?.scrollIntoView({behavior: 'smooth', block: 'center'}) : deepLink ? focusDeepLink(workspace, step) : openHelpCenter(article.id);
    host.querySelector('[data-guide-full]').onclick = () => openHelpCenter(article.id);
    host.querySelector('[data-guide-target]')?.addEventListener('click', event => openGuideTarget(event.currentTarget.dataset.guideTarget));
    host.querySelector('[data-guide-deep-link]')?.addEventListener('click', () => focusDeepLink(workspace, step));
    host.querySelector('[data-guide-back]')?.addEventListener('click', () => { guideState.set(stateKey, {step: Math.max(0, step - 1), signature}); render(); });
    host.querySelector('[data-guide-next]').onclick = () => { guideState.set(stateKey, {step: step === article.steps.length - 1 ? 0 : step + 1, signature}); render(); };
    host.querySelector('[data-guide-ai]').onclick = async () => {
      await openAssistant();
      const input = document.querySelector('#assistant-input');
      input.value = `Walk me through this step in ${article.title}: ${article.steps[step]}`;
      input.focus();
    };
  }

  document.addEventListener('kizuna:workspace-opened', render);
  document.addEventListener('kizuna:workspace-depth', render);
  document.addEventListener('DOMContentLoaded', render);
  window.renderGuidedWorkspace = render;
})();
