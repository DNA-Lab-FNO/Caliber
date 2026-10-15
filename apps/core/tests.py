import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthFlowTests(TestCase):
	def test_status_is_unauthenticated_by_default(self):
		response = self.client.get(reverse("auth_status"))
		self.assertEqual(response.status_code, 200)
		self.assertFalse(response.json()["authenticated"])

	def test_register_logs_user_in(self):
		response = self.client.post(
			reverse("register_view"),
			data=json.dumps(
				{
					"email": "doctor@example.com",
					"username": "oncology",
					"password": "StrongPass123!",
					"password_confirm": "StrongPass123!",
				}
			),
			content_type="application/json",
		)

		self.assertEqual(response.status_code, 201)
		payload = response.json()
		self.assertTrue(payload["authenticated"])
		self.assertEqual(payload["user"]["email"], "doctor@example.com")
		self.assertTrue(get_user_model().objects.filter(email="doctor@example.com").exists())

	def test_search_requires_authentication(self):
		response = self.client.get(reverse("search_variants"), {"gene": "BRCA1"})
		self.assertEqual(response.status_code, 401)

	def test_login_and_logout_round_trip(self):
		user = get_user_model().objects.create_user(
			email="nurse@example.com",
			username="ward-a",
			password="StrongPass123!",
		)

		login_response = self.client.post(
			reverse("login_view"),
			data=json.dumps({"email": user.email, "password": "StrongPass123!"}),
			content_type="application/json",
		)
		self.assertEqual(login_response.status_code, 200)
		self.assertTrue(login_response.json()["authenticated"])

		logout_response = self.client.post(reverse("logout_view"))
		self.assertEqual(logout_response.status_code, 200)
		self.assertFalse(logout_response.json()["authenticated"])


class InitDBCacheTests(TestCase):
	def test_import_caches_clear(self):
		import polars as pl
		from apps.core.management.commands.init_db import ImportCaches
		from apps.core.models import Patient

		caches = ImportCaches()
		caches.patient_cache["P001"] = Patient(name="P001")
		caches.variant_gene_m2m_cache.add((1, 2))
		self.assertEqual(len(caches.patient_cache), 1)
		self.assertEqual(len(caches.variant_gene_m2m_cache), 1)

		caches.clear()
		self.assertEqual(len(caches.patient_cache), 0)
		self.assertEqual(len(caches.variant_gene_m2m_cache), 0)

	def test_parse_df_clears_caches_after_execution(self):
		import polars as pl
		from apps.core.management.commands.init_db import parse_df, ImportCaches
		from apps.core.models import Patient, GeneVariant

		df = pl.DataFrame({
			"Name": ["Patient_A"],
			"Symbol": ["BRCA1"],
			"Variant_class": ["SNV"],
			"Chr": ["chr17"],
			"Coordinate": [43044295],
			"Reference": ["A"],
			"Alternate": ["G"],
			"VEP dbSNP ID": ["rs12345"],
			"HGVSc": ["NM_007294.3:c.100A>G"],
			"HGVSp": ["p.Lys34Arg"],
			"Kategorie": ["3"],
			"Komentář": ["Test comment"],
			"Exon": ["2"],
			"Genotype": ["het"],
			"gnomAD AF": ["0.001"],
		})

		parse_df(df, "test_file.xlsx")

		self.assertTrue(Patient.objects.filter(name="Patient_A").exists())
		self.assertTrue(GeneVariant.objects.filter(dbsnp="rs12345").exists())

	def test_parse_df_clears_owned_caches_on_exception(self):
		import polars as pl
		from apps.core.management.commands.init_db import parse_df

		df = pl.DataFrame({
			"Coordinate": ["invalid-int-value"],
		})

		with self.assertRaises(ValueError):
			parse_df(df, "faulty.xlsx")


