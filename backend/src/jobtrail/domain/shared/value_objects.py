"""集約をまたいで使う値の正規化。"""

import hashlib
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

from jobtrail.domain.shared.errors import ContentTooLargeError

_LEGAL_FORMS = re.compile(r"株式会社|有限会社|合同会社|\(株\)|\(有\)|\(同\)")
_SPACES = re.compile(r"\s+")


def normalize_company_name(name: str) -> str:
    """表記ゆれ（全半角・大小・空白・法人格）を吸収した比較用の社名を返す。"""
    text = unicodedata.normalize("NFKC", name).casefold()
    return _SPACES.sub("", _LEGAL_FORMS.sub("", text))


def normalize_url(url: str) -> str:
    """スキーム・ホストの大小と末尾スラッシュ、フラグメントの差を吸収する。"""
    parts = urlsplit(url.strip())
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, "")
    )


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def ensure_text_size(text: str, limit: int) -> None:
    if len(text) > limit:
        raise ContentTooLargeError(len(text), limit)
