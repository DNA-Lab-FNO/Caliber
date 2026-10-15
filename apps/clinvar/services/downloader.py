import urllib.request
import hashlib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Static, permanent URLs to the latest monthly ClinVar VCV releases
CLINVAR_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ClinVarVCVRelease_00-latest.xml.gz"
)
MD5_URL = f"{CLINVAR_URL}.md5"

TARGET_DIR = Path("data/clinvar")
LOCAL_FILE = TARGET_DIR / "ClinVarVCVRelease_00-latest.xml.gz"


def verify_md5(file_path: Path, expected_md5: str) -> bool:
    """Calculates file MD5 in chunks to check data integrity."""
    if not file_path.exists():
        logger.warning(f"File {file_path} does not exist for MD5 verification.")
        return False

    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest() == expected_md5


def download_monthly_release():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    expected_md5 = None
    try:
        logger.info("Fetching expected MD5 hash from NCBI...")
        with urllib.request.urlopen(MD5_URL, timeout=10) as response:
            expected_md5 = response.read().decode("utf-8").split()[0].strip()
    except Exception as e:
        if LOCAL_FILE.exists() and LOCAL_FILE.stat().st_size > 100 * 1024 * 1024:
            logger.warning(
                f"Could not reach NCBI to check latest MD5 ({e}), but local ClinVar archive exists. Proceeding with existing archive."
            )
            return
        raise


    # 2. Cache Check: Compare with local file if it exists
    if LOCAL_FILE.exists():
        logger.info("Comparing local file hash with server hash...")
        if verify_md5(LOCAL_FILE, expected_md5):
            logger.info(
                "Your local ClinVar archive is already up to date with the latest monthly release. Skipping."
            )
            return
        logger.warning(
            "New monthly release detected or local file is corrupted. Starting download..."
        )

    # 3. Stream the download directly to disk (safeguards RAM usage)
    logger.info("Downloading massive release file (~30GB+ uncompressed)...")
    with urllib.request.urlopen(CLINVAR_URL) as remote_stream:
        with open(LOCAL_FILE, "wb") as local_file:
            while chunk := remote_stream.read(
                65536
            ):  # Large 64KB buffers for high throughput
                local_file.write(chunk)
                logger.debug(f"Downloaded chunk of size {len(chunk)} bytes.")
    # 4. Final verification block
    if verify_md5(LOCAL_FILE, expected_md5):
        logger.info(f"Success! Downloaded and verified: {LOCAL_FILE}")
    else:
        logger.error(
            "CRITICAL: Download completed but MD5 verification failed. The file might be corrupted."
        )
        raise IOError("ClinVar release MD5 verification failed. Aborting sync.")
