import sys
import os
import argparse
import random
import uuid
from datetime import datetime, timedelta, timezone

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
import app.models  # Register all models with Base
from app.models.user import UserModel, UserRole
from app.models.device import DeviceModel, DeviceStatus
from app.models.batch import BatchModel, DuckBreed, BatchStage, BatchStatus
from app.models.session import CandlingSessionModel, CandlingStage
from app.models.scan import EggScanModel, FertilityClass, RoutingAction
from app.models.audit import AuditLogModel


def seed_database(reset: bool = False):
    if reset:
        print("[!] Resetting PostgreSQL public schema (DROP SCHEMA public CASCADE)...")
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
            conn.commit()
        print("[OK] Public schema cleanly recreated.")

    # Guarantee all tables exist
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables verified/created.")

    db = SessionLocal()
    try:
        # ----------------------------------------------------------------------
        # 1. Seed Users
        # ----------------------------------------------------------------------
        print("\n[1/5] Seeding Users...")
        admin_email = "admin@ovalens.fu.edu.ph"
        admin = db.query(UserModel).filter(UserModel.email == admin_email).first()
        if not admin:
            admin = UserModel(
                user_id=uuid.uuid4(),
                email=admin_email,
                hashed_password=get_password_hash("Admin@123"),
                full_name="Dr. Juan Dela Cruz (Admin)",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            print(f"  + Created Admin: {admin_email} / Admin@123")

        # Also seed foundationu.com admin
        fu_admin = db.query(UserModel).filter(UserModel.email == "admin@foundationu.com").first()
        if not fu_admin:
            fu_admin = UserModel(
                user_id=uuid.uuid4(),
                email="admin@foundationu.com",
                hashed_password=get_password_hash("admin123"),
                full_name="Ryle Gabotero (Lead Researcher)",
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(fu_admin)
            print("  + Created Admin: admin@foundationu.com / admin123")

        manager_email = "manager@ovalens.fu.edu.ph"
        if not db.query(UserModel).filter(UserModel.email == manager_email).first():
            manager = UserModel(
                user_id=uuid.uuid4(),
                email=manager_email,
                hashed_password=get_password_hash("Manager@123"),
                full_name="Engr. Maria Santos (Hatchery Manager)",
                role=UserRole.MANAGER,
                is_active=True
            )
            db.add(manager)
            print(f"  + Created Manager: {manager_email} / Manager@123")

        operator_email = "operator@ovalens.fu.edu.ph"
        if not db.query(UserModel).filter(UserModel.email == operator_email).first():
            operator = UserModel(
                user_id=uuid.uuid4(),
                email=operator_email,
                hashed_password=get_password_hash("Operator@123"),
                full_name="Pedro Penduko (Candling Operator)",
                role=UserRole.OPERATOR,
                is_active=True
            )
            db.add(operator)
            print(f"  + Created Operator: {operator_email} / Operator@123")

        # Also seed foundationu.com operator
        fu_operator = db.query(UserModel).filter(UserModel.email == "operator@foundationu.com").first()
        if not fu_operator:
            fu_operator = UserModel(
                user_id=uuid.uuid4(),
                email="operator@foundationu.com",
                hashed_password=get_password_hash("operator123"),
                full_name="Hatchery Shift Operator",
                role=UserRole.OPERATOR,
                is_active=True
            )
            db.add(fu_operator)
            print("  + Created Operator: operator@foundationu.com / operator123")

        db.commit()

        # ----------------------------------------------------------------------
        # 2. Seed Devices
        # ----------------------------------------------------------------------
        print("\n[2/5] Seeding Edge Sorting Stations...")
        d1 = db.query(DeviceModel).filter(DeviceModel.device_id == "STATION-01-RP5").first()
        if not d1:
            d1 = DeviceModel(
                device_id="STATION-01-RP5",
                device_name="Primary Raspberry Pi 5 Sorting Station",
                ip_address="192.168.1.120",
                hardware_platform="Raspberry Pi 5 (8GB)",
                model_version="yolov8n-fp16-v1.0",
                status=DeviceStatus.ONLINE,
                last_heartbeat=datetime.now(timezone.utc),
                conveyor_speed_cm_s=12.50,
                conveyor_dist_cm=25.00,
                servo_pulse_ms=250
            )
            db.add(d1)
            print("  + Created Station: STATION-01-RP5")

        d2 = db.query(DeviceModel).filter(DeviceModel.device_id == "STATION-02-PC").first()
        if not d2:
            d2 = DeviceModel(
                device_id="STATION-02-PC",
                device_name="Secondary Workstation Station",
                ip_address="192.168.1.125",
                hardware_platform="Windows 11 x86_64",
                model_version="yolov8n-fp16-v1.0",
                status=DeviceStatus.OFFLINE,
                last_heartbeat=datetime.now(timezone.utc) - timedelta(hours=2),
                conveyor_speed_cm_s=10.00,
                conveyor_dist_cm=20.00,
                servo_pulse_ms=250
            )
            db.add(d2)
            print("  + Created Station: STATION-02-PC")

        db.commit()

        # ----------------------------------------------------------------------
        # 3. Seed Incubation Batches
        # ----------------------------------------------------------------------
        print("\n[3/5] Seeding Batches...")
        now = datetime.now(timezone.utc)

        batches_data = [
            {
                "batch_id": "BATCH-2026-08-KAY-01",
                "batch_code": "BATCH-2026-08-KAY-01",
                "breed": DuckBreed.KAYUMANGGI,
                "incubator_id": "INCUBATOR-A1",
                "initial_egg_count": 500,
                "set_date": now - timedelta(days=10),
                "target_hatch_date": now - timedelta(days=10) + timedelta(days=28),
                "current_stage": BatchStage.DAY_10,
                "status": BatchStatus.INCUBATING,
                "notes": "Kayumanggi flock from Bayawan breeder farm."
            },
            {
                "batch_id": "BATCH-2026-08-ITM-01",
                "batch_code": "BATCH-2026-08-ITM-01",
                "breed": DuckBreed.ITIM,
                "incubator_id": "INCUBATOR-A2",
                "initial_egg_count": 450,
                "set_date": now - timedelta(days=18),
                "target_hatch_date": now - timedelta(days=18) + timedelta(days=28),
                "current_stage": BatchStage.DAY_18,
                "status": BatchStatus.INCUBATING,
                "notes": "Itim duck eggs, healthy batch."
            },
            {
                "batch_id": "BATCH-2026-07-KHK-01",
                "batch_code": "BATCH-2026-07-KHK-01",
                "breed": DuckBreed.KHAKI,
                "incubator_id": "INCUBATOR-B1",
                "initial_egg_count": 600,
                "set_date": now - timedelta(days=29),
                "target_hatch_date": now - timedelta(days=1),
                "current_stage": BatchStage.COMPLETED,
                "status": BatchStatus.COMPLETED,
                "hatched_count": 532,
                "unhatched_count": 68,
                "notes": "Successful hatch trial, 88.7% hatchability achieved."
            },
            {
                "batch_id": "BATCH-2026-08-KAY-02",
                "batch_code": "BATCH-2026-08-KAY-02",
                "breed": DuckBreed.KAYUMANGGI,
                "incubator_id": "INCUBATOR-B2",
                "initial_egg_count": 500,
                "set_date": now - timedelta(days=2),
                "target_hatch_date": now - timedelta(days=2) + timedelta(days=28),
                "current_stage": BatchStage.SETTING,
                "status": BatchStatus.INCUBATING,
                "notes": "Newly set batch."
            }
        ]

        for b in batches_data:
            existing = db.query(BatchModel).filter(BatchModel.batch_id == b["batch_id"]).first()
            if not existing:
                batch_obj = BatchModel(
                    batch_id=b["batch_id"],
                    batch_code=b["batch_code"],
                    breed=b["breed"],
                    incubator_id=b["incubator_id"],
                    initial_egg_count=b["initial_egg_count"],
                    set_date=b["set_date"],
                    target_hatch_date=b["target_hatch_date"],
                    current_stage=b["current_stage"],
                    status=b["status"],
                    hatched_count=b.get("hatched_count", 0),
                    unhatched_count=b.get("unhatched_count", 0),
                    notes=b.get("notes"),
                    created_by=admin.user_id if admin else None
                )
                db.add(batch_obj)
                print(f"  + Created Batch: {b['batch_id']}")

        db.commit()

        # ----------------------------------------------------------------------
        # 4. Seed Candling Sessions & Egg Scans
        # ----------------------------------------------------------------------
        print("\n[4/5] Seeding Candling Sessions & Conveyor Egg Scans...")

        # Session for BATCH-2026-08-KAY-01 (Day 10 - 500 eggs)
        sess_1 = db.query(CandlingSessionModel).filter(CandlingSessionModel.batch_id == "BATCH-2026-08-KAY-01").first()
        if not sess_1:
            sess_1_id = uuid.uuid4()
            sess_1 = CandlingSessionModel(
                session_id=sess_1_id,
                batch_id="BATCH-2026-08-KAY-01",
                device_id="STATION-01-RP5",
                stage=CandlingStage.DAY_10,
                operator_name="Pedro Penduko",
                started_at=now - timedelta(hours=3),
                ended_at=now - timedelta(hours=2, minutes=15)
            )
            db.add(sess_1)
            db.commit()

            print("  + Generating 500 conveyor scans for BATCH-2026-08-KAY-01 (Day 10)...")
            scans_to_add = []
            f_cnt, inf_cnt, ab_cnt = 0, 0, 0

            for seq in range(1, 501):
                # 88.6% Fertile, 8.4% Infertile, 3.0% Abnormal
                rand = random.random()
                if rand < 0.886:
                    cls = FertilityClass.FERTILE
                    action = RoutingAction.ACCEPT
                    conf = round(random.uniform(0.88, 0.98), 4)
                    f_cnt += 1
                elif rand < 0.970:
                    cls = FertilityClass.INFERTILE
                    action = RoutingAction.REJECT
                    conf = round(random.uniform(0.85, 0.96), 4)
                    inf_cnt += 1
                else:
                    cls = FertilityClass.ABNORMAL
                    action = RoutingAction.REJECT
                    conf = round(random.uniform(0.82, 0.94), 4)
                    ab_cnt += 1

                lat = random.randint(22, 38)
                scan_time = sess_1.started_at + timedelta(seconds=seq * 6)

                scans_to_add.append(EggScanModel(
                    scan_id=uuid.uuid4(),
                    session_id=sess_1_id,
                    batch_id="BATCH-2026-08-KAY-01",
                    sequence_number=seq,
                    final_class=cls,
                    confidence=conf,
                    inference_ms=lat,
                    routing_action=action,
                    detections=[{
                        "bbox": [0.50, 0.50, 0.42, 0.58],
                        "class": cls.value,
                        "confidence": conf
                    }],
                    scanned_at=scan_time
                ))

            db.bulk_save_objects(scans_to_add)
            sess_1.total_scanned = 500
            sess_1.fertile_count = f_cnt
            sess_1.infertile_count = inf_cnt
            sess_1.abnormal_count = ab_cnt
            sess_1.avg_inference_ms = 28.50
            db.commit()
            print(f"    [OK] 500 scans recorded: {f_cnt} Fertile, {inf_cnt} Infertile, {ab_cnt} Abnormal.")

        # ----------------------------------------------------------------------
        # 5. Audit Log Seed
        # ----------------------------------------------------------------------
        print("\n[5/5] Seeding Audit Logs...")
        log = AuditLogModel(
            user_id=admin.user_id if admin else None,
            action="SYSTEM_INITIALIZED",
            entity_type="SYSTEM",
            entity_id="OVALENS-CORE",
            details={"version": "2.0.0", "message": "Standalone OvaLens Capstone System Initialized."},
            ip_address="127.0.0.1"
        )
        db.add(log)
        db.commit()

        print("\n[SUCCESS] OvaLens Database Seeding Successfully Completed!")
        print("-------------------------------------------------------------")
        print("  Admin Credentials:    admin@ovalens.fu.edu.ph    / Admin@123")
        print("  Manager Credentials:  manager@ovalens.fu.edu.ph  / Manager@123")
        print("  Operator Credentials: operator@ovalens.fu.edu.ph / Operator@123")
        print("  Active Edge Station:  STATION-01-RP5")
        print("-------------------------------------------------------------\n")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OvaLens Database Seeder")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables before seeding")
    args = parser.parse_args()
    seed_database(reset=args.reset)