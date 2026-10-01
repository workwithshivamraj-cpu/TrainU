"""Seed the demo data described in docs/plan.md and the product spec:

- Portfolio Team organization with a full set of demo users (one per role).
- Two applications (ClientVantage, SupplyLine) with modules/features.
- Approved, indexed KT videos and a policy document with realistic
  creation/update-workflow transcripts, run through the *real* ingestion
  pipeline (mock STT + mock/real embeddings) so seeded data exercises the
  exact same code path as a live upload.
- A short synthetic placeholder video (generated with ffmpeg) uploaded to
  object storage for each video source. Set TRAINU_DEMO_VIDEO to an existing
  MP4 or MOV to use a supplied file instead. Demo transcripts are scripted;
  mock mode does not perform speech recognition.

Run with:  python -m scripts.seed   (from backend/, with the venv active and
DATABASE_URL / S3_* / etc. pointed at the local stack).
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slugify import slugify
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.application import Application, ApplicationModule
from app.models.enums import RoleName, SourceStatus, SourceType
from app.models.organization import Membership, Organization, OrganizationPlan
from app.models.source import Source
from app.models.user import User
from app.services.pipeline import index_approved_source, run_pipeline
from app.services.storage import build_storage_key, ensure_bucket, upload_bytes

DEMO_PASSWORD = "TrainU_Demo123!"


def log(msg: str) -> None:
    print(f"[seed] {msg}")


def make_placeholder_video(seconds: int = 240) -> tuple[bytes, str, str]:
    demo_video = os.environ.get("TRAINU_DEMO_VIDEO")
    if demo_video:
        path = Path(demo_video).expanduser()
        extension = path.suffix.lower()
        if extension not in {".mp4", ".mov"} or not path.is_file():
            raise ValueError("TRAINU_DEMO_VIDEO must point to an existing .mp4 or .mov file")
        content_type = "video/quicktime" if extension == ".mov" else "video/mp4"
        log(f"Using supplied demo video: {path.name}")
        return path.read_bytes(), extension, content_type

    with tempfile.TemporaryDirectory() as tmp:
        out = f"{tmp}/placeholder.mp4"
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=640x360:rate=2",
                "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out,
            ],
            check=True,
            capture_output=True,
        )
        return Path(out).read_bytes(), ".mp4", "video/mp4"


def get_or_create_user(db: Session, email: str, full_name: str, *, is_platform_admin: bool = False) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(DEMO_PASSWORD),
        is_platform_admin=is_platform_admin,
    )
    db.add(user)
    db.flush()
    return user


def add_membership(db: Session, user: User, org: Organization, role: RoleName) -> None:
    existing = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.organization_id == org.id)
        .first()
    )
    if existing:
        existing.role = role.value
        return
    db.add(Membership(user_id=user.id, organization_id=org.id, role=role.value))


VIDEO_TRANSCRIPTS = {
    "clientvantage_create": (
        "Welcome to this ClientVantage training video on creating a new client account. "
        "To create a new client account, first log in to ClientVantage and navigate to the Clients menu. "
        "Next, click the New Client Account button in the top right corner. "
        "Enter the client's legal name, primary contact email, and account tier in the required fields. "
        "Select the onboarding template that matches the client's industry from the template dropdown. "
        "Click Save Draft to store the account before submission. "
        "Review the details on the summary screen, then click Submit for Approval to send it to a Client Success Lead. "
        "Once approved, the account status automatically changes from Draft to Active. "
        "Any Contributor can create a client account, but only a Client Success Lead can approve it. "
        "That completes the walkthrough for creating a new client account in ClientVantage."
    ),
    "clientvantage_status": (
        "This video covers how to update the status of an existing client account in ClientVantage. "
        "To update the status, open the client account from the Clients list and click the Edit Status button. "
        "Choose the new status from the dropdown: Pending, Active, Suspended, or Closed. "
        "If you are changing the status to Closed, you must provide a closure reason in the notes field. "
        "Click Save Changes to apply the update. "
        "Status changes to Closed or Suspended require approval from a Client Success Lead before they take effect. "
        "A Contributor can request the status change, but only the Client Success Lead role can give final approval. "
        "The audit log records every status change with the user, timestamp, and reason. "
        "This concludes the walkthrough for updating a client account status."
    ),
    "supplyline_create": (
        "Welcome to the SupplyLine training on creating a new purchase order. "
        "To create a purchase order, go to the Purchase Orders tab and click New Purchase Order. "
        "Select the vendor from the vendor directory, or add a new vendor if needed. "
        "Add line items including item description, quantity, and unit price for each product you are ordering. "
        "Choose a delivery location and requested delivery date. "
        "Click Submit for Review to send the purchase order to a Procurement Approver. "
        "The purchase order status starts as Draft, moves to Pending Approval, and becomes Approved once a Procurement Approver signs off. "
        "Only users with the Procurement Approver role can approve purchase orders over five thousand dollars. "
        "This completes the walkthrough for creating a purchase order in SupplyLine."
    ),
    "supplyline_status": (
        "This video explains how to approve and update the status of a purchase order in SupplyLine. "
        "Open the purchase order from the Pending Approvals queue. "
        "Review the vendor, line items, and total cost against the budget. "
        "To approve, click Approve Purchase Order, which moves the status from Pending Approval to Approved. "
        "To reject, click Reject and provide a reason, which moves the status to Rejected and notifies the requester. "
        "Once goods are received, update the status to Received by clicking Mark as Received on the Receiving tab. "
        "Only the Procurement Approver or Supply Chain Systems admin role can approve or reject a purchase order. "
        "This concludes the walkthrough on approving and updating purchase order status."
    ),
}

POLICY_DOCUMENT = """# ClientVantage Approval Policy

## Purpose
This document defines which roles can approve key actions in ClientVantage.

## Client account creation
Any Contributor or Content Owner may create a new client account in Draft
status. No approval is required to save a draft.

## Client account approval
Submitting a client account for approval routes it to a Client Success
Lead. Only the Client Success Lead role can move an account from Pending
Approval to Active.

## Status changes
Changing a client account status to Suspended or Closed always requires
Client Success Lead approval. Reopening a Closed account requires Org Admin
approval in addition to a Client Success Lead sign-off.

## Audit
Every approval, rejection, and status change is recorded in the audit log
with the acting user, timestamp, and reason.
"""


def create_source_with_video(
    db: Session,
    *,
    org: Organization,
    application: Application,
    module: ApplicationModule | None,
    owner: User,
    title: str,
    description: str,
    feature_tag: str,
    transcript_key: str,
    audience_roles: list[str],
    placeholder_video: bytes,
    video_extension: str = ".mp4",
    video_mime_type: str = "video/mp4",
) -> Source:
    source_video = os.environ.get(f"TRAINU_DEMO_VIDEO_{transcript_key.upper()}")
    if source_video:
        path = Path(source_video).expanduser()
        video_extension = path.suffix.lower()
        if video_extension not in {".mp4", ".mov"} or not path.is_file():
            raise ValueError(
                f"TRAINU_DEMO_VIDEO_{transcript_key.upper()} must point to an existing .mp4 or .mov file"
            )
        placeholder_video = path.read_bytes()
        video_mime_type = "video/quicktime" if video_extension == ".mov" else "video/mp4"
        log(f"Using source-specific demo video for {transcript_key}: {path.name}")

    source = Source(
        organization_id=org.id,
        application_id=application.id,
        module_id=module.id if module else None,
        content_owner_id=owner.id,
        title=title,
        description=description,
        source_type=SourceType.VIDEO.value,
        status=SourceStatus.UPLOADED.value,
        feature_tag=feature_tag,
        application_version=application.version,
        environment=application.environment,
        audience_roles=audience_roles,
        storage_key="",
        original_filename=f"{slugify(title)}{video_extension}",
        file_size_bytes=len(placeholder_video),
        mime_type=video_mime_type,
    )
    db.add(source)
    db.flush()

    key = build_storage_key(str(org.id), str(source.id), source.original_filename)
    upload_bytes(key, placeholder_video, "video/mp4")
    source.storage_key = key
    db.commit()

    run_pipeline(db, source, seed_transcript_text=VIDEO_TRANSCRIPTS[transcript_key])
    db.refresh(source)

    source.status = SourceStatus.APPROVED.value
    source.approved_by_id = owner.id
    from datetime import datetime, timezone

    source.approved_at = datetime.now(timezone.utc)
    db.commit()
    from app.services.source_state import sync_chunk_status

    sync_chunk_status(db, source)
    index_approved_source(db, source)
    db.refresh(source)
    log(f"Seeded video source '{title}' -> status={source.status}, chunks={len(source.chunks)}")
    return source


def create_document_source(
    db: Session,
    *,
    org: Organization,
    application: Application,
    owner: User,
    title: str,
    description: str,
    text: str,
    audience_roles: list[str],
) -> Source:
    data = text.encode("utf-8")
    source = Source(
        organization_id=org.id,
        application_id=application.id,
        content_owner_id=owner.id,
        title=title,
        description=description,
        source_type=SourceType.MARKDOWN.value,
        status=SourceStatus.UPLOADED.value,
        feature_tag="approval-policy",
        application_version=application.version,
        environment=application.environment,
        audience_roles=audience_roles,
        storage_key="",
        original_filename=f"{slugify(title)}.md",
        file_size_bytes=len(data),
        mime_type="text/markdown",
    )
    db.add(source)
    db.flush()

    key = build_storage_key(str(org.id), str(source.id), source.original_filename)
    upload_bytes(key, data, "text/markdown")
    source.storage_key = key
    db.commit()

    run_pipeline(db, source)
    db.refresh(source)

    source.status = SourceStatus.APPROVED.value
    source.approved_by_id = owner.id
    from datetime import datetime, timezone

    source.approved_at = datetime.now(timezone.utc)
    db.commit()
    from app.services.source_state import sync_chunk_status

    sync_chunk_status(db, source)
    index_approved_source(db, source)
    db.refresh(source)
    log(f"Seeded document source '{title}' -> status={source.status}, chunks={len(source.chunks)}")
    return source


def main() -> None:
    Base.metadata.create_all(bind=engine)  # no-op if migrations already ran; safety net
    ensure_bucket()
    db = SessionLocal()
    try:
        org = db.query(Organization).filter(Organization.slug == "portfolio-team").first()
        if org is None:
            org = Organization(name="Portfolio Team", slug="portfolio-team", retention_days=365)
            db.add(org)
            db.flush()
            db.add(OrganizationPlan(organization_id=org.id, plan_name="demo", is_trial=True))
            log("Created organization 'Portfolio Team'")
        else:
            log("Organization 'Portfolio Team' already exists; reusing")

        platform_admin = get_or_create_user(
            db, "platform.admin@trainu.dev", "Priya Admin", is_platform_admin=True
        )
        org_admin = get_or_create_user(db, "admin@portfolioteam.example", "Alex Chen")
        content_owner = get_or_create_user(db, "owner@portfolioteam.example", "Jordan Rivera")
        contributor = get_or_create_user(db, "contributor@portfolioteam.example", "Sam Patel")
        viewer = get_or_create_user(db, "viewer@portfolioteam.example", "Morgan Lee")

        add_membership(db, platform_admin, org, RoleName.ORG_ADMIN)
        add_membership(db, org_admin, org, RoleName.ORG_ADMIN)
        add_membership(db, content_owner, org, RoleName.CONTENT_OWNER)
        add_membership(db, contributor, org, RoleName.CONTRIBUTOR)
        add_membership(db, viewer, org, RoleName.VIEWER)
        db.commit()
        log("Seeded demo users and memberships")

        client_vantage = db.query(Application).filter(
            Application.organization_id == org.id, Application.name == "ClientVantage"
        ).first()
        if client_vantage is None:
            client_vantage = Application(
                organization_id=org.id,
                name="ClientVantage",
                description="Customer relationship and onboarding platform used by the Client Success org to manage client accounts end to end.",
                version="3.4.1",
                environment="production",
                owning_team="Customer Platform Engineering",
                support_contact="client-platform-support@portfolioteam.example",
                status="active",
                features=["Client record creation", "Status workflow", "Approval routing", "Document attachments"],
            )
            db.add(client_vantage)
            db.flush()
            db.add(ApplicationModule(
                organization_id=org.id, application_id=client_vantage.id, name="Client Accounts",
                description="Core client record management.", features=["Create", "Edit", "Status workflow"],
            ))
            db.add(ApplicationModule(
                organization_id=org.id, application_id=client_vantage.id, name="Approvals",
                description="Approval routing and audit trail.", features=["Approve", "Reject", "Audit log"],
            ))
            db.commit()
            log("Created application 'ClientVantage'")

        supply_line = db.query(Application).filter(
            Application.organization_id == org.id, Application.name == "SupplyLine"
        ).first()
        if supply_line is None:
            supply_line = Application(
                organization_id=org.id,
                name="SupplyLine",
                description="Internal procurement and supply chain system for creating and approving purchase orders.",
                version="2.1.0",
                environment="production",
                owning_team="Supply Chain Systems",
                support_contact="supply-chain-support@portfolioteam.example",
                status="active",
                features=["Purchase order creation", "Vendor management", "Approval workflow", "Receiving"],
            )
            db.add(supply_line)
            db.flush()
            db.add(ApplicationModule(
                organization_id=org.id, application_id=supply_line.id, name="Purchase Orders",
                description="Create and track purchase orders.", features=["Create", "Submit", "Track status"],
            ))
            db.add(ApplicationModule(
                organization_id=org.id, application_id=supply_line.id, name="Receiving",
                description="Record receipt of ordered goods.", features=["Mark received", "Discrepancy notes"],
            ))
            db.commit()
            log("Created application 'SupplyLine'")

        existing_sources = db.query(Source).filter(Source.organization_id == org.id).count()
        if existing_sources > 0:
            log(f"{existing_sources} sources already exist; skipping source seeding")
        else:
            log("Generating placeholder training video (ffmpeg)...")
            placeholder_video, video_extension, video_mime_type = make_placeholder_video(seconds=240)

            client_accounts_module = db.query(ApplicationModule).filter(
                ApplicationModule.application_id == client_vantage.id,
                ApplicationModule.name == "Client Accounts",
            ).first()
            create_source_with_video(
                db, org=org, application=client_vantage, module=client_accounts_module, owner=content_owner,
                title="ClientVantage KT — Creating a New Client Account",
                description="Step-by-step walkthrough of creating and submitting a new client account.",
                feature_tag="client-account-creation", transcript_key="clientvantage_create",
                audience_roles=["contributor", "content_owner"], placeholder_video=placeholder_video,
                video_extension=video_extension, video_mime_type=video_mime_type,
            )
            create_source_with_video(
                db, org=org, application=client_vantage, module=client_accounts_module, owner=content_owner,
                title="ClientVantage KT — Updating Client Account Status",
                description="How to change a client account's status and who must approve it.",
                feature_tag="client-account-status", transcript_key="clientvantage_status",
                audience_roles=["contributor", "content_owner", "viewer"], placeholder_video=placeholder_video,
                video_extension=video_extension, video_mime_type=video_mime_type,
            )
            create_document_source(
                db, org=org, application=client_vantage, owner=content_owner,
                title="ClientVantage Approval Policy",
                description="Policy document describing which roles may approve client account actions.",
                text=POLICY_DOCUMENT, audience_roles=["contributor", "content_owner", "viewer", "org_admin"],
            )

            po_module = db.query(ApplicationModule).filter(
                ApplicationModule.application_id == supply_line.id,
                ApplicationModule.name == "Purchase Orders",
            ).first()
            create_source_with_video(
                db, org=org, application=supply_line, module=po_module, owner=content_owner,
                title="SupplyLine KT — Creating a Purchase Order",
                description="Step-by-step walkthrough of creating and submitting a purchase order.",
                feature_tag="po-creation", transcript_key="supplyline_create",
                audience_roles=["contributor", "content_owner"], placeholder_video=placeholder_video,
                video_extension=video_extension, video_mime_type=video_mime_type,
            )
            create_source_with_video(
                db, org=org, application=supply_line, module=po_module, owner=content_owner,
                title="SupplyLine KT — Approving and Updating Purchase Order Status",
                description="How to approve, reject, or receive a purchase order.",
                feature_tag="po-approval", transcript_key="supplyline_status",
                audience_roles=["contributor", "content_owner", "viewer"], placeholder_video=placeholder_video,
                video_extension=video_extension, video_mime_type=video_mime_type,
            )

        log("")
        log("=== Demo credentials (all use password: %s) ===" % DEMO_PASSWORD)
        log("  platform.admin@trainu.dev   (platform admin + org admin)")
        log("  admin@portfolioteam.example (org admin)")
        log("  owner@portfolioteam.example (content owner)")
        log("  contributor@portfolioteam.example (contributor)")
        log("  viewer@portfolioteam.example (viewer)")
        log("")
        log("Example questions to try in the Ask TrainU assistant:")
        log("  - How do I create a new client account in ClientVantage?")
        log("  - How do I update the status of a client account?")
        log("  - Which role can approve a client account status change?")
        log("  - How do I create a purchase order in SupplyLine?")
        log("  - Who can approve a purchase order?")
        log("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
