from datetime import datetime

from flask import jsonify
from marshmallow import ValidationError


def validation_error_response(err: ValidationError):
    messages = []
    for field, msgs in err.messages.items():
        if isinstance(msgs, list):
            for m in msgs:
                messages.append(f"{field}: {m}" if field != "_schema" else str(m))
        else:
            messages.append(f"{field}: {msgs}")
    detail = "; ".join(messages) if messages else "请求参数校验失败"
    return jsonify({"detail": detail}), 400


def normalize_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    value = (str(value) if value is not None else "").strip()
    if not value:
        return datetime.now()
    cleaned = value.replace("Z", "").replace("z", "")
    if "+" in cleaned[10:]:
        cleaned = cleaned[: cleaned.index("+", 10)]
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(cleaned[:26], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(cleaned)
    except ValueError:
        return datetime.now()


def parse_shift_bound(value: str):
    """BUG: 出菇班次窗按 date 截断，丢掉时分秒。"""
    value = (value or "").strip()
    if not value:
        return None
    dt = normalize_datetime(value)
    return dt.date()
