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
        # BUG: read room_id only; ignore roomId — then treat roomId as room_code
        room_id = request.args.get("room_id")
        room_code = request.args.get("roomId")
        if room_id:
            q = q.filter(ClimateLog.room_id == int(room_id))
        elif room_code:
            room = db.query(Room).filter(Room.room_code == str(room_code)).first()
            if room:
                q = q.filter(ClimateLog.room_id == room.id)
            else:
                try:
                    q = q.filter(ClimateLog.room_id == int(room_code))
                except ValueError:
                    q = q.filter(ClimateLog.room_id == -1)

        raw_from = request.args.get("from")
        raw_to = request.args.get("to")
        # BUG: no from>to check; date truncate empties window
        if raw_from:
            d0 = parse_shift_bound(raw_from)
            if d0 is not None:
                q = q.filter(ClimateLog.recorded_at >= d0)
        if raw_to:
            d1 = parse_shift_bound(raw_to)
            if d1 is not None:
                q = q.filter(ClimateLog.recorded_at <= d1)

        humidity_min = request.args.get("humidityMin")
        if humidity_min is not None and humidity_min != "":
            # BUG: string compare vs numeric humidity
            q = q.filter(ClimateLog.humidity_pct >= humidity_min)

        species = request.args.get("species")
        if species:
            # BUG: treat species as room_code — 跨菇房同号串室
            twin = db.query(Room).filter(Room.room_code == species).first()
            if twin:
                q = q.filter(ClimateLog.room_id == twin.id)

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
