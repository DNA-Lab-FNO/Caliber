<script lang="ts">
  import { apiUrl } from '../lib/api';

  interface Props {
    currentView: 'registry' | 'batch' | 'dashboard';
    onviewchange: (view: 'registry' | 'batch' | 'dashboard') => void;
    userLabel: string;
    isStaff?: boolean;
    isRegistryUploading?: boolean;
    isBatchProcessing?: boolean;
    onlogout: () => void;
  }

  let {
    currentView,
    onviewchange,
    userLabel,
    isStaff = false,
    isRegistryUploading = false,
    isBatchProcessing = false,
    onlogout,
  }: Props = $props();
</script>

<header class="topbar">
  <div class="topbar-main">
    <div class="brand">
      <div class="mark" aria-hidden="true">
        <span></span>
        <span></span>
        <span></span>
      </div>
      <div>
        <p class="eyebrow">Caliber</p>
        <h1>Klinický registr variant</h1>
      </div>
    </div>

    <nav class="nav-links">
      <button
        type="button"
        class="ghost nav-btn {currentView === 'registry' ? 'active' : ''}"
        onclick={() => onviewchange('registry')}
      >
        Registr Variant
        {#if isRegistryUploading}
          <span class="tab-badge-spinner" title="Probíhá nahrávání..."></span>
        {/if}
      </button>
      <button
        type="button"
        class="ghost nav-btn {currentView === 'batch' ? 'active' : ''}"
        onclick={() => onviewchange('batch')}
      >
        Klasifikace
        {#if isBatchProcessing}
          <span class="tab-badge-spinner" title="Probíhá zpracování..."></span>
        {/if}
      </button>
      <button
        type="button"
        class="ghost nav-btn {currentView === 'dashboard' ? 'active' : ''}"
        onclick={() => onviewchange('dashboard')}
      >
        Přehled databáze
      </button>
    </nav>
    <div class="spacer"></div>
    <div class="topbar-actions">
      {#if isStaff}
        <a href={apiUrl('/admin/')} class="ghost nav-btn admin-topbar-link" target="_blank" rel="noreferrer">
          Administrace ↗
        </a>
      {/if}
      <div class="user-chip">
        <span class="user-chip__label">Přihlášen</span>
        <span class="user-chip__value">{userLabel}</span>
      </div>
      <button type="button" class="ghost logout-btn" onclick={onlogout}> Odhlásit </button>
    </div>
  </div>
</header>
