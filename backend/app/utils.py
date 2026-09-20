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


def _parse_datetime_text(text: str):
    """严格解析时刻文本，保留时分秒；无法解析时返回 None。"""
    cleaned = text.replace("Z", "").replace("z", "")
    if "+" in cleaned[10:]:
        cleaned = cleaned[: cleaned.index("+", 10)]
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ):
        try:
            parsed = datetime.strptime(cleaned[:26], fmt)
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(cleaned)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


def normalize_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    value = (str(value) if value is not None else "").strip()
    if not value:
        return datetime.now()
    return _parse_datetime_text(value) or datetime.now()


def parse_shift_bound(value: str):
    """解析班次时刻边界，保留时分秒（不按 date 截断）。

    空值返回 None；无法解析时也返回 None，由调用方决定如何报错。
    """
    value = (value or "").strip()
    if not value:
        return None
    return _parse_datetime_text(value)
