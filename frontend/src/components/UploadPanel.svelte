<script lang="ts">
  interface Props {
    onunauthorized?: () => void
  }

  let { onunauthorized }: Props = $props()

  let uploadFiles = $state<File[]>([])
  let uploadMessage = $state('')
  let uploadError = $state('')
  let isUploading = $state(false)
  let isDragActive = $state(false)
  let fileInputRef = $state<HTMLInputElement | null>(null)

  const getCookie = (name: string) => {
    const cookie = document.cookie
      .split(';')
      .map((value) => value.trim())
      .find((value) => value.startsWith(`${name}=`))
    return cookie ? decodeURIComponent(cookie.split('=')[1]) : ''
  }

  const handleUpload = async () => {
    uploadMessage = ''
    uploadError = ''
    if (uploadFiles.length === 0) {
      uploadError = 'Vyberte soubor pro nahrání.'
      return
    }

    const formData = new FormData()
    uploadFiles.forEach((file) => formData.append('file', file))

    isUploading = true
    try {
      const response = await fetch('/api/upload/', {
        method: 'POST',
        headers: {
          'X-CSRFToken': getCookie('csrftoken'),
        },
        body: formData,
      })
      if (!response.ok) {
        if (response.status === 401) {
          onunauthorized?.()
          return
        }
        let errorMsg = `Upload failed (HTTP ${response.status})`
        try {
          const contentType = response.headers.get('content-type')
          if (contentType && contentType.includes('application/json')) {
            const payload = (await response.json()) as { error?: string }
            errorMsg = payload.error || errorMsg
          } else {
            if (response.status === 413) {
              errorMsg = 'Soubor je příliš velký pro nahrání (HTTP 413 Request Entity Too Large).'
            } else if (response.status === 403) {
              errorMsg = 'Přístup odepřen (HTTP 403 CSRF verification failed). Obnovte stránku a zkuste to znovu.'
            } else if (response.status === 502 || response.status === 504) {
              errorMsg = 'Časový limit serveru vypršel (HTTP 502/504). Zpracování trvalo příliš dlouho.'
            } else {
              errorMsg = `Chyba serveru (HTTP ${response.status}). Zkontrolujte logy aplikace.`
            }
          }
        } catch {
          // ignore parsing error and keep errorMsg
        }
        throw new Error(errorMsg)
      }
      const payload = (await response.json()) as { filename?: string; filenames?: string[] }
      if (payload.filenames && payload.filenames.length > 0) {
        uploadMessage = `Nahráno souborů: ${payload.filenames.length}.`
      } else if (payload.filename) {
        uploadMessage = `Soubor ${payload.filename} byl nahrán.`
      } else {
        uploadMessage = 'Soubor(y) byly nahrány.'
      }
      uploadFiles = []
      if (fileInputRef) {
        fileInputRef.value = ''
      }
    } catch (error) {
      uploadError = error instanceof Error ? error.message : 'Upload failed.'
    } finally {
      isUploading = false
    }
  }

  const appendFiles = (files: File[]) => {
    if (files.length === 0) {
      return uploadFiles
    }
    uploadMessage = ''
    uploadError = ''
    const seen = new Set(uploadFiles.map((file) => `${file.name}-${file.size}-${file.lastModified}`))
    const merged = [...uploadFiles]
    files.forEach((file) => {
      const key = `${file.name}-${file.size}-${file.lastModified}`
      if (!seen.has(key)) {
        seen.add(key)
        merged.push(file)
      }
    })
    uploadFiles = merged
    return merged
  }

  const clearSelectedFile = () => {
    uploadMessage = ''
    uploadError = ''
    uploadFiles = []
    if (fileInputRef) {
      fileInputRef.value = ''
    }
  }

  const removeFile = (index: number) => {
    uploadFiles = uploadFiles.filter((_, itemIndex) => itemIndex !== index)
    if (uploadFiles.length === 0) {
      clearSelectedFile()
    }
  }

  const handleFileChange = (event: Event) => {
    const target = event.currentTarget as HTMLInputElement
    appendFiles(target.files ? Array.from(target.files) : [])
  }

  const handleDrop = (event: DragEvent) => {
    event.preventDefault()
    isDragActive = false
    const droppedFiles = event.dataTransfer?.files
      ? Array.from(event.dataTransfer.files)
      : []
    const mergedFiles = appendFiles(droppedFiles)
    if (fileInputRef) {
      const dataTransfer = new DataTransfer()
      mergedFiles.forEach((file) => dataTransfer.items.add(file))
      fileInputRef.files = dataTransfer.files
    }
  }

  const handleDragOver = (event: DragEvent) => {
    event.preventDefault()
    isDragActive = true
  }

  const handleDragLeave = () => {
    isDragActive = false
  }

  const openFileDialog = () => {
    fileInputRef?.click()
  }

  const handleDropzoneKeydown = (event: KeyboardEvent) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      openFileDialog()
    }
  }
</script>

<div class="card hero">
  <h2>Nahrání Dat</h2>
  <p>
    Nahrajte Excel z vaší analýzy. Soubor bude zpracován a nahrán do databáze.
  </p>
  <div class="upload-panel">
    <div
      class="dropzone {isDragActive ? 'drag-active' : ''}"
      role="button"
      tabindex="0"
      onclick={openFileDialog}
      onkeydown={handleDropzoneKeydown}
      ondragover={handleDragOver}
      ondragleave={handleDragLeave}
      ondrop={handleDrop}
    >
      <input
        bind:this={fileInputRef}
        class="file-input"
        type="file"
        accept=".xlsx,.xls,.csv"
        multiple
        onchange={handleFileChange}
      />
      <div class="dropzone-content">
        <span class="dropzone-title">Přetáhněte soubor nebo</span>
        <span class="browse-button">Vybrat soubor</span>
        <span class="dropzone-hint">Podporuje .xlsx, .xls, .csv</span>
      </div>
      <div class="file-meta">
        <span class="file-name">
          {uploadFiles.length > 0
            ? `Vybráno souborů: ${uploadFiles.length}`
            : 'Soubor nevybrán'}
        </span>
        {#if uploadFiles.length > 0}
          <button
            type="button"
            class="clear-file"
            aria-label="Odebrat všechny soubory"
            onclick={(e) => {
              e.stopPropagation()
              clearSelectedFile()
            }}
          >
            Odebrat vše
          </button>
        {/if}
      </div>
      {#if uploadFiles.length > 0}
        <ul class="file-list">
          {#each uploadFiles as file, index}
            <li class="file-item">
              <span>{file.name}</span>
              <button
                type="button"
                class="remove-file"
                aria-label={`Odebrat ${file.name}`}
                onclick={(e) => {
                  e.stopPropagation()
                  removeFile(index)
                }}
              >
                Odebrat
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
    <div class="hero-actions">
      <button type="button" class="ghost" disabled={isUploading} onclick={handleUpload}>
        {isUploading ? 'Nahrávám...' : 'Nahrát soubor'}
      </button>
    </div>
    {#if uploadMessage}
      <p class="success">{uploadMessage}</p>
    {/if}
    {#if uploadError}
      <p class="error">{uploadError}</p>
    {/if}
  </div>
</div>
