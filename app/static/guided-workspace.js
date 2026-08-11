(function () {
  const articleByWorkspace = {
    productions: 'start', crew: 'ai-help', writer: 'writing', style: 'craft-compass',
    characters: 'characters', worlds: 'worlds', shots: 'storyboard', timeline: 'edit',
    audio: 'audio', compositor: 'compositor', render: 'render', assets: 'assets',
    activity: 'activity', settings: 'connections', account: 'start'
  };
  const stepByWorkspace = new Map();
  let collapsed = false;

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

  function render() {
    const host = ensureHost();
    const workspace = currentWorkspace();
    const article = currentArticle(workspace);
    if (!article) { host.hidden = true; return; }
    host.hidden = false;
    const step = Math.max(0, Math.min(stepByWorkspace.get(workspace) || 0, article.steps.length - 1));
    stepByWorkspace.set(workspace, step);
    host.classList.toggle('collapsed', collapsed);
    host.innerHTML = `<header><div><span>GUIDED PATH</span><b>${safe(article.title)}</b></div><div class="guided-workspace-actions"><button type="button" data-guide-full>Full guide</button><button type="button" data-guide-collapse aria-expanded="${!collapsed}">${collapsed ? 'Show' : 'Hide'}</button></div></header><div class="guided-workspace-body"><p>${safe(article.summary)}</p><div class="guided-workspace-step"><span>STEP ${step + 1} OF ${article.steps.length}</span><b>${safe(article.steps[step])}</b></div><footer><div class="guided-workspace-dots" aria-label="Guide progress">${article.steps.map((_, index) => `<i class="${index === step ? 'active' : ''}"></i>`).join('')}</div><div><button type="button" data-guide-back ${step === 0 ? 'disabled' : ''}>Back</button><button type="button" data-guide-ai>Ask AI about this</button><button class="primary" type="button" data-guide-next>${step === article.steps.length - 1 ? 'Start again' : 'Next'}</button></div></footer></div>`;
    host.querySelector('[data-guide-collapse]').onclick = () => { collapsed = !collapsed; render(); };
    host.querySelector('[data-guide-full]').onclick = () => openHelpCenter(article.id);
    host.querySelector('[data-guide-back]')?.addEventListener('click', () => { stepByWorkspace.set(workspace, Math.max(0, step - 1)); render(); });
    host.querySelector('[data-guide-next]').onclick = () => { stepByWorkspace.set(workspace, step === article.steps.length - 1 ? 0 : step + 1); render(); };
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
