from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError

from app.database import SessionLocal
from app.models.climate_log import ClimateLog
from app.models.room import Room
from app.schemas.climate_log import ClimateLogCreateSchema, ClimateLogOutSchema
from app.utils import parse_shift_bound, validation_error_response

bp = Blueprint("climate_logs", __name__, url_prefix="/api/climate-logs")

create_schema = ClimateLogCreateSchema()
out_schema = ClimateLogOutSchema()
out_many = ClimateLogOutSchema(many=True)


@bp.get("")
@jwt_required()
def list_climate_logs():
    db = SessionLocal()
    try:
        q = db.query(ClimateLog)

        # roomId 只认出菇室主键（整数），绝不拿室代号比对
        raw_room_id = request.args.get("roomId", type=str)
        if raw_room_id is not None and raw_room_id.strip() != "":
            try:
                room_pk = int(raw_room_id)
            except (TypeError, ValueError):
                return jsonify({"detail": "roomId 须为出菇室主键（整数）"}), 400
            q = q.filter(ClimateLog.room_id == room_pk)

        # 班次时刻窗：保留时分秒；from > to 直接拒绝
        raw_from = request.args.get("from")
        raw_to = request.args.get("to")
        d0 = parse_shift_bound(raw_from) if raw_from else None
        d1 = parse_shift_bound(raw_to) if raw_to else None
        if raw_from and d0 is None:
            return jsonify({"detail": "from 时刻格式无法识别"}), 400
        if raw_to and d1 is None:
            return jsonify({"detail": "to 时刻格式无法识别"}), 400
        if d0 is not None and d1 is not None and d0 > d1:
            return jsonify({"detail": "from 不得晚于 to"}), 400
        if d0 is not None:
            q = q.filter(ClimateLog.recorded_at >= d0)
        if d1 is not None:
            q = q.filter(ClimateLog.recorded_at <= d1)

        # humidityMin 按数值比较
        raw_humidity_min = request.args.get("humidityMin")
        if raw_humidity_min is not None and raw_humidity_min.strip() != "":
            try:
                humidity_min = float(raw_humidity_min)
            except (TypeError, ValueError):
                return jsonify({"detail": "humidityMin 须为数值"}), 400
            q = q.filter(ClimateLog.humidity_pct >= humidity_min)

        rows = q.order_by(ClimateLog.recorded_at.desc()).all()
        return jsonify(out_many.dump(rows))
    finally:
        db.close()


@bp.post("")
@jwt_required()
def create_climate_log():
    db = SessionLocal()
    try:
        try:
            data = create_schema.load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return validation_error_response(err)
        room = db.query(Room).filter(Room.id == data["room_id"]).first()
        if not room:
            return jsonify({"detail": "出菇室不存在"}), 400
        item = ClimateLog(
            room_id=data["room_id"],
            recorded_at=data["recorded_at"],
            temp_c=data["temp_c"],
            humidity_pct=data["humidity_pct"],
            co2_ppm=data.get("co2_ppm"),
            notes=data.get("notes"),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return jsonify(out_schema.dump(item)), 201
    finally:
        db.close()


@bp.delete("/<int:log_id>")
@jwt_required()
def delete_climate_log(log_id: int):
    db = SessionLocal()
    try:
        item = db.query(ClimateLog).filter(ClimateLog.id == log_id).first()
        if not item:
            return jsonify({"detail": "环境记录不存在"}), 404
        db.delete(item)
        db.commit()
        return "", 204
    finally:
        db.close()
