from datetime import date
import logging
from dataclasses import dataclass
import gzip
from pathlib import Path

from apps.core.management.commands.init_db import normalize_var_type

logger = logging.getLogger(__name__)

try:
    from lxml import etree

    logger.info("running with lxml.etree")
except ImportError:
    import xml.etree.ElementTree as etree

    logger.info("running with Python's xml.etree.ElementTree")

DATA_DIR = Path("data/clinvar")
CLINVAR_ZIP_PATH = DATA_DIR / "ClinVarVCVRelease_00-latest.xml.gz"


@dataclass
class TranscriptAnnotation:
    transcript_base: str | None
    transcript_version: int | None
    hgvs_c: str | None
    hgvs_p: str | None


@dataclass
class ParsedVariant:
    variation_id: int
    variation_type: str

    chromosome: str | None
    position: int | None
    ref_allele: str | None
    alt_allele: str | None

    last_updated: str

    genes: list[str]
    transcript_annotations: list[TranscriptAnnotation]
    dbsnp: str | None

    classification: str | None
    disease: str | None


def parse_variation_coding(
    variation_elem: etree.Element,
) -> tuple[str | None, int | None, str | None, str | None]:
    """Extracts chromosome, position, ref allele, and alt allele from the XML element attributes."""
    chromosome = None
    position = None
    ref_allele = None
    alt_allele = None

    for loc in variation_elem.findall("Location/SequenceLocation"):
        if loc.get("Assembly") == "GRCh38":
            chromosome = f"chr{loc.get('Chr')}"
            position_text = loc.get("positionVCF") or loc.get("start")
            ref_allele = loc.get("referenceAlleleVCF")
            alt_allele = loc.get("alternateAlleleVCF")

            if position_text and position_text.isdigit():
                position = int(position_text)
            break

    return chromosome, position, ref_allele, alt_allele


def process_variation(variation_elem: etree.Element) -> ParsedVariant | None:
    allele_record = variation_elem.find(".//SimpleAllele")
    if allele_record is None:
        return None

    transcript_annotations = _get_mane_hgvs(allele_record)
    if not transcript_annotations:
        return None

    var_id_raw = variation_elem.get("VariationID")
    if not var_id_raw:
        return None

    var_id = int(var_id_raw)

    last_updated_raw = variation_elem.get("DateLastUpdated")
    last_updated = (
        last_updated_raw.strip() if last_updated_raw else date.today().isoformat()
    )
    variation_type = normalize_var_type(variation_elem.get("VariationType"))

    chromosome, position, ref_allele, alt_allele = parse_variation_coding(allele_record)

    genes = _get_genes(allele_record)
    dbsnp = _get_dbsnp(allele_record)

    classification = variation_elem.findtext(
        ".//Classifications/GermlineClassification/Description"
    )

    disease = None
    element_val = variation_elem.find(
        ".//Classifications/GermlineClassification//Trait/Name/ElementValue"
    )
    if element_val is not None:
        disease = element_val.text

    return ParsedVariant(
        variation_id=var_id,
        variation_type=variation_type,
        last_updated=last_updated,
        genes=genes,
        position=position,
        chromosome=chromosome,
        ref_allele=ref_allele,
        alt_allele=alt_allele,
        transcript_annotations=transcript_annotations,
        dbsnp=dbsnp,
        classification=classification,
        disease=disease,
    )


def _get_mane_hgvs(allele_record: etree.Element) -> list[TranscriptAnnotation]:
    """Finds all coding HGVS annotations tagged with MANESelect='true' using XML attributes."""
    annotations = []

    for hgvs in allele_record.findall("HGVSlist/HGVS"):
        if hgvs.get("Type") != "coding":
            continue

        nuc_expr = hgvs.find("NucleotideExpression")
        if nuc_expr is not None and nuc_expr.get("MANESelect") == "true":
            transcript_base = nuc_expr.get("sequenceAccession")
            transcript_version = nuc_expr.get("sequenceVersion")
            hgvs_c = nuc_expr.get("change")

            hgvs_p = None
            prot_expr = hgvs.find("ProteinExpression")
            if prot_expr is not None:
                hgvs_p = prot_expr.get("change")

                if not hgvs_p:
                    full_hgvs_p = prot_expr.findtext("Expression")
                    if full_hgvs_p:
                        hgvs_p = (
                            full_hgvs_p.split(":")[-1]
                            if ":" in full_hgvs_p
                            else full_hgvs_p
                        )

            version_int = (
                int(transcript_version)
                if transcript_version and transcript_version.isdigit()
                else None
            )

            annotations.append(
                TranscriptAnnotation(
                    transcript_base=transcript_base,
                    transcript_version=version_int,
                    hgvs_c=hgvs_c,
                    hgvs_p=hgvs_p,
                )
            )

    return annotations


def _get_genes(allele_record: etree.Element) -> list[str]:
    """Extracts gene symbols."""
    genes = []
    for gene in allele_record.findall("GeneList/Gene"):
        symbol = gene.get("Symbol")
        if symbol:
            genes.append(symbol)
    return genes


def _get_dbsnp(allele_record: etree.Element) -> str | None:
    """Extracts the rsID from dbSNP."""
    for xref in allele_record.findall("XRefList/XRef"):
        if xref.get("DB") == "dbSNP" and xref.get("Type") == "rs":
            return f"rs{xref.get('ID')}"
    return None


def parse_clinvar_xml():
    with gzip.open(CLINVAR_ZIP_PATH, "rb") as f:
        context = etree.iterparse(
            f, events=("end",), tag=("ClinVarVariationRelease", "VariationArchive")
        )

        for event, elem in context:
            # 1. Capture the global release metadata when its closing tag is reached
            if elem.tag == "ClinVarVariationRelease":
                release_date = elem.get("ReleaseDate")
                logger.info(f"--- ClinVar Release Date: {release_date} ---")
                elem.clear()

            # 2. Extract, process, and yield individual variants
            elif elem.tag == "VariationArchive":
                parsed = process_variation(elem)
                if parsed:
                    yield parsed

                # --- CRITICAL MEMORY MANAGEMENT FOR 69GB FILES ---
                # Wipe the children/text of the current element
                elem.clear()

                # Sever the link to all preceding siblings in the XML tree.
                # This allows Python's Garbage Collector to free the parsed chunks.
                parent = elem.getparent()
                if parent is not None:
                    while elem.getprevious() is not None:
                        del parent[0]

        # Explicitly clean up the iterator context when finished
        del context
