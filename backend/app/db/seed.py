"""Idempotent synthetic demo seed. Data is NOT real production telemetry."""

from __future__ import annotations

import hashlib
import math
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.constants import SENSOR_PARAM_SPECS
from app.core.roles import ROLE_LABELS, UserRole
from app.core.security import hash_password
from app.models import (
    Alert,
    EquipmentUnit,
    Failure,
    MaintenanceAction,
    OilField,
    OperationalState,
    Role,
    Sensor,
    SensorType,
    Telemetry,
    User,
    Well,
    WellPad,
)


def seed_database(db: Session, *, force_telemetry: bool = False) -> dict[str, int]:
    settings = get_settings()
    stats = {
        "roles": 0,
        "users": 0,
        "fields": 0,
        "wells": 0,
        "telemetry": 0,
        "events": 0,
    }

    for code, name in ROLE_LABELS.items():
        role = db.query(Role).filter(Role.code == code).first()
        if not role:
            db.add(Role(code=code, name=name, description=name))
            stats["roles"] += 1
    db.flush()

    def ensure_user(username: str, password: str, full_name: str, role_code: str) -> None:
        nonlocal stats
        if db.query(User).filter(User.username == username).first():
            return
        role = db.query(Role).filter(Role.code == role_code).one()
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                full_name=full_name,
                email=f"{username}@example.local",
                role_id=role.id,
                is_active=True,
            )
        )
        stats["users"] += 1

    ensure_user(
        settings.admin_username,
        settings.admin_password,
        settings.admin_full_name,
        UserRole.ADMIN,
    )
    ensure_user("technologist", "TechnoDemo123!", "Иванов П.А. (технолог)", UserRole.TECHNOLOGIST)
    ensure_user("viewer", "ViewerDemo123!", "Петрова Н.С. (просмотр)", UserRole.VIEWER)

    for code, spec in SENSOR_PARAM_SPECS.items():
        if not db.query(SensorType).filter(SensorType.code == code).first():
            db.add(
                SensorType(
                    code=code,
                    name=spec["name"],
                    unit=spec["unit"],
                    min_value=spec["min"],
                    max_value=spec["max"],
                    critical_min=spec["critical_min"],
                    critical_max=spec["critical_max"],
                )
            )
    db.flush()

    fields_spec = [
        ("Самотлорское", "SAM", "ХМАО"),
        ("Приобское", "PRB", "ХМАО"),
    ]
    field_rows: list[OilField] = []
    for name, code, region in fields_spec:
        row = db.query(OilField).filter(OilField.code == code).first()
        if not row:
            row = OilField(name=name, code=code, region=region, description="Синтетическое месторождение")
            db.add(row)
            db.flush()
            stats["fields"] += 1
        field_rows.append(row)

    # Wells: create once
    existing_wells = db.query(Well).count()
    wells: list[Well] = []
    if existing_wells == 0:
        pad_counter = 1
        well_defs = [
            ("SAM-101", "SAM", "normal", False),
            ("SAM-102", "SAM", "warning", True),
            ("SAM-103", "SAM", "normal", False),
            ("SAM-104", "SAM", "critical", True),
            ("PRB-201", "PRB", "normal", False),
            ("PRB-202", "PRB", "warning", True),
            ("PRB-203", "PRB", "stopped", False),
            ("PRB-204", "PRB", "normal", False),
        ]
        pads_by_field: dict[str, WellPad] = {}
        for field in field_rows:
            pad = WellPad(
                oil_field_id=field.id,
                name=f"Куст {pad_counter}",
                code=f"{field.code}-P{pad_counter}",
                latitude=61.0 + pad_counter * 0.1,
                longitude=73.0 + pad_counter * 0.1,
            )
            db.add(pad)
            db.flush()
            pads_by_field[field.code] = pad
            pad_counter += 1
            # second pad
            pad2 = WellPad(
                oil_field_id=field.id,
                name=f"Куст {pad_counter}",
                code=f"{field.code}-P{pad_counter}",
                latitude=61.0 + pad_counter * 0.1,
                longitude=73.0 + pad_counter * 0.1,
            )
            db.add(pad2)
            db.flush()
            pads_by_field[f"{field.code}2"] = pad2
            pad_counter += 1

        sensor_types = {st.code: st for st in db.query(SensorType).all()}
        now = datetime.now(timezone.utc)

        for idx, (wname, fcode, status, degraded) in enumerate(well_defs):
            field = next(f for f in field_rows if f.code == fcode)
            pad = pads_by_field[fcode] if idx % 2 == 0 else pads_by_field[f"{fcode}2"]
            well = Well(
                well_pad_id=pad.id,
                name=wname,
                inventory_number=f"INV-{1000 + idx}",
                depth_m=2200 + idx * 35,
                status=status,
                commissioning_date=now - timedelta(days=400 + idx * 20),
                notes="Синтетический объект для демонстрации GNO Monitor",
            )
            db.add(well)
            db.flush()
            stats["wells"] += 1

            pump = EquipmentUnit(
                well_id=well.id,
                equipment_type="pump",
                name=f"УЭЦН {wname}",
                manufacturer="Новомет",
                model="ЭЦН5-125",
                serial_number=f"P-{wname}",
                rated_power_kw=90,
                rated_current_a=55,
                rated_voltage_v=380,
                install_date=now - timedelta(days=300),
                status="operating" if status != "stopped" else "stopped",
            )
            motor = EquipmentUnit(
                well_id=well.id,
                equipment_type="motor",
                name=f"ПЭД {wname}",
                manufacturer="Борец",
                model="ПЭД-90",
                serial_number=f"M-{wname}",
                rated_power_kw=90,
                rated_current_a=55,
                rated_voltage_v=380,
                install_date=now - timedelta(days=300),
                status="operating" if status != "stopped" else "stopped",
            )
            cable = EquipmentUnit(
                well_id=well.id,
                equipment_type="cable",
                name=f"Кабель {wname}",
                manufacturer="Камкабель",
                model="КГБ 3х16",
                serial_number=f"C-{wname}",
                install_date=now - timedelta(days=300),
                status="operating",
            )
            db.add_all([pump, motor, cable])
            db.flush()

            for code, st in sensor_types.items():
                equip = motor if "motor" in code or "current" in code or "voltage" in code else pump
                db.add(
                    Sensor(
                        well_id=well.id,
                        equipment_unit_id=equip.id,
                        sensor_type_id=st.id,
                        tag=f"{wname}.{code}",
                        is_active=True,
                    )
                )
            db.flush()

            db.add(
                OperationalState(
                    well_id=well.id,
                    state="running" if status != "stopped" else "stopped",
                    started_at=now - timedelta(days=10),
                    description="Синтетическое состояние",
                )
            )

            if degraded or idx in {1, 3, 5}:
                db.add(
                    Failure(
                        well_id=well.id,
                        equipment_unit_id=pump.id,
                        failure_type="Снижение подачи",
                        severity="high" if status == "critical" else "medium",
                        occurred_at=now - timedelta(days=5 + idx),
                        downtime_hours=8 + idx,
                        presumed_cause="Износ рабочих органов / осложнения",
                        description="Синтетический отказ для обучения/демо аналитики",
                    )
                )
                stats["events"] += 1

            db.add(
                MaintenanceAction(
                    well_id=well.id,
                    equipment_unit_id=pump.id,
                    action_type="ТО-2",
                    started_at=now - timedelta(days=40 + idx * 3),
                    ended_at=now - timedelta(days=39 + idx * 3),
                    performer="Бригада №3",
                    result="Выполнено",
                    description="Синтетическое ТО",
                )
            )
            stats["events"] += 1
            wells.append(well)
        db.flush()
    else:
        wells = db.query(Well).all()

    # Telemetry: seed if empty
    tel_count = db.query(Telemetry).count()
    if tel_count == 0 or force_telemetry:
        if force_telemetry and tel_count:
            db.query(Telemetry).delete()
            db.flush()
        stats["telemetry"] = _seed_telemetry(db, wells)

    db.commit()
    return stats


def _seed_telemetry(db: Session, wells: list[Well]) -> int:
    import os

    rng = random.Random(42)
    now = datetime.now(timezone.utc)
    created = 0
    sensors = db.query(Sensor).all()
    sensors_by_well: dict[int, list[Sensor]] = {}
    for s in sensors:
        sensors_by_well.setdefault(s.well_id, []).append(s)

    sensor_types = {st.id: st for st in db.query(SensorType).all()}
    # Full demo: 14 days hourly. Light mode (tests): 3 days every 2 hours, key params only.
    light = os.environ.get("SEED_LIGHT", "").lower() in {"1", "true", "yes"}
    hours_back = 3 * 24 if light else 14 * 24
    step = 2 if light else 1
    key_codes = {
        "intake_pressure",
        "temperature",
        "motor_temperature",
        "current_a",
        "vibration",
        "flow_rate",
        "rpm",
        "power",
        "load",
    }

    for well in wells:
        degraded = well.status in {"warning", "critical"}
        stopped = well.status == "stopped"
        well_sensors = sensors_by_well.get(well.id, [])
        if light:
            well_sensors = [
                s for s in well_sensors if sensor_types[s.sensor_type_id].code in key_codes
            ]
        for hour in range(0, hours_back, step):
            ts = now - timedelta(hours=hours_back - hour)
            tnorm = hour / max(hours_back, 1)
            for sensor in well_sensors:
                st = sensor_types[sensor.sensor_type_id]
                base = (st.min_value + st.max_value) / 2 if st.min_value and st.max_value else 50
                amp = (st.max_value - st.min_value) * 0.08 if st.min_value and st.max_value else 2
                value = base + amp * math.sin(hour / 6 + hash(well.name) % 7) + rng.uniform(-amp * 0.2, amp * 0.2)
                if degraded:
                    # Progressive degradation + sharp recent deterioration for alert demos
                    recent = 1.0 if hour >= hours_back - 24 else tnorm
                    if st.code == "vibration":
                        value = 4.0 + 5.5 * recent + rng.uniform(0, 0.4)
                    elif st.code == "motor_temperature":
                        value = 95.0 + 25.0 * recent + rng.uniform(-1, 1)
                    elif st.code == "current_a":
                        value = 55.0 + 20.0 * recent + rng.uniform(-1, 2)
                    elif st.code == "intake_pressure":
                        value = 5.0 - 2.2 * recent
                    elif st.code == "flow_rate":
                        value = 180.0 - 90.0 * recent
                    else:
                        if st.code in {"temperature"}:
                            value += 15.0 * recent
                if stopped:
                    if st.code in {"flow_rate", "rpm", "current_a", "power", "load"}:
                        value *= 0.05
                key = hashlib.sha1(f"{sensor.id}:{ts.isoformat()}".encode()).hexdigest()[:24]
                db.add(
                    Telemetry(
                        well_id=well.id,
                        equipment_unit_id=sensor.equipment_unit_id,
                        sensor_id=sensor.id,
                        parameter_code=st.code,
                        value=round(float(value), 3),
                        unit=st.unit,
                        quality_flag="good",
                        source="seed",
                        recorded_at=ts,
                        idempotency_key=key,
                    )
                )
                created += 1
            if hour % 50 == 0:
                db.flush()
    db.flush()
    return created

