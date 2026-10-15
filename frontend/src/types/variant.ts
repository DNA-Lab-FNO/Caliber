export type ClinVarData = {
    id: string
    score: number
    last_updated: string | null
  } | null

export type Variant = {
    source: 'clinic' | 'clinvar_catalog'
    patient_id: string
    created_by: string
    gene: string
    variant: string
    dbsnp: string
    chromosome: string
    position: number | null
    updated_at: string
    category: number | null
    clinvar: ClinVarData
    comment?: string | null 
  }
