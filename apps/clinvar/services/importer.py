from datetime import datetime, timezone as dt_timezone
import logging
from django.db import transaction
from apps.clinvar.models import ClinVarGeneVariant
from apps.core.models import Gene, GeneVariant, TranscriptAnnotation, compute_allele_hash

logger = logging.getLogger(__name__)


def parse_last_updated(date_str: str | None) -> datetime:
    if not date_str:
        return datetime(2026, 1, 1, tzinfo=dt_timezone.utc)
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt
    except Exception:
        return datetime(2026, 1, 1, tzinfo=dt_timezone.utc)


class ClinVarBulkImporter:
    def __init__(self, batch_size: int = 10000):
        self.batch_size = batch_size
        self.buffer = []

        # Human gene pool is small (~30,000 genes total).
        # We can safely cache ALL genes in memory without leaking RAM.
        self.gene_cache = {g.symbol: g.id for g in Gene.objects.all()}

    def add_variant(self, parsed_var):
        """Buffers parsed dataclass items and automatically flushes when full."""
        self.buffer.append(parsed_var)
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self):
        """
        Executes the heavy lifting. Processes the accumulated buffer in
        highly optimized database batches using a 4-stage pipeline.
        """
        if not self.buffer:
            return

        # Filter out records missing vital genomic coordinates up front
        valid_items = [
            item
            for item in self.buffer
            if item.chromosome and item.position and item.ref_allele and item.alt_allele
        ]

        if not valid_items:
            self.buffer.clear()
            return

        try:
            with transaction.atomic():
                # STAGE 1: Bulk resolve missing Gene entities
                self._bulk_resolve_genes(valid_items)

                # STAGE 2: Bulk upsert GeneVariant records
                variant_instances = self._bulk_upsert_variants(valid_items)

                # Map original parsed elements to their newly saved database primary keys
                variant_mapping = {
                    (
                        v.chromosome,
                        v.position,
                        v.variation_type,
                        v.allele_hash,
                    ): v.id
                    for v in variant_instances
                }

                # STAGE 3: Bulk process intermediate Relationships
                self._bulk_insert_relations(valid_items, variant_mapping)

        except Exception as e:
            logger.error(f"Database write execution crash on batch: {str(e)}")
            raise e
        finally:
            # Always empty memory cache structures regardless of transaction state
            self.buffer.clear()

    def _bulk_resolve_genes(self, items):
        """Identifies and creates unlogged genes in a single bulk sweep."""
        unique_symbols = set(sym for item in items for sym in item.genes if sym)
        missing_symbols = [sym for sym in unique_symbols if sym not in self.gene_cache]

        if missing_symbols:
            Gene.objects.bulk_create(
                [Gene(symbol=sym) for sym in missing_symbols], ignore_conflicts=True
            )
            # Update the application level master gene dictionary cache
            self.gene_cache.update(
                {
                    g.symbol: g.id
                    for g in Gene.objects.filter(symbol__in=missing_symbols)
                }
            )

    def _bulk_upsert_variants(self, items) -> list:
        """Uses database engine indexing mechanics to handle conflicts in bulk."""
        variant_instances = [
            GeneVariant(
                chromosome=item.chromosome,
                position=item.position,
                variation_type=item.variation_type,
                ref_allele=item.ref_allele,
                alt_allele=item.alt_allele,
                allele_hash=compute_allele_hash(item.ref_allele, item.alt_allele),
                dbsnp=item.dbsnp or "",
            )
            for item in items
        ]

        # On conflict (duplicate coordinates + allele hash), refresh the dbSNP field value and return the ID
        return GeneVariant.objects.bulk_create(
            variant_instances,
            update_conflicts=True,
            unique_fields=[
                "chromosome",
                "position",
                "variation_type",
                "allele_hash",
            ],
            update_fields=["dbsnp"],
        )

    def _bulk_insert_relations(self, items, variant_mapping):
        """Batches out child elements using explicit relational through tables."""
        m2m_through_instances = []
        transcript_instances = []
        clinvar_instances = []

        # Deduping sets to avoid duplicate key errors inside the single memory block
        seen_m2m = set()
        seen_transcripts = set()
        seen_clinvar = set()

        # Gather target relationship database rows in memory
        for item in items:
            v_id = variant_mapping.get(
                (
                    item.chromosome,
                    item.position,
                    item.variation_type,
                    compute_allele_hash(item.ref_allele, item.alt_allele),
                )
            )

            if not v_id:
                continue

            # A. Gene Many-to-Many through links
            for symbol in item.genes:
                g_id = self.gene_cache.get(symbol)
                if g_id and (v_id, g_id) not in seen_m2m:
                    m2m_through_instances.append(
                        GeneVariant.genes.through(genevariant_id=v_id, gene_id=g_id)
                    )
                    seen_m2m.add((v_id, g_id))

            # B. Transcript Annotation Child Records
            for trans in item.transcript_annotations:
                if trans.hgvs_c and (v_id, trans.hgvs_c) not in seen_transcripts:
                    transcript_instances.append(
                        TranscriptAnnotation(
                            variant_id=v_id,
                            transcript_base=trans.transcript_base,
                            transcript_version=trans.transcript_version,
                            hgvs_c=trans.hgvs_c,
                            hgvs_p=trans.hgvs_p or "",
                        )
                    )
                    seen_transcripts.add((v_id, trans.hgvs_c))

            # C. ClinVar Metadata Domain Records
            if v_id not in seen_clinvar:
                clinvar_instances.append(
                    ClinVarGeneVariant(
                        gene_variant_id=v_id,
                        clinvar_id=str(item.variation_id),
                        clinvar_classification=item.classification.score,
                        last_updated=parse_last_updated(item.last_updated),
                    )
                )
                seen_clinvar.add(v_id)

        # Execute ultra-fast, isolated database inserts for all child collections
        if m2m_through_instances:
            GeneVariant.genes.through.objects.bulk_create(
                m2m_through_instances, ignore_conflicts=True
            )
        if transcript_instances:
            TranscriptAnnotation.objects.bulk_create(
                transcript_instances, ignore_conflicts=True
            )
        if clinvar_instances:
            ClinVarGeneVariant.objects.bulk_create(
                clinvar_instances,
                update_conflicts=True,
                unique_fields=["gene_variant"],
                update_fields=["clinvar_classification", "last_updated"],
            )
