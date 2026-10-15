<script lang="ts">
  import { onMount } from 'svelte'

  import Topbar from './components/Topbar.svelte'
  import SearchForm from './components/SearchForm.svelte'
  import UploadPanel from './components/UploadPanel.svelte'
  import ResultsTable from './components/ResultsTable.svelte'
  import VariantClassifier from './components/VariantClassifier.svelte'

  import type { Variant } from './types/variant'
  import type { PaginationMeta } from './types/pagination'

  type SearchResponse = {
    results: Variant[]
    meta: PaginationMeta
  }

  type AuthUser = {
    email: string
    username : string
  }

  type AuthResponse = {
    authenticated: boolean
    user: AuthUser | null
    error?: string
  }

  type AuthMode = 'login' | 'register'
  type SessionState = 'loading' | 'ready'

  let variantQuery = $state('')
  let geneQuery = $state('')
  let dbsnpQuery = $state('')
  let isSearching = $state(false)
  let errorMessage = $state('')

  let results = $state<Variant[]>([])
  let meta = $state<PaginationMeta | null>(null)
  let currentPage = $state(1)
  let currentView = $state<'registry' | 'batch'>('registry')

  let sessionState = $state<SessionState>('loading')
  let currentUser = $state<AuthUser | null>(null)
  let authMode = $state<AuthMode>('login')
  let authEmail = $state('')
  let authUsername = $state('')
  let authPassword = $state('')
  let authPasswordConfirm = $state('')
  let authMessage = $state('')
  let authError = $state('')
  let authSubmitting = $state(false)

  const csrfToken = () => {
    const value = `; ${document.cookie}`
    const parts = value.split(`; csrftoken=`)
    return parts.length === 2 ? parts.pop()?.split(';').shift() || '' : ''
  }

  const clearSearch = () => {
    variantQuery = ''
    geneQuery = ''
    dbsnpQuery = ''
    errorMessage = ''
    results = []
    meta = null
    currentPage = 1
  }

  const setAuthenticatedUser = (user: AuthUser | null, message = '') => {
    currentUser = user
    authMessage = message
    authError = ''
    authPassword = ''
    authPasswordConfirm = ''
    if (!user) {
      clearSearch()
    }
  }

  const handleUnauthorized = () => {
    setAuthenticatedUser(null, 'Vaše relace vypršela. Přihlaste se znovu.')
    sessionState = 'ready'
  }

  const loadSession = async () => {
    try {
      const response = await fetch('/auth/status/', {
        headers: {
          Accept: 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('Unable to load session state.')
      }

      const payload = (await response.json()) as AuthResponse
      setAuthenticatedUser(payload.authenticated ? payload.user : null)
    } catch {
      setAuthenticatedUser(null)
    } finally {
      sessionState = 'ready'
    }
  }

  const submitAuth = async (event: SubmitEvent) => {
    event.preventDefault()
    authError = ''
    authMessage = ''
    authSubmitting = true

    try {
      const endpoint = authMode === 'login' ? '/auth/login/' : '/auth/register/'
      const payload =
        authMode === 'login'
          ? {
              email: authEmail.trim(),
              password: authPassword,
            }
          : {
              email: authEmail.trim(),
              username: authUsername.trim(),
              password: authPassword,
              password_confirm: authPasswordConfirm,
            }

      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
        },
        body: JSON.stringify(payload),
      })

      const data = (await response.json().catch(() => ({}))) as AuthResponse
      if (!response.ok) {
        throw new Error(data.error || 'Přihlášení se nezdařilo.')
      }

      setAuthenticatedUser(
        data.user,
        authMode === 'login' ? 'Přihlášení proběhlo úspěšně.' : 'Registrace proběhla úspěšně.',
      )
      currentView = 'registry'
    } catch (error) {
      authError = error instanceof Error ? error.message : 'Přihlášení se nezdařilo.'
    } finally {
      authSubmitting = false
    }
  }

  const handleLogout = async () => {
    try {
      await fetch('/auth/logout/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken(),
        },
      })
    } finally {
      setAuthenticatedUser(null, 'Byli jste odhlášeni.')
    }
  }

  const runSearch = async (page: number = 1) => {
    if (!currentUser) {
      handleUnauthorized()
      return
    }

    errorMessage = ''
    currentPage = page

    const params = new URLSearchParams({
      variant: variantQuery.trim(),
      gene: geneQuery.trim(),
      dbsnp: dbsnpQuery.trim(),
      page: String(page),
      per_page: '50',
    })

    if (![params.get('variant'), params.get('gene'), params.get('dbsnp')].some((value) => value && value.length > 0)) {
      errorMessage = 'Vyplňte alespoň jedno vyhledávací pole.'
      results = []
      meta = null
      return
    }

    isSearching = true
    try {
      const response = await fetch(`/api/search/?${params.toString()}`)
      if (response.status === 401) {
        handleUnauthorized()
        return
      }
      if (!response.ok) {
        throw new Error('Search failed. Please try again.')
      }
      const data = (await response.json()) as SearchResponse
      results = data.results
      meta = data.meta
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Search failed.'
      results = []
      meta = null
    } finally {
      isSearching = false
    }
  }

  const handleFormSubmit = () => {
    runSearch(1)
  }

  const handlePageChange = (targetPage: number) => {
    runSearch(targetPage)
  }

  onMount(loadSession)
</script>

{#if sessionState === 'loading'}
  <div class="auth-shell">
    <section class="auth-card card auth-loading">
      <p class="eyebrow">Caliber</p>
      <h1>Načítám bezpečné přihlášení</h1>
      <p>Ověřuji aktivní session a připravuji přístup k registru.</p>
    </section>
  </div>
{:else if currentUser}
  <div class="page">
    <Topbar
      {currentView}
      onviewchange={(view) => (currentView = view)}
      userLabel={`${currentUser.username} · ${currentUser.email}`}
      onlogout={handleLogout}
    />
    {#if currentView === 'registry'}
      <section class="search">
        <SearchForm
          bind:variantQuery
          bind:geneQuery
          bind:dbsnpQuery
          {isSearching}
          {errorMessage}
          onsubmit={handleFormSubmit}
          onclear={clearSearch}
        />
        <UploadPanel onunauthorized={handleUnauthorized} />
      </section>

      <section class="grid">
        <ResultsTable
          {results}
          {meta}
          onrefresh={() => runSearch(currentPage)}
          onpagechange={handlePageChange}
        />
      </section>
    {:else}
      <section class="batch-container">
        <VariantClassifier onunauthorized={handleUnauthorized} />
      </section>
    {/if}
  </div>
{:else}
  <div class="auth-shell">
  <!-- Minimal Header -->
  <header class="auth-header">
    <h1>Caliber</h1>
  </header>

  <!-- Login / Register Card -->
  <section class="card auth-card">
    <div class="auth-switcher">
      <button 
        type="button" 
        class="ghost auth-toggle {authMode === 'login' ? 'active' : ''}" 
        onclick={() => (authMode = 'login')}
      >
        Přihlášení
      </button>
      <button 
        type="button" 
        class="ghost auth-toggle {authMode === 'register' ? 'active' : ''}" 
        onclick={() => (authMode = 'register')}
      >
        Registrace
      </button>
    </div>

    <form class="auth-form" onsubmit={submitAuth}>
      <label class="field auth-field">
        <span>E-mail</span>
        <input 
          type="email" 
          bind:value={authEmail} 
          placeholder="lekar@nemocnice.cz" 
          autocomplete="email" 
          required 
        />
      </label>

      {#if authMode === 'register'}
        <label class="field auth-field">
          <span>Přezdívka</span>
          <input 
            type="text" 
            bind:value={authUsername} 
            placeholder="neurologie-tym" 
            autocomplete="off" 
            required 
          />
        </label>
      {/if}

      <label class="field auth-field">
        <span>Heslo</span>
        <input 
          type="password" 
          bind:value={authPassword} 
          autocomplete={authMode === 'login' ? 'current-password' : 'new-password'} 
          required 
        />
      </label>

      {#if authMode === 'register'}
        <label class="field auth-field">
          <span>Potvrzení hesla</span>
          <input 
            type="password" 
            bind:value={authPasswordConfirm} 
            autocomplete="new-password" 
            required 
          />
        </label>
      {/if}

      <button type="submit" class="ghost auth-submit" disabled={authSubmitting}>
        {authSubmitting ? 'Zpracovávám...' : authMode === 'login' ? 'Přihlásit se' : 'Vytvořit účet'}
      </button>
    </form>

    {#if authMessage}
      <p class="success">{authMessage}</p>
    {/if}

    {#if authError}
      <p class="error">{authError}</p>
    {/if}
  </section>
</div>
{/if}
