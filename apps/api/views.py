import logging
import io
import polars as pl
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from apps.core.auth import login_required_json
from apps.api.services import (
    annotate_excel_workbook,
    get_variant_hashes_from_db,
    process_uploaded_variants_file,
    query_variants,
)
from apps.core.management.commands.init_db import (
    parse_excel_dbsnp,
)
from apps.core.management.commands.init_db import parse_excel_hgvs

logger = logging.getLogger(__name__)

# TODO: Add authentication and permissions to restrict access to these endpoints
# TODO: Imporove FE part so it displays all the info about the variant in the detail.
@login_required_json
def search_variants(request):
    """
    Search for variants based on query parameters.
    Query Parameters:
    - variant: The variant identifier (e.g., HGVS notation).
    - gene: The gene symbol (e.g., BRCA1).
    - dbsnp: The dbSNP identifier (e.g., rs123456).
    - page: The page number for pagination (default: 1).
    - per_page: The number of results per page (default: 50).
    Returns:
    - JSON response containing the search results and pagination metadata.

    The search first attempts to find matching variants in the internal patient records.
    If no matches are found, it falls back to searching the ClinVar database.
    """
    variant = request.GET.get("variant", "").strip()
    gene = request.GET.get("gene", "").strip()
    dbsnp = request.GET.get("dbsnp", "").strip()
    page_number = request.GET.get("page", 1)
    per_page = request.GET.get("per_page", 50)

    if not (variant or gene or dbsnp):
        return JsonResponse(
            {"results": [], "meta": {"has_next": False, "total_count": 0}}
        )

    try:
        response_data = query_variants(variant, gene, dbsnp, page_number, per_page)
        return JsonResponse(response_data)
    except Exception as e:
        logger.exception("Chyba při vyhledávání variant.")
        return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)


@require_POST
@login_required_json
def upload_variants_file(request):
    """
    Handle the upload of variant files (Excel) and process them to populate the database.
    Expects files to be uploaded under the "file" key in the request.
    Returns a JSON response indicating the success or failure of the operation.
    """
    user = request.user

    uploaded_files = request.FILES.getlist("file")
    if not uploaded_files:
        return JsonResponse({"error": "No file provided."}, status=400)

    allowed_extensions = {".xlsx", ".xls", ".csv"}
    for uploaded in uploaded_files:
        if not any(uploaded.name.lower().endswith(ext) for ext in allowed_extensions):
            return JsonResponse(
                {"error": f"Unsupported file type: {uploaded.name}."}, status=400
            )

    results = []
    try:
        for uploaded in uploaded_files:
            file_result = process_uploaded_variants_file(uploaded, user=user)
            results.append(file_result)

        return JsonResponse(
            {
                "filenames": [item["filename"] for item in results],
                "rows": sum(item["rows"] for item in results),
                "files": results,
            }
        )
    except Exception as e:
        logger.exception("Chyba při nahrávání souboru variant.")
        return JsonResponse(
            {"error": f"Chyba při zpracování souborů: {str(e)}"}, status=500
        )

#TODO Sheet name have to be either default or we have to get it from the user. Currently it is hardcoded to default.
@require_POST
@login_required_json
def classify_variants(request):
    """
    Handle the upload of an Excel file containing variants and classify them based on internal and ClinVar data.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Requires POST method."}, status=405)

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"error": "No file provided."}, status=400)

    allowed_extensions = {
        ".xlsx"
    }  # Currently only supporting .xlsx for classification due to usage of openpyxl, but can be extended to .xls with additional handling if needed
    name_lower = uploaded_file.name.lower()
    if not any(name_lower.endswith(ext) for ext in allowed_extensions):
        return JsonResponse(
            {"error": f"Unsupported file type: {uploaded_file.name}."},
            status=400,
        )

    try:
        file_bytes = uploaded_file.read()
        df = pl.read_excel(io.BytesIO(file_bytes))

        gene_col = None
        hgsv_c_col = None
        dbsnp_col = None

        for orig_col in df.columns:
            low = orig_col.lower()
            if low in ["symbol", "gene"]:
                gene_col = orig_col
            elif low in ["nucleotide"]:
                hgsv_c_col = orig_col
            elif low in ["hgvsc"]:
                hgsv_c_col = orig_col
            elif low in ["vep dbsnp id", "dbsnp"]:
                dbsnp_col = orig_col

        if not (gene_col or hgsv_c_col or dbsnp_col):
            return JsonResponse(
                {
                    "error": "Chybná struktura Excelu. Tabulka musí obsahovat alespoň jeden ze sloupců: Gen, Varianta, dbSNP."
                },
                status=400,
            )

        unique_dbsnps = []

        if dbsnp_col:
            parsed_dbsnps = [
                parse_excel_dbsnp(str(x).strip())
                for x in df[dbsnp_col].drop_nulls().unique().to_list()
            ]

            unique_dbsnps = [
                db
                for db in parsed_dbsnps
                if db and db.strip() not in ["", "-", "—", "none", "nan"]
            ]

        if hgsv_c_col:
            raw_variants = [
                str(x).strip()
                for x in df[hgsv_c_col].drop_nulls().unique().to_list()
                if str(x).strip()
            ]

            unique_variants = []
            for v in raw_variants:
                _, _, hgvs = parse_excel_hgvs(v)
                if hgvs:
                    unique_variants.append(hgvs)

        dbsnp_map, hgvs_map = get_variant_hashes_from_db(unique_dbsnps, unique_variants)

        output = annotate_excel_workbook(file_bytes, dbsnp_map, hgvs_map)

        response = HttpResponse(
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            'attachment; filename="analyzovaný_report.xlsx"'
        )
        return response

    except Exception as e:
        return JsonResponse(
            {"error": f"Chyba serveru při analýze: {str(e)}"}, status=500
        )
