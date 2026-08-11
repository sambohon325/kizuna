(function () {
  const STORAGE_KEY = 'kizuna-workspace-depth';
  const modes = {
    guided: {
      label: 'Guided',
      short: 'Guided workspace',
      description: 'Full explanations, craft context, and clear next actions while you learn the studio.'
    },
    studio: {
      label: 'Studio',
      short: 'Studio workspace',
      description: 'Short production context with the working controls kept front and center.'
    },
    expert: {
      label: 'Expert',
      short: 'Expert workspace',
      description: 'Compact professional workspaces with maximum room for the active craft.'
    }
  };

  function getMode() {
    const saved = localStorage.getItem(STORAGE_KEY);
    return modes[saved] ? saved : 'guided';
  }

  function syncControls(mode) {
    document.querySelectorAll('[data-workspace-depth]').forEach(control => {
      if (control.tagName === 'SELECT') control.value = mode;
      else {
        const active = control.dataset.workspaceDepth === mode;
        control.classList.toggle('active', active);
        control.setAttribute('aria-pressed', String(active));
      }
    });
    document.querySelectorAll('[data-workspace-depth-label]').forEach(node => {
      node.textContent = modes[mode].short;
    });
  }

  function applyMode(mode, notify) {
    const selected = modes[mode] ? mode : 'guided';
    localStorage.setItem(STORAGE_KEY, selected);
    document.documentElement.dataset.workspaceDepth = selected;
    if (document.body) document.body.dataset.workspaceDepth = selected;
    syncControls(selected);
    document.dispatchEvent(new CustomEvent('kizuna:workspace-depth', {detail: {mode: selected}}));
    if (notify && window.showToast) window.showToast(`${modes[selected].label} workspace enabled`);
    return selected;
  }

  function settingsMarkup() {
    const active = getMode();
    return `<section class="experience-settings"><header><div><p class="eyebrow">WORKSPACE DEPTH</p><h3>Choose how much guidance you see</h3><p>This changes explanation density and spacing for you. Production data, compliance gates, approvals, and AI authority stay exactly the same.</p></div></header><div class="experience-options" role="group" aria-label="Workspace depth">${Object.entries(modes).map(([key, item]) => `<button type="button" data-workspace-depth="${key}" class="${active === key ? 'active' : ''}" aria-pressed="${active === key}"><span>${item.label}</span><small>${item.description}</small></button>`).join('')}</div><div class="experience-safety"><b>Personal display preference</b><span>Saved in this browser so collaborators can choose the view that suits them.</span></div></section>`;
  }

  function wire(root) {
    (root || document).querySelectorAll('[data-workspace-depth]').forEach(control => {
      const change = () => applyMode(control.value || control.dataset.workspaceDepth, true);
      if (control.tagName === 'SELECT') control.onchange = change;
      else control.onclick = change;
    });
    syncControls(getMode());
  }

  window.kizunaExperience = {modes, getMode, applyMode, settingsMarkup, wire};
  document.documentElement.dataset.workspaceDepth = getMode();
  document.addEventListener('DOMContentLoaded', () => {
    document.body.dataset.workspaceDepth = getMode();
    wire(document);
  });
})();
