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

    def test_import_with_in_batch_duplicate_variants(self):
        # Two items with the same genomic coordinates and alleles in the SAME batch
        var1 = TransformedVariant(
            variation_id=1001,
            variation_type="SNV",
            chromosome="chr1",
            position=500000,
            ref_allele="A",
            alt_allele="C",
            dbsnp="",
            disease="Phenotype A",
            last_updated="2026-01-01",
            genes=["TEST1"],
            transcript_annotations=[],
            classification=ClassificationEnum.BENIGN,
        )
        var2 = TransformedVariant(
            variation_id=1002,
            variation_type="SNV",
            chromosome="chr1",
            position=500000,
            ref_allele="A",
            alt_allele="C",
            dbsnp="rs999000",
            disease="Phenotype B",
            last_updated="2026-02-01",
            genes=["TEST1"],
            transcript_annotations=[],
            classification=ClassificationEnum.PATHOGENIC,
        )

        importer = ClinVarBulkImporter(batch_size=10)
        importer.add_variant(var1)
        importer.add_variant(var2)
        importer.flush()

        # Should not crash with CardinalityViolation
        variants = GeneVariant.objects.filter(chromosome="chr1", position=500000)
        self.assertEqual(variants.count(), 1)
        self.assertEqual(variants.first().dbsnp, "rs999000")

    def test_import_long_hgvs_strings_and_distinct_transcripts(self):
        long_hgvs_c = "c.100delins" + ("A" * 1200)
        long_hgvs_p = "p.Ala10delins" + ("Met" * 300)

        variant_item = TransformedVariant(
            variation_id=2001,
            variation_type="Indel",
            chromosome="chr2",
            position=1000000,
            ref_allele="A",
            alt_allele="T",
            dbsnp="rs111222",
            disease="Test Condition",
            last_updated="2026-01-01",
            genes=["GENE1"],
            transcript_annotations=[
                # Transcript 1 with long HGVS
                TranscriptAnnotation(
                    transcript_base="NM_001001",
                    transcript_version=1,
                    hgvs_c=long_hgvs_c,
                    hgvs_p=long_hgvs_p,
                ),
                # Transcript 2 with same hgvs_c but different transcript_base
                TranscriptAnnotation(
                    transcript_base="NM_001002",
                    transcript_version=2,
                    hgvs_c=long_hgvs_c,
                    hgvs_p=long_hgvs_p,
                ),
            ],
            classification=ClassificationEnum.PATHOGENIC,
        )

        importer = ClinVarBulkImporter(batch_size=1)
        importer.add_variant(variant_item)

        var = GeneVariant.objects.get(chromosome="chr2", position=1000000)
        annotations = var.annotations.all().order_by("transcript_base")

        # Verify both transcript annotations were created successfully
        self.assertEqual(annotations.count(), 2)
        self.assertEqual(annotations[0].transcript_base, "NM_001001")
        self.assertEqual(annotations[0].hgvs_c, long_hgvs_c)
        self.assertEqual(annotations[0].hgvs_p, long_hgvs_p)
        self.assertEqual(annotations[1].transcript_base, "NM_001002")
        self.assertEqual(annotations[1].hgvs_c, long_hgvs_c)


