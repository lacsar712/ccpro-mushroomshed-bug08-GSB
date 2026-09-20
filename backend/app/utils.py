from datetime import datetime, timezone

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
    """解析时刻；带时区的输入统一换算为 UTC naive，与库中 DATETIME 一致。"""
    if isinstance(value, datetime):
        dt = value
    else:
        text = (str(value) if value is not None else "").strip()
        if not text:
            return datetime.utcnow()
        cleaned = text.replace("Z", "+00:00").replace("z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            dt = None
            for fmt in (
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d",
            ):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return datetime.utcnow()
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def parse_shift_bound(value):
    """解析班次窗口边界，保留时分秒；空串或无法解析时返回 None。"""
    if isinstance(value, datetime):
        dt = value
    else:
        text = (value or "").strip()
        if not text:
            return None
        cleaned = text.replace("Z", "+00:00").replace("z", "+00:00")
        try:
            dt = datetime.fromisoformat(cleaned)
        except ValueError:
            dt = None
            for fmt in (
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d",
            ):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
