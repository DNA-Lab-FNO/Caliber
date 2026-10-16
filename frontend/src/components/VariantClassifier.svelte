<script lang="ts">
    import { apiUrl, getCookie } from "../lib/api";

  interface Props {
    onunauthorized?: () => void
  }

  let { onunauthorized }: Props = $props()

  let isProcessing = $state(false);
  let errorMessage = $state('');
  let successMessage = $state('');
  let selectedFile = $state<File | null>(null);
  let isDragActive = $state(false);

  // Obsluha výběru souboru přes dialog
  function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    if (target.files && target.files.length > 0) {
      selectedFile = target.files[0];
      errorMessage = '';
      successMessage = '';
    }
  }

  // Obsluha Drag & Drop
  function handleDragOver(event: DragEvent) {
    event.preventDefault();
    isDragActive = true;
  }

  function handleDragLeave() {
    isDragActive = false;
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    isDragActive = false;
    
    if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
      const file = event.dataTransfer.files[0];
      // Ověření, že jde o Excel
      if (file.name.endsWith('.xlsx')) {
        selectedFile = file;
        errorMessage = '';
        successMessage = '';
      } else {
        errorMessage = 'Neplatný formát souboru. Nahrajte prosím soubor typu .xlsx (Excel).';
      }
    }
  }

  function clearFile() {
    selectedFile = null;
    errorMessage = '';
    successMessage = '';
  }
  
  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedFile) return;

    isProcessing = true;
    errorMessage = '';
    successMessage = '';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const csrfToken = getCookie('csrftoken');
      
      const response = await fetch(apiUrl('/api/classify/'), {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': csrfToken
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          onunauthorized?.()
          return
        }
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Zpracování souboru selhalo.');
      }

      // KLÍČOVÉ: Přečteme odpověď jako binární blob (Excel soubor)
      const blob = await response.blob();
      
      // Vytvoříme dočasný odkaz pro stažení v prohlížeči
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Pojmenujeme stažený soubor (přidáme prefix ke jménu původního)
      a.download = `klasifikace_${selectedFile.name}`;
      document.body.appendChild(a);
      a.click();
      
      // Vyčištění paměti
      window.URL.revokeObjectURL(url);
      a.remove();

      successMessage = 'Soubor byl úspěšně klasifikován a stažen.';
      selectedFile = null; // Resetujeme po úspěšném stažení
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Nastala neočekávaná chyba při zpracování.';
    } finally {
      isProcessing = false;
    }
  }
</script>

<div class="batch-layout">
  <div class="card layout-panel">
    <div class="panel-head">
      <h2>Automatická anotace a klasifikace</h2>
      <p class="muted">Nahrajte váš laboratorní Excel seznam variant. Systém se pokusí automaticky anotovat a klasifikovat jednotlivé varianty za pomocí interní a ClinVar databáze. Následně vám bude k dispozici stažený soubor s výsledky.</p>
    </div>

    <form onsubmit={handleSubmit} class="upload-panel">
      <div 
        class="dropzone {isDragActive ? 'drag-active' : ''}"
        ondragover={handleDragOver}
        ondragleave={handleDragLeave}
        ondrop={handleDrop}
        role="button"
        tabindex="0"
      >
        <input 
          type="file" 
          id="batch-file-input" 
          class="file-input" 
          accept=".xlsx" 
          onchange={handleFileChange} 
        />
        
        <div class="dropzone-content">
          <span class="dropzone-title">Přetáhněte soubor sem nebo</span>
          <label for="batch-file-input" class="browse-button">
            Vybrat soubor
          </label>
          <span class="dropzone-hint">Podporován je pouze formát .xlsx</span>
        </div>
      </div>

      {#if selectedFile}
        <div class="file-meta">
          <span class="file-name">📄 {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
          <button type="button" class="clear-file" onclick={clearFile} disabled={isProcessing}>
            Zrušit
          </button>
        </div>
      {/if}

      <div class="actions">
        <button 
          type="submit" 
          class="ghost run-btn" 
          disabled={!selectedFile || isProcessing}
        >
          {isProcessing ? 'Zpracovávám a porovnávám...' : 'Spustit klasifikaci a stáhnout'}
        </button>
      </div>
    </form>

    {#if errorMessage}
      <p class="error">{errorMessage}</p>
    {/if}

    {#if successMessage}
      <p class="success">{successMessage}</p>
    {/if}
  </div>

  <div class="card documentation-panel">
    <h3>Jak připravit vstupní soubor?</h3>
    <p class="muted">Aby parsovací engine na backendu dokázal varianty správně identifikovat, ujistěte se, že váš Excel splňuje následující kritéria:</p>
    
    <ul class="doc-list">
      <li>
        <strong>Názvy sloupců:</strong> Na pořadí sloupců v tabulce nezáleží. Systém v prvním řádku hledá klíčová slova:
        <div class="chips-info">
          <code>Gen</code> / <code>Gene</code>
          <code>Varianta</code> / <code>Variant</code>
          <code>dbSNP</code>
        </div>
      </li>
      <li>
        <strong>Identifikace podle dbSNP:</strong> Pokud je přítomen sloupec <code>dbSNP</code> (např. s hodnotou <code>rs13078881</code>), vyhledávání v ClinVar databázi je nejrychlejší a nejpřesnější.
      </li>
      <li>
        <strong>Identifikace podle HGVS:</strong> Pokud dbSNP chybí, systém se pokusí variantu spárovat kombinací názvu genu a HGVS zápisu (např. <code>c.1336G>C</code> nebo <code>p.Gly446Arg</code>).
      </li>
      <li>
        <strong>Výstupní data:</strong> Váš původní formát tabulky zůstane zcela nedotčen. Na konec pravé strany tabulky systém pouze připíjí nové sloupce: <code>System_Classification</code> (kategorie patogenity), <code>ClinVar_ID</code> a <code>Database_Match_Status</code>.
      </li>
    </ul>
  </div>
</div>

<style>
  .batch-layout {
    display: grid;
    gap: 24px;
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr);
  }

  .layout-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .panel-head h2 {
    margin-bottom: 8px;
  }

  .run-btn {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    width: 100%;
    padding: 14px 20px;
    font-size: 15px;
  }

  .run-btn:hover:not(:disabled) {
    box-shadow: 0 12px 25px -18px rgba(201, 107, 60, 0.6);
  }

  /* Pravý panel nápovědy */
  .documentation-panel {
    background: rgba(255, 255, 255, 0.4);
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .doc-list {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    font-size: 14px;
    line-height: 1.5;
  }

  .doc-list li {
    color: var(--ink);
  }

  .chips-info {
    display: flex;
    gap: 6px;
    margin-top: 6px;
  }

  .chips-info code {
    font-family: 'IBM Plex Mono', monospace;
    background: rgba(20, 18, 16, 0.06);
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
  }

  @media (max-width: 960px) {
    .batch-layout {
      grid-template-columns: 1fr;
    }
  }
</style>