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
    if (Number.isFinite(details.instances)) rows.push(['Instances', String(details.instances)]);
    if (Number.isFinite(details.last_seen_seconds)) rows.push(['Heartbeat', `${details.last_seen_seconds}s ago`]);
    if (Number.isFinite(details.records)) rows.push(['Reference corpus', `${details.records} records`]);
    if (Number.isFinite(details.expanded_bytes)) rows.push(['Rehearsed data', `${(details.expanded_bytes / 1048576).toFixed(1)} MB`]);
    if (Number.isFinite(details.recovered_assets)) rows.push(['Recovered media', String(details.recovered_assets)]);
    if (Number.isFinite(details.duration_seconds)) rows.push(['Drill time', `${details.duration_seconds.toFixed(1)}s`]);
    if (Array.isArray(details.channels) && details.channels.length) rows.push(['Channels', details.channels.map(item => `${item.key}${item.ready ? '' : ' · setup incomplete'}`).join(' · ')]);
    if (Array.isArray(details.history) && details.history.length) rows.push(['Last delivery', `${details.history[0].status} · ${details.history[0].channel}`]);
    return rows.length ? `<dl>${rows.map(([name, value]) => `<div><dt>${safe(name)}</dt><dd>${safe(value)}</dd></div>`).join('')}</dl>` : '';
  }

  function render(data) {
    if (!data) return '<section class="operational-readiness"><div class="settings-loading">Checking studio operations...</div></section>';
    const backup = data.checks.find(item => item.key === 'backups');
    const drill = data.checks.find(item => item.key === 'restore-drill');
    const externalAlerts = data.checks.find(item => item.key === 'external-alerts');
    const heading = data.status === 'ready' ? 'The production engine is ready' : data.status === 'error' ? 'The studio needs attention' : 'The studio is running with advisories';
    const alerts = data.alerts || [];
    return `<section class="operational-readiness ${safe(data.status)}"><header><div><p class="eyebrow">STUDIO OPERATIONS</p><h3>${heading}</h3><p>Live, production-safe checks for persistence, service heartbeats, job recovery, storage capacity, backups, and outside notifications.</p></div><span><i></i>${safe(labels[data.status] || data.status)}</span></header>${alerts.length ? `<section class="operations-alerts"><header><div><b>${alerts.length} operating notice${alerts.length===1?'':'s'}</b><span>Errors need action; advisories explain the current tradeoff.</span></div></header>${alerts.map(alert => `<article class="${safe(alert.severity)}"><div><b>${safe(alert.title)}</b><span>${safe(alert.message)}</span></div><p>${safe(alert.action)}</p></article>`).join('')}</section>` : ''}<div class="operations-check-grid">${data.checks.map(check => `<article class="${safe(check.state)}"><header><i>${icons[check.state] || '?'}</i><span><b>${safe(check.label)}</b><small>${safe(labels[check.state] || check.state)}</small></span></header><p>${safe(check.summary)}</p>${detailRows(check.details || {})}</article>`).join('')}</div><div class="operations-actions"><div><b>Last checked</b><span>${new Date(data.checked_at).toLocaleString()} · ${safe(data.environment)}</span></div><button type="button" id="refresh-operations">Run checks again</button>${externalAlerts?.details?.configured ? '<button type="button" id="test-operations-alert">Send test alert</button>' : ''}${backup?.details?.deep_verification_available ? '<button type="button" id="verify-latest-backup">Verify latest backup</button>' : ''}${backup?.details?.restore_drill_available && !['queued','running'].includes(drill?.details?.status) ? '<button type="button" class="primary" id="run-restore-drill">Run recovery drill</button>' : ''}</div><div id="operations-result" aria-live="polite"></div><details class="operations-explanation"><summary>What these checks prove</summary><p>Readiness confirms that Kizuna can query its database, observe its core services, wake or poll workers, write to production disks, recover durable jobs, reach its compliance scanner, locate the newest backup, and report external delivery history. Alerts are deduplicated during the configured cooldown. A recovery drill reads every archived byte and rebuilds a temporary recovery catalog without overwriting active work.</p></details></section>`;
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
    document.querySelector('#test-operations-alert')?.addEventListener('click', async event => {
      const button = event.currentTarget, result = document.querySelector('#operations-result');
      button.disabled = true;
      result.innerHTML = '<div class="operations-running">Sending a test alert to every configured channel...</div>';
      try {
        const delivery = await api('/api/settings/operations/test-alert', {method: 'POST'});
        result.innerHTML = `<div class="operations-verified"><b>Test alert delivered</b><span>${delivery.delivered} channel${delivery.delivered === 1 ? '' : 's'} confirmed delivery.</span></div>`;
        await window.reloadOperationalSettings?.();
      } catch (error) {
        result.innerHTML = `<div class="job-error">${safe(error.message)}</div>`;
        button.disabled = false;
      }
    });
    document.querySelector('#run-restore-drill')?.addEventListener('click', async event => {
      const button = event.currentTarget, result = document.querySelector('#operations-result');
      button.disabled = true;
      result.innerHTML = '<div class="operations-running">Starting a non-destructive recovery rehearsal...</div>';
      try {
        const job = await api('/api/settings/operations/run-restore-drill', {method: 'POST'});
        result.innerHTML = `<div class="operations-verified"><b>Recovery drill ${safe(job.status)}</b><span>Kizuna is reading the backup and rebuilding it in temporary storage.</span></div>`;
        await window.reloadOperationalSettings?.();
      } catch (error) {
        result.innerHTML = `<div class="job-error">${safe(error.message)}</div>`;
        button.disabled = false;
      }
    });
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
