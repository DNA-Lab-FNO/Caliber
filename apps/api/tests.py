from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Gene, GeneVariant, TranscriptAnnotation


class SearchVariantsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="researcher@example.com",
            username="researcher",
            password="StrongPassword123!",
        )
        self.client.force_login(self.user)

        brca1 = Gene.objects.create(symbol="BRCA1")
        cftr = Gene.objects.create(symbol="CFTR")

        variant_one = GeneVariant.objects.create(
            variation_type="deletion",
            chromosome="chr17",
            position=43044295,
            ref_allele="AG",
            alt_allele="",
            dbsnp="rs80357713",
        )
        variant_one.genes.add(brca1)
        TranscriptAnnotation.objects.create(
            variant=variant_one,
            hgvs_c="c.68_69delAG",
            hgvs_p="",
        )

        variant_two = GeneVariant.objects.create(
            variation_type="deletion",
            chromosome="chr7",
            position=117199644,
            ref_allele="CTT",
            alt_allele="",
            dbsnp="rs113993960",
        )
        variant_two.genes.add(cftr)
        TranscriptAnnotation.objects.create(
            variant=variant_two,
            hgvs_c="c.1521_1523delCTT",
            hgvs_p="p.Phe508del",
        )

    def test_empty_query_returns_no_results(self):
        response = self.client.get(reverse("search_variants"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"results": [], "meta": {"has_next": False, "total_count": 0}},
        )

    def test_search_by_gene(self):
        response = self.client.get(
            reverse("search_variants"),
            {"gene": "brca1"},
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["gene"], "BRCA1")

    def test_search_by_dbsnp(self):
        response = self.client.get(
            reverse("search_variants"),
            {"dbsnp": "rs113993960"},
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["dbsnp"], "rs113993960")

    def test_search_by_variant_hgvs(self):
        response = self.client.get(
            reverse("search_variants"),
            {"variant": "c.1521_1523delCTT"},
        )
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["gene"], "CFTR")

