import os
import re
import glob
import hashlib
import json
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLANIFICACIONES_DIR = os.path.join(BASE_DIR, "Planificaciones")
INDEX_CACHE_FILE = os.path.join(PLANIFICACIONES_DIR, ".pdf_index.json")

_gdrive_id_re = re.compile(r"/file/d/([A-Za-z0-9_-]+)")
_INVALID_NAME_RE = re.compile(r"no[\s_.-]*valido", re.IGNORECASE)
_flag_snapshot = None
_flag_hashes = None


def gdrive_file_id(url):
    if not url:
        return None
    m = _gdrive_id_re.search(str(url))
    return m.group(1) if m else None


def ensure_planificaciones_dir():
    os.makedirs(PLANIFICACIONES_DIR, exist_ok=True)


def _file_hash(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _invalid_hash_set():
    global _flag_snapshot, _flag_hashes
    flagged = [p for p in list_local_pdfs() if _INVALID_NAME_RE.search(os.path.basename(p))]
    snapshot = tuple((os.path.basename(p), os.path.getsize(p), os.path.getmtime(p)) for p in flagged)
    if _flag_hashes is None or snapshot != _flag_snapshot:
        _flag_hashes = {_file_hash(p) for p in flagged}
        _flag_snapshot = snapshot
    return _flag_hashes


def is_invalid_doc(path):
    if not path or not os.path.exists(path):
        return True
    if _INVALID_NAME_RE.search(os.path.basename(path)):
        return True
    return _file_hash(path) in _invalid_hash_set()


def local_pdf_for_url(url):
    file_id = gdrive_file_id(url)
    if not file_id:
        return None
    dest = os.path.join(PLANIFICACIONES_DIR, f"{file_id}.pdf")
    if os.path.exists(dest) and not is_invalid_doc(dest):
        return dest
    return None


def local_dest_for_url(url):
    file_id = gdrive_file_id(url)
    if not file_id:
        return None
    return os.path.join(PLANIFICACIONES_DIR, f"{file_id}.pdf")


_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
_DL_CONFIRM_RE = re.compile(r"confirm=([0-9A-Za-z_-]+)")


def _gdrive_open(dl_url):
    req = urllib.request.Request(dl_url, headers={"User-Agent": _UA})
    return urllib.request.urlopen(req, timeout=60)


def _stream_download(resp, dest_path, prefix=b""):
    with open(dest_path, "wb") as f:
        if prefix:
            f.write(prefix)
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    return dest_path


def download_gdrive_pdf(url, dest_path):
    file_id = gdrive_file_id(url)
    if not file_id:
        return None
    if os.path.exists(dest_path):
        if not is_invalid_doc(dest_path):
            return dest_path
        return None
    try:
        resp = _gdrive_open(f"https://drive.google.com/uc?export=download&id={file_id}")
        prefix = resp.read(4)
        if prefix.startswith(b"%PDF"):
            return _stream_download(resp, dest_path, prefix)
        token = _DL_CONFIRM_RE.search((prefix + resp.read()).decode("utf-8", errors="replace"))
        if token:
            resp = _gdrive_open(
                f"https://drive.google.com/uc?export=download&id={file_id}&confirm={token.group(1)}"
            )
            prefix = resp.read(4)
            if prefix.startswith(b"%PDF"):
                return _stream_download(resp, dest_path, prefix)
    except Exception:
        return None
    return None


def list_local_pdfs():
    return sorted(glob.glob(os.path.join(PLANIFICACIONES_DIR, "*.pdf")))


def _cache_signature():
    items = []
    for path in list_local_pdfs():
        if is_invalid_doc(path):
            continue
        st = os.stat(path)
        items.append([os.path.basename(path), int(st.st_mtime), st.st_size])
    return sorted(items)


def _load_index_cache(signature):
    try:
        with open(INDEX_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("signature") == signature:
            return data.get("index")
    except Exception:
        pass
    return None


def _save_index_cache(signature, index):
    try:
        with open(INDEX_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"signature": signature, "index": index}, f)
    except Exception:
        pass


def index_local_pdfs():
    from modules.date_comparison.date_extractor import extract_project_code

    signature = _cache_signature()
    cached = _load_index_cache(signature)
    if cached is not None:
        return cached

    indexed = {}
    for path in list_local_pdfs():
        if is_invalid_doc(path):
            continue
        try:
            code = extract_project_code(path)
            if code:
                indexed.setdefault(code, []).append(path)
        except Exception:
            continue

    _save_index_cache(signature, indexed)
    return indexed