import re
from enum import Enum


class ClassificationEnum(Enum):
    PATHOGENIC = "Pathogenic"
    PATHOGENIC_LIKELY_PATHOGENIC = "Pathogenic/Likely pathogenic"
    LIKELY_PATHOGENIC = "Likely pathogenic"
    UNCERTAIN_SIGNIFICANCE = "Uncertain significance"
    LIKELY_BENIGN_UNCERTAIN_SIGNIFICANCE = "Likely benign/Uncertain significance"
    LIKELY_BENIGN = "Likely benign"
    BENIGN_LIKELY_BENIGN = "Benign/Likely benign"
    BENIGN = "Benign"

    @classmethod
    def from_clinvar_string(cls, value: str | None) -> "ClassificationEnum":
        """
        Parses high-frequency exact matches instantly, then routes complex
        compound terms through fallback logic. Safe for millions of rows.
        """
        if not value:
            return cls.UNCERTAIN_SIGNIFICANCE

        norm = value.strip().lower()

        # Step 1: O(1) Fast path for the top 99% of variants
        if norm in cls._DIRECT_MAP:
            return cls._DIRECT_MAP[norm]

        # Step 2: Fallback logic for compound strings / low penetrance tail

        # Unify conflicting classifications or explicit unprovided statuses
        if (
            "conflict" in norm
            or "not provided" in norm
            or "no classification" in norm
            or "[missing" in norm
        ):
            return cls.UNCERTAIN_SIGNIFICANCE

        # Handle combinations of pathogenic variants
        if "pathogenic" in norm:
            if "likely" in norm and "pathogenic/likely" not in norm:
                return cls.LIKELY_PATHOGENIC
            if "likely" in norm and "pathogenic/likely" in norm:
                return cls.PATHOGENIC_LIKELY_PATHOGENIC
            return cls.PATHOGENIC

        # Handle combinations of benign variants
        if "benign" in norm:
            if "uncertain" in norm:
                return cls.LIKELY_BENIGN_UNCERTAIN_SIGNIFICANCE
            if "likely" in norm and "benign/likely" not in norm:
                return cls.LIKELY_BENIGN
            if "likely" in norm and "benign/likely" in norm:
                return cls.BENIGN_LIKELY_BENIGN
            return cls.BENIGN

        # Explicit custom ClinVar sub-tiers (VUS-high, VUS-mid, VUS-low)
        if "vus" in norm:
            return cls.UNCERTAIN_SIGNIFICANCE

        # Default fallback for everything else (drug response, risk factor, modifiers)
        return cls.UNCERTAIN_SIGNIFICANCE

    @classmethod
    def from_excel_string(cls, value: str | None) -> "ClassificationEnum":
        if not value:
            return cls.UNCERTAIN_SIGNIFICANCE
        norm = value.strip()
        return cls._EXCEL_MAP.get(norm, cls.UNCERTAIN_SIGNIFICANCE)

    @property
    def score(self) -> float:
        """Returns the numeric float score of the enum instance."""
        return self._SCORES.get(self.value, 3.0)


ClassificationEnum._DIRECT_MAP = {
    "uncertain significance": ClassificationEnum.UNCERTAIN_SIGNIFICANCE,
    "likely benign": ClassificationEnum.LIKELY_BENIGN,
    "[missing / no assertion provided]": ClassificationEnum.UNCERTAIN_SIGNIFICANCE,
    "benign": ClassificationEnum.BENIGN,
    "pathogenic": ClassificationEnum.PATHOGENIC,
    "likely pathogenic": ClassificationEnum.LIKELY_PATHOGENIC,
    "conflicting classifications of pathogenicity": ClassificationEnum.UNCERTAIN_SIGNIFICANCE,
    "benign/likely benign": ClassificationEnum.BENIGN_LIKELY_BENIGN,
    "pathogenic/likely pathogenic": ClassificationEnum.PATHOGENIC_LIKELY_PATHOGENIC,
    "not provided": ClassificationEnum.UNCERTAIN_SIGNIFICANCE,
}

ClassificationEnum._EXCEL_MAP = {
    "5": ClassificationEnum.PATHOGENIC,
    "4-5": ClassificationEnum.PATHOGENIC_LIKELY_PATHOGENIC,
    "4": ClassificationEnum.LIKELY_PATHOGENIC,
    "3": ClassificationEnum.UNCERTAIN_SIGNIFICANCE,
    "2-3": ClassificationEnum.LIKELY_BENIGN_UNCERTAIN_SIGNIFICANCE,
    "2": ClassificationEnum.LIKELY_BENIGN,
    "1-2": ClassificationEnum.BENIGN_LIKELY_BENIGN,
    "1": ClassificationEnum.BENIGN,
}

ClassificationEnum._CLASSIFICATION_SCORE_TO_STRING = {
    5.0: "5",
    4.5: "4-5",
    4.0: "4",
    3.0: "3",
    2.5: "2-3",
    2.0: "2",
    1.5: "1-2",
    1.0: "1",
}

ClassificationEnum._SCORES = {
    "Pathogenic": 5.0,
    "Pathogenic/Likely pathogenic": 4.5,
    "Likely pathogenic": 4.0,
    "Uncertain significance": 3.0,
    "Likely benign/Uncertain significance": 2.5,
    "Likely benign": 2.0,
    "Benign/Likely benign": 1.5,
    "Benign": 1.0,
}
