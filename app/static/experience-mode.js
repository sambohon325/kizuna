(function () {
  const STORAGE_KEY = 'kizuna-workspace-depth';
  const modes = {
    guided: {
      label: 'Beginner',
      short: 'Beginner view',
      description: 'One clear next action at a time. Extra controls stay close by without crowding your work.'
    },
    studio: {
      label: 'Intermediate',
      short: 'Intermediate view',
      description: 'See the full craft workflow, supporting context, and the controls used most often.'
    },
    expert: {
      label: 'Advanced',
      short: 'Advanced view',
      description: 'Open the complete production toolset in a denser professional workspace.'
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
    if (notify && window.showToast) window.showToast(`${modes[selected].label} view enabled`);
    return selected;
  }

  function settingsMarkup() {
    const active = getMode();
    return `<section class="experience-settings"><header><div><p class="eyebrow">EXPERIENCE LEVEL</p><h3>Choose how much of the studio you see</h3><p>Beginner is the default. Move up or down at any time as you learn a craft or need deeper control.</p></div></header><div class="experience-options" role="group" aria-label="Experience level">${Object.entries(modes).map(([key, item]) => `<button type="button" data-workspace-depth="${key}" class="${active === key ? 'active' : ''}" aria-pressed="${active === key}"><span>${item.label}${key === 'guided' ? '<em>Recommended</em>' : ''}</span><small>${item.description}</small></button>`).join('')}</div><div class="experience-safety"><b>Only the view changes</b><span>Your production, approvals, compliance gates, and AI authority remain exactly the same.</span></div></section>`;
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
