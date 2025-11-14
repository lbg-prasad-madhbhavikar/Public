import os
import io
import re
import math
import pathlib
import concurrent.futures
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Tuple
# -------------------------
# Configuration
# -------------------------
DIRECTORY_PATH = "Data_Contracts_upload"
UPLOAD_URL = "https://registration.lcap.ap-int.oncp.group/foundation-api/api/large-file/upload"
ASSEMBLE_URL = "https://registration.lcap.ap-int.oncp.group/foundation-api/api/large-file/assemble"

HEADERS = {
    "Authorization": "Bearer JWT eyJraWQiOiJsYmdKd3RUb2tlbklkMDEiLCJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJMQ0FQLUFWQVRBUiIsInN1YiI6ImF2YXRhcnxiYzgyZTFmZi1mOWJiLTQ2NTYtOTAyOS1hZjdmMDk0MTlhNTJ8MTIzMjMiLCJhdWQiOlsiMDFkMzAzN2ItM2IyYi00NGVjLThjMWUtYjdlY2ZkY2M1MzFhIiwiODQxY2M5OTktYjZkNi00MzljLTk5OWQtODlmNDQwNzgxMDI5Il0sImlhdCI6MTc2MjI3NTMzOCwiZXhwIjoxNzYyMjc2MjM4LCJnaXZlbl9uYW1lIjoiYXZhdGFyIiwiZmFtaWx5X25hbWUiOiJhZG1pbjEiLCJlbWFpbCI6ImF2YXRhci1hZG1pbkBsbG95ZHNiYW5raW5nLmNvbSIsInBpY3R1cmUiOiJodHRwOi8vZXhhbXBsZS5jb20vamFuZWRvZS9tZS5qcGciLCJyb2xlIjoiQURNSU4iLCJwZXJtaXNzaW9ucyI6WyJ2aWV3IiwiZWRpdCIsImNyZWF0ZSIsInVwZGF0ZSIsImRlbGV0ZSJdfQ.BTkhgFcWvgtyxl1Bwh1Y75vsml8Mf-xzNgZrapKlNZnorAekykC_0ydkLzYZ6Pe68m9zVSTkE6FtGN8Mcrpb6g",
    "x-tenant-id": "avatar",
    "x-correlation-id": "bdf86ef7-721e-44e2-a48f-31af998b60v7"
}

# Chunk size per part (1 MiB)
PART_SIZE = 1000 * 1024

# Concurrency controls
FILE_CONCURRENCY = 4         # how many files to process at the same time
PART_CONCURRENCY = 8         # how many parts to upload in parallel per file

# HTTP robustness
REQUEST_TIMEOUT = (30, 120)  # (connect_timeout, read_timeout) seconds
RETRY_TOTAL = 5
RETRY_BACKOFF = 0.5
RETRY_STATUSES = (500, 502, 503, 504)
VERIFY_SSL = False  # you had verify=False; leaving configurable


# -------------------------
# Helpers
# -------------------------

def disable_insecure_warning():
    if not VERIFY_SSL:
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=RETRY_TOTAL,
        backoff_factor=RETRY_BACKOFF,
        status_forcelist=RETRY_STATUSES,
        method_whitelist=frozenset(["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_skip_list_csv(directory_path: str) -> set:
    """
    Reads contract.csv from the given directory, returns a set of contractIds to skip.

    Robust against:
      - Windows/Excel encodings (utf-8-sig, utf-8, cp1252, latin-1)
      - Odd line endings and embedded newlines
      - Multi-delimiter formats (comma/semicolon/tab)
      - Optional header row ('contractId')

    Only the FIRST column is used per line.
    """
    csv_path = pathlib.Path(directory_path) / "contract.csv"
    skip_ids = set()
    if not csv_path.exists():
        print("No contract.csv found. Proceeding without skip list.")
        return skip_ids

    # Read bytes once
    raw = csv_path.read_bytes()

    # Try multiple decodings
    encodings_to_try = ["utf-8-sig", "utf-8", "cp1252", "latin-1"]
    text = None
    chosen_encoding = None
    for enc in encodings_to_try:
        try:
            text = raw.decode(enc)
            chosen_encoding = enc
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode("latin-1", errors="replace")
        chosen_encoding = "latin-1 (with replacements)"
        print("Warning: Decoded contract.csv with latin-1 and replacement characters. "
              "Consider saving as UTF-8 for best results.")

    print(f"Reading skip list from: {csv_path} (encoding: {chosen_encoding})")

    # Normalize line endings to '\n'
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split into lines and pick the first column only
    lines = text.split("\n")

    # Collect tokens from the first column (split on comma/semicolon/tab once)
    tokens = []
    for ln in lines:
        if not ln:
            continue
        # ignore comment lines if any
        if ln.lstrip().startswith(("#", "//", ";")):
            continue

        # Extract the first field by common delimiters (comma, semicolon, tab)
        first = re.split(r"[,;\t]", ln, maxsplit=1)[0]
        # Trim quotes and BOM residues
        first = first.strip().strip('"').strip("'").lstrip("\ufeff")
        if first:
            tokens.append(first)

    if not tokens:
        print("contract.csv is empty. Proceeding without skip list.")
        return skip_ids

    # If the first token is a header 'contractId', drop it
    if tokens[0].lower() == "contractid":
        tokens = tokens[1:]

    # Add to set
    for val in tokens:
        if val:
            skip_ids.add(val)

    print(f"Loaded {len(skip_ids)} contractId(s) to skip.")
    return skip_ids


def is_contract_json(path: pathlib.Path) -> bool:
    return path.is_file() and path.name.lower().endswith(".contract.json")


def extract_asset_id(filename: str) -> str:
    """
    Safely strips the trailing '.contract.json' suffix (case-insensitive) to get contractId.
    """
    suffix = ".contract.json"
    if filename.lower().endswith(suffix):
        return filename[: -len(suffix)]
    # Fallback: legacy behavior (may be unsafe with extra dots)
    return filename.split(".")[0]


def upload_part_from_source_file(
    session: requests.Session,
    file_path: pathlib.Path,
    asset_id: str,
    part_number: int,
    total_parts: int,
    part_size: int,
) -> bool:
    """
    Reads the correct byte range from the source file and uploads it as a multipart part.
    Avoids creating temp part files on disk.
    """
    try:
        file_size = file_path.stat().st_size
        offset = (part_number - 1) * part_size
        if offset >= file_size:
            print(f"[{asset_id}] Part {part_number}: offset beyond file size. Skipping.")
            return False
        to_read = min(part_size, file_size - offset)

        with open(file_path, "rb") as f:
            f.seek(offset)
            data = f.read(to_read)

        files = {
            "file": (f"{file_path.name}.part{part_number}", io.BytesIO(data), "application/octet-stream")
        }
        headers = {
            **HEADERS,
            "x-correlation-id": f"{asset_id}-{part_number}"
        }

        resp = session.post(
            UPLOAD_URL,
            headers=headers,
            data={
                "contractId": asset_id,
                "partNumber": part_number,
                "totalParts": total_parts
            },
            files=files,
            timeout=REQUEST_TIMEOUT,
            verify=VERIFY_SSL,
        )
        if resp.status_code in (200, 201, 202, 204):
            return True
        else:
            print(f"[{asset_id}] Part {part_number} upload failed. "
                  f"HTTP {resp.status_code}. Response: {resp.text[:500]}")
            return False
    except Exception as e:
        print(f"[{asset_id}] Part {part_number} upload error: {e}")
        return False


def process_single_contract_file(
    session: requests.Session,
    file_path: pathlib.Path,
    skip_ids: set,
) -> Tuple[str, str]:
    """
    Processes one .contract.json file: splits into parts (byte-accurate),
    uploads all parts (in parallel), and calls assemble.
    Returns (asset_id, status) where status is 'skipped' | 'assembled' | 'failed'.
    """
    filename = file_path.name
    asset_id = extract_asset_id(filename)

    if asset_id in skip_ids:
        print(f"Skipping {filename} because assetId is in contract.csv")
        return asset_id, "skipped"

    file_size = file_path.stat().st_size
    total_parts = max(1, math.ceil(file_size / PART_SIZE))

    print(f"[{asset_id}] Found: {filename} ({file_size} bytes). Parts: {total_parts}")

    # Upload all parts concurrently (per file)
    with concurrent.futures.ThreadPoolExecutor(max_workers=PART_CONCURRENCY) as executor:
        futures = [
            executor.submit(
                upload_part_from_source_file,
                session,
                file_path,
                asset_id,
                part_number,
                total_parts,
                PART_SIZE,
            )
            for part_number in range(1, total_parts + 1)
        ]
        results = []
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    if all(results):
        print(f"[{asset_id}] All parts uploaded. Calling assemble API...")
        try:
            resp = session.get(
                ASSEMBLE_URL,
                headers=HEADERS,
                params={"contractId": asset_id},
                timeout=REQUEST_TIMEOUT,
                verify=VERIFY_SSL,
            )
            if resp.status_code in (200, 201, 202, 204):
                print(f"[{asset_id}] Assemble successful. HTTP {resp.status_code}")
                return asset_id, "assembled"
            else:
                print(f"[{asset_id}] Assemble failed. HTTP {resp.status_code}. Response: {resp.text[:500]}")
                return asset_id, "failed"
        except Exception as e:
            print(f"[{asset_id}] Assemble error: {e}")
            return asset_id, "failed"
    else:
        print(f"[{asset_id}] Upload failed for one or more parts.")
        return asset_id, "failed"


# -------------------------
# Main
# -------------------------
def main():
    disable_insecure_warning()

    base_dir = pathlib.Path(DIRECTORY_PATH)
    if not base_dir.exists():
        raise FileNotFoundError(f"Directory not found: {DIRECTORY_PATH}")

    # Load skip list from contract.csv (if present)
    skip_ids = load_skip_list_csv(DIRECTORY_PATH)

    # Discover all .contract.json files
    files = [p for p in base_dir.iterdir() if is_contract_json(p)]
    if not files:
        print("No *.contract.json files found.")
        return

    print(f"Discovered {len(files)} contract file(s).")

    session = build_session()

    assembled = 0
    failed = 0
    skipped = 0

    # Process multiple files concurrently
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=FILE_CONCURRENCY) as executor:
            future_to_path = {
                executor.submit(process_single_contract_file, session, p, skip_ids): p
                for p in files
            }
            for future in concurrent.futures.as_completed(future_to_path):
                try:
                    asset_id, status = future.result()
                    if status == "assembled":
                        assembled += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    failed += 1
    except KeyboardInterrupt:
        print("\nInterrupted by user. Shutting down...")

    total = len(files)
    print("----- SUMMARY -----")
    print(f"Total discovered : {total}")
    print(f"Skipped          : {skipped}")
    print(f"Success        : {assembled}")
    print(f"Failed           : {failed}")


if __name__ == "__main__":
    main()