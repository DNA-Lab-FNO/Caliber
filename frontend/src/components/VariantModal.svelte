<script lang="ts">
  import type { Variant } from '../types/variant'
  
  interface Props {
    variant: Variant;
    onclose: () => void;
  }

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      }
    };
  }

  let { variant, onclose }: Props = $props();
</script>

<div 
  class="modal-backdrop" 
  use:portal 
  onclick={onclose} 
  onkeydown={(e) => { if (e.key === 'Escape') onclose(); }}
  role="button" 
  tabindex="0"
  aria-label="Zavřít modal"
>
  <div 
    class="modal-content card" 
    role="dialog"
    aria-modal="true"
    tabindex="-1"
    onclick={(e) => e.stopPropagation()}
    onkeydown={(e) => e.stopPropagation()}
  >
    <div class="modal-header">
      <h3>Detaily: {variant.gene} ({variant.variant || 'Neznámá varianta'})</h3>
      <button type="button" class="close-btn ghost" onclick={onclose}>✕</button>
    </div>
    
    <div class="modal-body">
      <div class="detail-group">
        <span class="muted">Pacient ID</span>
        <p>{variant.patient_id}</p>
      </div>
      
      <div class="detail-group">
        <span class="muted">Komentář k variantě</span>
        <p>{variant.comment || 'Žádný komentář není k dispozici.'}</p>
      </div>
      
      <div class="detail-group">
        <span class="muted">Vytvořil</span>
        <p>{variant.created_by}</p>
      </div>
    </div>
  </div>
</div>