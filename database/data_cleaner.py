"""تنظيف وتوحيد بيانات Excel قبل الاستيراد."""

from __future__ import annotations

import datetime
import re
import unicodedata
from typing import Any

import pandas as pd

_ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652\u0670\u0640]")
_HIDDEN_CHARS = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
_PUNCTUATION = re.compile(r"[^\w\s\u0600-\u06FF.-]", re.UNICODE)


def clean_text(value: Any) -> str:
    """تنظيف نصي شامل: مسافات، تشكيل، أحرف مخفية، توحيد أحرف عربية."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    text = _HIDDEN_CHARS.sub("", text)
    text = unicodedata.normalize("NFKC", text)
    text = _ARABIC_DIACRITICS.sub("", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ئ", "ي")
    text = text.replace("ة", "ه")
    text = _PUNCTUATION.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_numeric_text(value: Any) -> str:
    """تحويل الأرقام النصية/العشرية إلى تمثيل نصي موحّد."""
    text = clean_text(value)
    if not text:
        return ""
    text = text.replace(",", "").replace("،", "")
    if re.fullmatch(r"-?\d+\.0+", text):
        return str(int(float(text)))
    return text


def normalize_date_value(value: Any) -> datetime.date | None:
    """توحيد تنسيق التاريخ من Excel أو نص."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        try:
            return datetime.datetime.strptime(digits, "%Y%m%d").date()
        except ValueError:
            return None
    return None


def clean_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """تنظيف DataFrame بالكامل: إزالة الصفوف الفارغة وتنظيف كل الخلايا."""
    if dataframe is None or dataframe.empty:
        return dataframe
    cleaned = dataframe.copy()
    cleaned.columns = [clean_text(col) for col in cleaned.columns]
    cleaned = cleaned.dropna(how="all")
    for column in cleaned.columns:
        cleaned[column] = cleaned[column].apply(
            lambda v: clean_numeric_text(v) if isinstance(v, (int, float)) or str(v).strip().replace(".", "", 1).isdigit() else clean_text(v)
        )
    cleaned = cleaned[~cleaned.apply(lambda row: all(not str(v).strip() for v in row), axis=1)]
    cleaned = cleaned.reset_index(drop=True)
    return cleaned
