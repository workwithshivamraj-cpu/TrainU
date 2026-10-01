"""Create four polished local motion-graphic training videos and attach them to demo sources."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "demo-videos"
OUT.mkdir(parents=True, exist_ok=True)

from scripts.seed import VIDEO_TRANSCRIPTS  # noqa: E402

SPECS = [
    {
        "key": "clientvantage_create",
        "title": "ClientVantage KT — Creating a New Client Account",
        "application": "ClientVantage",
        "accent": "#18A88B",
        "steps": [
            ("Open Clients", "Start from the Clients workspace and review the existing account list.", "FIND THE RIGHT WORKSPACE"),
            ("Start a new account", "Choose New Client Account to open the guided account form.", "CREATE A CLEAN RECORD"),
            ("Enter client details", "Add the legal name, primary contact email, and account tier.", "COMPLETE REQUIRED FIELDS"),
            ("Choose a template", "Match the onboarding template to the client’s industry.", "MAKE ONBOARDING RELEVANT"),
            ("Save a draft", "Save first so the details can be checked before submission.", "KEEP WORK IN PROGRESS SAFE"),
            ("Review and submit", "Confirm the summary, then send it to a Client Success Lead.", "HAND OFF FOR APPROVAL"),
            ("Activate the account", "After approval, the account moves from Draft to Active.", "APPROVAL UNLOCKS THE NEXT STEP"),
        ],
    },
    {
        "key": "clientvantage_status",
        "title": "ClientVantage KT — Updating Client Account Status",
        "application": "ClientVantage",
        "accent": "#18A88B",
        "steps": [
            ("Find the client", "Open the account from the Clients list before changing its state.", "START WITH THE ACCOUNT"),
            ("Edit status", "Select Edit Status to review the available account states.", "OPEN THE CONTROL"),
            ("Choose a status", "Set Pending, Active, Suspended, or Closed as needed.", "SELECT THE RIGHT STATE"),
            ("Add a closure reason", "A Closed account needs a clear reason in the notes field.", "MAKE THE CHANGE TRACEABLE"),
            ("Save changes", "Apply the update and confirm the new state on the account.", "COMMIT THE REQUEST"),
            ("Request approval", "Suspended and Closed changes wait for a Client Success Lead.", "SENSITIVE CHANGES NEED REVIEW"),
            ("Check the audit log", "Every change records who acted, when, and why.", "KEEP A CLEAR HISTORY"),
        ],
    },
    {
        "key": "supplyline_create",
        "title": "SupplyLine KT — Creating a Purchase Order",
        "application": "SupplyLine",
        "accent": "#6176D9",
        "steps": [
            ("Open Purchase Orders", "Start from the Purchase Orders tab in SupplyLine.", "OPEN THE PROCUREMENT FLOW"),
            ("Create a new PO", "Choose New Purchase Order to begin a draft.", "START WITH A DRAFT"),
            ("Select a vendor", "Use the vendor directory or add a new approved vendor.", "LINK THE SUPPLIER"),
            ("Add line items", "Enter each item description, quantity, and unit price.", "MAKE THE TOTAL CLEAR"),
            ("Set delivery details", "Choose the destination and requested delivery date.", "PLAN THE ARRIVAL"),
            ("Submit for review", "Send the purchase order to a Procurement Approver.", "ROUTE IT TO REVIEW"),
            ("Wait for approval", "The status moves from Draft to Pending Approval, then Approved.", "FOLLOW THE APPROVAL STATE"),
        ],
    },
    {
        "key": "supplyline_status",
        "title": "SupplyLine KT — Approving and Updating Purchase Order Status",
        "application": "SupplyLine",
        "accent": "#6176D9",
        "steps": [
            ("Open pending approvals", "Choose a purchase order from the review queue.", "START IN THE RIGHT QUEUE"),
            ("Review the order", "Check vendor, line items, and total against the budget.", "VERIFY BEFORE YOU DECIDE"),
            ("Approve or reject", "Approve to proceed, or reject with a reason for the requester.", "MAKE THE DECISION CLEAR"),
            ("Record the outcome", "An approval moves the order to Approved; a rejection is recorded.", "KEEP STATUS ACCURATE"),
            ("Receive the goods", "When items arrive, open the Receiving tab.", "CLOSE THE LOOP"),
            ("Mark as Received", "Update the status after receipt is confirmed.", "COMPLETE THE ORDER"),
            ("Respect role controls", "Procurement Approvers or Supply Chain Systems admins can decide.", "THE RIGHT ROLE TAKES ACTION"),
        ],
    },
]


def main() -> None:
    clips = []
    for spec in SPECS:
        audio = OUT / f"{spec['key']}-voice.aiff"
        output = OUT / f"{spec['key']}.mp4"
        subprocess.run(
            # The slower narration leaves room for the existing transcript citations to
            # stay within each clip instead of seeking past the final frame.
            ["say", "-v", "Samantha", "-r", "100", "-o", str(audio), VIDEO_TRANSCRIPTS[spec["key"]]],
            check=True,
        )
        clips.append({
            "title": spec["title"],
            "application": spec["application"],
            "accent": spec["accent"],
            "steps": [dict(title=a, detail=b, tag=c) for a, b, c in spec["steps"]],
            "audio": str(audio),
            "output": str(output),
        })
    manifest = OUT / "render-manifest.json"
    manifest.write_text(json.dumps({"clips": clips}, indent=2), encoding="utf-8")
    subprocess.run(["swift", str(ROOT / "scripts" / "render_demo_motion.swift"), str(manifest)], check=True)

    results = json.loads((OUT / "render-results.json").read_text(encoding="utf-8"))
    # Replace the seeded placeholder objects in the local demo bucket while keeping their
    # source IDs, transcripts, permissions, and citation links stable.
    from app.db.session import SessionLocal
    from app.models.source import Source, TranscriptChunk
    from app.services.storage import build_storage_key, delete_object, upload_bytes

    with SessionLocal() as db:
        replaced_keys = []
        for spec, result in zip(SPECS, results, strict=True):
            source = db.query(Source).filter(Source.title == spec["title"]).one()
            video = Path(result["output"]).read_bytes()
            old_key = source.storage_key
            filename = f"{spec['key'].replace('_', '-')}.mp4"
            new_key = build_storage_key(str(source.organization_id), str(source.id), filename)
            upload_bytes(new_key, video, "video/mp4")
            source.storage_key = new_key
            source.original_filename = filename
            source.file_size_bytes = len(video)
            source.mime_type = "video/mp4"
            source.duration_seconds = float(result["duration_seconds"])
            chunks = (
                db.query(TranscriptChunk)
                .filter(TranscriptChunk.source_id == source.id)
                .order_by(TranscriptChunk.start_seconds, TranscriptChunk.id)
                .all()
            )
            word_counts = [max(1, len(chunk.text.split())) for chunk in chunks]
            total_words = sum(word_counts)
            cursor = 0.0
            for i, (chunk, words) in enumerate(zip(chunks, word_counts, strict=True)):
                chunk.start_seconds = cursor
                cursor = (
                    source.duration_seconds
                    if i == len(chunks) - 1
                    else cursor + source.duration_seconds * words / total_words
                )
                chunk.end_seconds = cursor
            print(f"Attached {source.title} ({len(video) / 1_000_000:.1f} MB, {source.duration_seconds:.1f}s)")
            replaced_keys.append(old_key)
        db.commit()
        for old_key in replaced_keys:
            delete_object(old_key)

    print(f"Videos and voice tracks are in {OUT}")


if __name__ == "__main__":
    main()
