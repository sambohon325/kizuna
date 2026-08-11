(function () {
  const labels = {ready: 'Ready', warning: 'Attention', error: 'Needs action'};
  const icons = {ready: '✓', warning: '!', error: '×'};

  function detailRows(details) {
    const rows = [];
    if (details.revision) rows.push(['Schema', details.revision]);
    if (Number.isFinite(details.queued)) rows.push(['Queue', `${details.queued} waiting · ${details.running} running`]);
    if (Number.isFinite(details.failed)) rows.push(['History', `${details.completed} completed · ${details.failed} failed`]);
    if (Number.isFinite(details.free_bytes)) rows.push(['Capacity', `${(details.free_bytes / 1073741824).toFixed(1)} GB free`]);
    if (details.backend) rows.push(['Latest copy', `${details.backend.toUpperCase()} · ${(Number(details.size_bytes || 0) / 1048576).toFixed(1)} MB`]);
    return rows.length ? `<dl>${rows.map(([name, value]) => `<div><dt>${safe(name)}</dt><dd>${safe(value)}</dd></div>`).join('')}</dl>` : '';
  }

  function render(data) {
    if (!data) return '<section class="operational-readiness"><div class="settings-loading">Checking studio operations...</div></section>';
    const backup = data.checks.find(item => item.key === 'backups');
    const heading = data.status === 'ready' ? 'The production engine is ready' : data.status === 'error' ? 'The studio needs attention' : 'The studio is running with advisories';
    return `<section class="operational-readiness ${safe(data.status)}"><header><div><p class="eyebrow">STUDIO OPERATIONS</p><h3>${heading}</h3><p>Live, production-safe checks for persistence, job recovery, storage capacity, and backups.</p></div><span><i></i>${safe(labels[data.status] || data.status)}</span></header><div class="operations-check-grid">${data.checks.map(check => `<article class="${safe(check.state)}"><header><i>${icons[check.state] || '?'}</i><span><b>${safe(check.label)}</b><small>${safe(labels[check.state] || check.state)}</small></span></header><p>${safe(check.summary)}</p>${detailRows(check.details || {})}</article>`).join('')}</div><div class="operations-actions"><div><b>Last checked</b><span>${new Date(data.checked_at).toLocaleString()} · ${safe(data.environment)}</span></div><button type="button" id="refresh-operations">Run checks again</button>${backup?.details?.deep_verification_available ? '<button type="button" class="primary" id="verify-latest-backup">Verify latest backup</button>' : ''}</div><div id="operations-result" aria-live="polite"></div><details class="operations-explanation"><summary>What these checks prove</summary><p>Readiness confirms that Kizuna can query its database, wake or poll workers, write to production disks, recover durable jobs, and locate the newest backup. Backup verification additionally reads the full archive, recalculates its checksum, tests every ZIP entry, and validates the Kizuna manifest and production identity. It never overwrites a production.</p></details></section>`;
  }

  function wire() {
    const section = document.querySelector('.operational-readiness');
    const tabs = document.querySelector('.settings-tabs');
    if (section && tabs && !tabs.querySelector('[data-settings-view="operations"]')) {
      const pane = document.createElement('div');
      pane.className = 'settings-pane';
      pane.dataset.settingsPane = 'operations';
      pane.hidden = true;
      tabs.parentNode.appendChild(pane);
      pane.appendChild(section);
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.settingsView = 'operations';
      button.textContent = 'Operations';
      tabs.appendChild(button);
      button.onclick = () => {
        document.querySelectorAll('.settings-pane').forEach(item => item.hidden = item !== pane);
        tabs.querySelectorAll('button').forEach(item => item.classList.toggle('active', item === button));
      };
      tabs.querySelectorAll('button:not([data-settings-view="operations"])').forEach(item => item.addEventListener('click', () => { pane.hidden = true; }));
    }
    document.querySelector('#refresh-operations')?.addEventListener('click', () => window.reloadOperationalSettings?.());
    document.querySelector('#verify-latest-backup')?.addEventListener('click', async event => {
      const button = event.currentTarget, result = document.querySelector('#operations-result');
      button.disabled = true;
      result.innerHTML = '<div class="operations-running">Reading and validating the complete backup archive...</div>';
      try {
        const verification = await api('/api/settings/operations/verify-latest-backup', {method: 'POST'});
        result.innerHTML = `<div class="operations-verified"><b>Backup verification passed</b><span>${safe(verification.message)}</span><small>${safe(verification.filename)} · ${verification.entries} archive entries · ${new Date(verification.verified_at).toLocaleString()}</small></div>`;
      } catch (error) {
        result.innerHTML = `<div class="job-error">${safe(error.message)}</div>`;
      } finally {
        button.disabled = false;
      }
    });
  }

  window.renderOperationalSettings = render;
  window.wireOperationalSettings = wire;
})();
