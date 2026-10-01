"""Migration and database seeding script for HireShield-AI.

Migrates assessments and scam reports from local MongoDB to MongoDB Atlas,
and optionally seeds known scam indicators from dataset files.
"""

import asyncio
import json
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient

import os
from dotenv import load_dotenv

load_dotenv()

LOCAL_URI = os.getenv("LOCAL_DATABASE_URL", "mongodb://localhost:27017")
ATLAS_URI = os.getenv("DATABASE_URL", LOCAL_URI)
DB_NAME = os.getenv("DATABASE_NAME", "hireshield")

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
INDIA_SCAMS_JSON = WORKSPACE_ROOT / "ml" / "data" / "raw" / "india_job_scams.json"
MODERN_SCAMS_JSON = WORKSPACE_ROOT / "ml" / "data" / "raw" / "modern_scams_and_startups.json"


async def main():
    print(f"Connecting to Local MongoDB: {LOCAL_URI} ...")
    local_client = AsyncIOMotorClient(LOCAL_URI, serverSelectionTimeoutMS=3000)
    local_db = local_client[DB_NAME]

    print(f"Connecting to MongoDB Atlas: {ATLAS_URI[:35]}... ...")
    atlas_client = AsyncIOMotorClient(ATLAS_URI, serverSelectionTimeoutMS=10000)
    atlas_db = atlas_client[DB_NAME]

    # 1. Migrate assessments
    local_assessments = await local_db.assessments.find().to_list(length=1000)
    print(f"Found {len(local_assessments)} assessments in local MongoDB.")

    if local_assessments:
        atlas_count = await atlas_db.assessments.count_documents({})
        if atlas_count == 0:
            print(f"Migrating {len(local_assessments)} assessments to Atlas...")
            # MongoDB Atlas insert
            await atlas_db.assessments.insert_many(local_assessments)
            print("Assessments successfully migrated to Atlas!")
        else:
            print(f"Atlas already contains {atlas_count} assessments. Skipping assessment migration.")

    # 2. Migrate existing local scam reports
    local_reports = await local_db.scam_reports.find().to_list(length=1000)
    print(f"Found {len(local_reports)} scam reports in local MongoDB.")
    if local_reports:
        for r in local_reports:
            await atlas_db.scam_reports.update_one(
                {"indicator_value": r["indicator_value"]},
                {"$setOnInsert": r},
                upsert=True
            )
        print("Local scam reports synced to Atlas.")

    # 3. Seed additional known fraudulent indicators from dataset
    curated_scam_seeds = [
        {
            "id": "seed-tcs-impersonation-email",
            "indicator_type": "email",
            "indicator_value": "hr-tcs-verification@gmail.com",
            "company_impersonated": "Tata Consultancy Services Ltd",
            "description": "Counterfeit direct campus placement offer demanding refundable laptop insurance fee of Rs 4,850.",
            "loss_amount": 4850.0,
            "reported_at": "2026-09-15T10:00:00Z",
        },
        {
            "id": "seed-wipro-rediffmail",
            "indicator_type": "email",
            "indicator_value": "hr.wipro.recruiting@rediffmail.com",
            "company_impersonated": "Wipro Technologies",
            "description": "Fake joining letter requiring upfront security deposit of Rs 3,500 via rediffmail account.",
            "loss_amount": 3500.0,
            "reported_at": "2026-09-18T14:30:00Z",
        },
        {
            "id": "seed-telegram-task-scam",
            "indicator_type": "telegram",
            "indicator_value": "@digital_task_india",
            "company_impersonated": "Global Digital Media Marketing Partner",
            "description": "YouTube video liking task scam requiring initial recharge payments before freezing funds.",
            "loss_amount": 5000.0,
            "reported_at": "2026-09-20T08:15:00Z",
        },
        {
            "id": "seed-telegram-hr-apex",
            "indicator_type": "telegram",
            "indicator_value": "@apex_hr_onboarding",
            "company_impersonated": "Apex Global Solutions",
            "description": "Cashier check equipment scam directing candidate to buy equipment from a fraudulent vendor.",
            "loss_amount": 2850.0,
            "reported_at": "2026-09-25T11:00:00Z",
        },
        {
            "id": "seed-domain-scam-apextech",
            "indicator_type": "url",
            "indicator_value": "http://apextech-careers.top/apply",
            "company_impersonated": "Apex Technology",
            "description": "Lookalike phishing domain mimicking enterprise careers portal to harvest bank details.",
            "loss_amount": 0.0,
            "reported_at": "2026-09-28T09:00:00Z",
        }
    ]

    for seed in curated_scam_seeds:
        await atlas_db.scam_reports.update_one(
            {"indicator_value": seed["indicator_value"]},
            {"$setOnInsert": seed},
            upsert=True
        )
    print(f"Curated scam blacklist seeds synced to Atlas.")

    # 4. Final summary count on Atlas
    final_assessments = await atlas_db.assessments.count_documents({})
    final_reports = await atlas_db.scam_reports.count_documents({})
    print("\n=== Atlas Database Status ===")
    print(f"Database: '{DB_NAME}'")
    print(f"  - assessments: {final_assessments} documents")
    print(f"  - scam_reports: {final_reports} documents")

    local_client.close()
    atlas_client.close()

if __name__ == "__main__":
    asyncio.run(main())
