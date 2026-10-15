from django.test import TestCase
from apps.clinvar.services.importer import ClinVarBulkImporter
from apps.clinvar.services.transformer import TransformedVariant
from apps.clinvar.services.parser import TranscriptAnnotation
from apps.core.enums import ClassificationEnum
from apps.clinvar.models import ClinVarGeneVariant
from apps.core.models import GeneVariant, compute_allele_hash


class ClinVarBulkImporterTests(TestCase):
    def test_import_long_allele_variants_without_index_overflow(self):
        long_ref = "A" * 7500
        long_alt = "T" * 7500

        variant_item = TransformedVariant(
            variation_id=7606,
            variation_type="Indel",
            chromosome="chr6",
            position=32812345,
            ref_allele=long_ref,
            alt_allele=long_alt,
            dbsnp="rs12345678",
            disease="Immunodeficiency",
            last_updated="2026-01-01",
            genes=["TAPBP"],
            transcript_annotations=[
                TranscriptAnnotation(
                    transcript_base="NM_005500",
                    transcript_version=3,
                    hgvs_c="c.100delins" + ("A" * 100),
                    hgvs_p="p.Val34delins" + ("X" * 10),
                )
            ],
            classification=ClassificationEnum.PATHOGENIC,
        )

        importer = ClinVarBulkImporter(batch_size=1)
        importer.add_variant(variant_item)

        # Confirm the GeneVariant was saved with the full long alleles and correct allele_hash
        var = GeneVariant.objects.get(chromosome="chr6", position=32812345)
        self.assertEqual(var.ref_allele, long_ref)
        self.assertEqual(var.alt_allele, long_alt)
        self.assertEqual(var.allele_hash, compute_allele_hash(long_ref, long_alt))

        # Confirm ClinVarGeneVariant was created
        cv = ClinVarGeneVariant.objects.get(gene_variant=var)
        self.assertEqual(cv.clinvar_id, "7606")
        self.assertEqual(cv.clinvar_classification, ClassificationEnum.PATHOGENIC.score)

        # Test duplicate import (upsert on conflict) does not crash and updates fields
        variant_item.dbsnp = "rs87654321"
        importer.add_variant(variant_item)

        var.refresh_from_db()
        self.assertEqual(var.dbsnp, "rs87654321")
