<script lang="ts">
  interface Props {
    currentView: 'registry' | 'batch'
    onviewchange: (view: 'registry' | 'batch') => void
    userLabel: string
    onlogout: () => void
  }

  let { currentView, onviewchange, userLabel, onlogout }: Props = $props()
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
      </button>
      <button
        type="button"
        class="ghost nav-btn {currentView === 'batch' ? 'active' : ''}"
        onclick={() => onviewchange('batch')}
      >
        Klasifikace
      </button>
    </nav>

    <div class="topbar-actions">
      <div class="user-chip">
        <span class="user-chip__label">Přihlášen</span>
        <span class="user-chip__value">{userLabel}</span>
      </div>
      <button type="button" class="ghost logout-btn" onclick={onlogout}>
        Odhlásit
      </button>
    </div>
  </div>
</header>
