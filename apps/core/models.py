from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from caliber import settings


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email address must be set.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=80)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_created = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email


class Patient(models.Model):
    name = models.CharField(max_length=120, unique=True)


class Gene(models.Model):
    symbol = models.CharField(max_length=32, unique=True)


class GeneVariant(models.Model):
    genes = models.ManyToManyField(Gene, related_name="variants")

    chromosome = models.CharField(max_length=8)
    position = models.BigIntegerField(null=True)

    ref_allele = models.CharField(max_length=255)
    alt_allele = models.CharField(max_length=255)

    variation_type = models.CharField(max_length=32, blank=True)

    dbsnp = models.CharField(max_length=64, blank=True)
    gnomAD = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "chromosome",
                    "position",
                    "variation_type",
                    "ref_allele",
                    "alt_allele",
                ],
                name="unique_genomic_variant",
            )
        ]

        indexes = [
            models.Index(fields=["dbsnp"]),
            models.Index(fields=["chromosome", "position"]),
        ]


class TranscriptAnnotation(models.Model):
    """
    Holds the 1-to-many relationship of transcripts to a variant.
    ClinVar will populate multiple of these; Excel will populate one.
    """

    variant = models.ForeignKey(
        GeneVariant, on_delete=models.CASCADE, related_name="annotations"
    )

    transcript_base = models.CharField(
        max_length=32, db_index=True, null=True, blank=True
    )  # e.g., "NM_000059"
    transcript_version = models.IntegerField(
        null=True, blank=True
    )  # e.g., 3 // The version might change over time, so we store it separately from the base transcript ID.
    hgvs_c = models.CharField(
        max_length=120, db_index=True, null=True, blank=True
    )  # e.g., "c.432A>G"
    hgvs_p = models.CharField(max_length=120, blank=True)

    exon = models.CharField(
        max_length=32, blank=True
    )  # Exon number is transcript-dependent

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["variant", "hgvs_c"],
                name="unique_variant_transcript_annotation",
            )
        ]

        indexes = [
            models.Index(fields=["hgvs_c"]),
            models.Index(fields=["hgvs_p"]),
        ]


class GeneticReport(models.Model):
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="reports"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="genetic_reports"
    )

    report_name = models.CharField(max_length=120, blank=True)


class PatientVariant(models.Model):
    """
    Strictly data regarding THIS patient's observation of the variant.
    """

    report = models.ForeignKey(
        GeneticReport, on_delete=models.CASCADE, related_name="variants"
    )
    variant = models.ForeignKey(GeneVariant, on_delete=models.CASCADE)

    zygosity = models.CharField(max_length=32, blank=True)
    category = models.FloatField(
        null=True, blank=True
    )  # e.g., Lab's specific pathogenic call
    comment = models.TextField(blank=True)

    # original hgvs from excel
    reported_hgvs_c = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("report", "variant")
