"""
Test script for diagnosing WhatsApp template sync issues.
Run from project root:  python scripts/test_template_sync.py
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import inspect
import traceback


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def ok(msg: str):
    print(f"  [OK]   {msg}")


def fail(msg: str):
    print(f"  [FAIL] {msg}")


def warn(msg: str):
    print(f"  [WARN] {msg}")


def info(msg: str):
    print(f"  [INFO] {msg}")


# ── Step 1: Check PyWa installation ──

section("1. PyWa Library Check")
try:
    import pywa
    ok(f"pywa installed — version {pywa.__version__}")
except ImportError:
    fail("pywa is NOT installed. Run: pip install pywa")
    sys.exit(1)

from pywa import WhatsApp

# ── Step 2: Check configuration ──

section("2. Configuration Check")
from app.config import settings

checks = {
    "WHATSAPP_PHONE_NUMBER_ID": settings.WHATSAPP_PHONE_NUMBER_ID,
    "WHATSAPP_ACCESS_TOKEN": settings.WHATSAPP_ACCESS_TOKEN,
    "WHATSAPP_BUSINESS_ACCOUNT_ID": settings.WHATSAPP_BUSINESS_ACCOUNT_ID,
}

all_configured = True
for key, val in checks.items():
    if val:
        display = val[:15] + "..." if len(val) > 15 else val
        ok(f"{key} = {display}")
    else:
        fail(f"{key} is EMPTY — set it in .env")
        all_configured = False

if not all_configured:
    fail("Missing required WhatsApp credentials. Fix .env and retry.")
    sys.exit(1)


# ── Step 3: Create WhatsApp client ──

section("3. WhatsApp Client Initialization")
try:
    client = WhatsApp(
        phone_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        token=settings.WHATSAPP_ACCESS_TOKEN,
        business_account_id=settings.WHATSAPP_BUSINESS_ACCOUNT_ID,
    )
    ok("WhatsApp client created successfully")
except Exception as e:
    fail(f"Failed to create client: {e}")
    sys.exit(1)

# Check method availability
has_get_templates = hasattr(client, "get_templates")
is_async = inspect.iscoroutinefunction(client.get_templates) if has_get_templates else None

if has_get_templates:
    ok(f"client.get_templates exists (async={is_async})")
else:
    fail("client.get_templates NOT found — PyWa version too old?")
    sys.exit(1)

if is_async:
    info("get_templates is ASYNC — must use 'await' in async context")
else:
    warn("get_templates is SYNC — code using 'await' on it will FAIL silently!")
    info("This is likely the root cause of the sync problem.")


# ── Step 4: Call get_templates directly (sync) ──

section("4. Fetching Templates from Meta (direct call)")
try:
    if is_async:
        import asyncio
        raw_templates = asyncio.run(client.get_templates())
    else:
        raw_templates = client.get_templates()

    info(f"Return type: {type(raw_templates).__name__}")

    # TemplatesResult may be iterable
    templates_list = list(raw_templates) if raw_templates else []
    ok(f"Retrieved {len(templates_list)} templates from Meta")

    if not templates_list:
        warn("Meta returned 0 templates. Check:")
        warn("  - Is the WABA ID correct?")
        warn("  - Does the Business Account have any templates?")
        warn("  - Is the access token valid and has the right permissions?")
except Exception as e:
    fail(f"Error fetching templates: {e}")
    traceback.print_exc()
    templates_list = []


# ── Step 5: Inspect template objects ──

if templates_list:
    section("5. Template Object Inspection")
    first = templates_list[0]
    info(f"Object type: {type(first).__name__}")
    info(f"Available attributes: {[a for a in dir(first) if not a.startswith('_')]}")

    for i, t in enumerate(templates_list[:10]):
        name = getattr(t, "name", "?")
        status = getattr(t, "status", "?")
        category = getattr(t, "category", "?")
        language = getattr(t, "language", "?")
        tid = getattr(t, "id", "?")

        # Handle enum values
        if hasattr(status, "value"):
            status = status.value
        if hasattr(category, "value"):
            category = category.value
        if hasattr(language, "value"):
            language = language.value

        print(f"\n  Template #{i+1}:")
        print(f"    name     = {name}")
        print(f"    id       = {tid}")
        print(f"    status   = {status}")
        print(f"    category = {category}")
        print(f"    language = {language}")

        # Show components
        components = getattr(t, "components", [])
        if components:
            for comp in components:
                comp_type = getattr(comp, "type", None)
                if hasattr(comp_type, "value"):
                    comp_type = comp_type.value
                comp_text = getattr(comp, "text", None)
                print(f"    component: type={comp_type}, text={comp_text[:60] if comp_text else None}...")
        else:
            print("    components: (none)")

    if len(templates_list) > 10:
        info(f"... and {len(templates_list) - 10} more templates (showing first 10)")


# ── Step 6: Test serialization ──

if templates_list:
    section("6. Serialization Test")
    from app.services.whatsapp_service import _serialize_template

    try:
        serialized = _serialize_template(templates_list[0])
        ok(f"Serialized first template: {serialized.get('name')}")
        for key, val in serialized.items():
            display = str(val)[:80] if val else "None"
            print(f"    {key}: {display}")
    except Exception as e:
        fail(f"Serialization failed: {e}")
        traceback.print_exc()


# ── Step 7: Test language mapping ──

if templates_list:
    section("7. Language Mapping Test")
    from app.services.template_service import _map_wa_language

    for t in templates_list:
        lang = getattr(t, "language", None)
        if hasattr(lang, "value"):
            lang = lang.value

        mapped = _map_wa_language(str(lang)) if lang else None
        status_icon = "[OK]  " if mapped else "[SKIP]"
        print(f"  {status_icon} WhatsApp '{lang}' -> Local {mapped}")


# ── Step 8: Test the WhatsAppService singleton ──

section("8. WhatsAppService Singleton Check")
from app.services.whatsapp_service import whatsapp_service

info(f"is_configured: {whatsapp_service.is_configured}")
info(f"_client type: {type(whatsapp_service._client).__name__ if whatsapp_service._client else 'None'}")

if whatsapp_service.is_configured:
    has_method = hasattr(whatsapp_service._client, "get_templates")
    is_sync = not inspect.iscoroutinefunction(whatsapp_service._client.get_templates) if has_method else None
    info(f"_client.get_templates exists: {has_method}")
    if is_sync:
        warn("_client.get_templates is SYNC but code uses 'await' — this is the bug!")
else:
    warn("WhatsAppService is NOT configured — sync will return empty list")


# ── Step 9: Test the actual sync endpoint ──

section("9. Testing TemplateService.sync_templates_from_whatsapp()")
try:
    import asyncio
    from app.database import SessionLocal
    from app.services.template_service import TemplateService

    db = SessionLocal()
    svc = TemplateService(db)

    result = asyncio.run(svc.sync_templates_from_whatsapp())
    print(f"\n  Sync Result:")
    for key, val in result.items():
        print(f"    {key}: {val}")

    if result.get("success"):
        ok(f"Sync completed: created={result.get('created')}, updated={result.get('updated')}, skipped={result.get('skipped')}")
    else:
        fail(f"Sync failed: {result.get('error')}")

    db.close()
except Exception as e:
    fail(f"Sync test exception: {e}")
    traceback.print_exc()


# ── Step 10: Check DB after sync ──

section("10. Database Check After Sync")
try:
    from app.database import SessionLocal
    from app.models.template import Template, TemplateTranslation

    db = SessionLocal()
    templates = db.query(Template).all()
    translations = db.query(TemplateTranslation).all()

    info(f"Templates in DB: {len(templates)}")
    info(f"Translations in DB: {len(translations)}")

    for t in templates:
        trans_info = ", ".join(
            f"{tr.language.value}({tr.approval_status})" for tr in t.translations
        )
        print(f"    [{t.id}] {t.template_name} | {t.category} | translations: {trans_info}")

    db.close()
except Exception as e:
    fail(f"DB check failed: {e}")
    traceback.print_exc()


# ── Summary ──

section("SUMMARY")
if not is_async and has_get_templates:
    print("""
  ROOT CAUSE IDENTIFIED:
  pywa.WhatsApp.get_templates() is SYNCHRONOUS, but
  whatsapp_service.py calls it with 'await'.

  When you 'await' a non-coroutine in Python, it does NOT raise an error —
  it just returns the object as-is. HOWEVER, the real issue may be that
  the sync call is actually working but something else fails downstream.

  FIX: In whatsapp_service.py, change:
      raw_templates = await self._client.get_templates()
  To:
      raw_templates = self._client.get_templates()

  Or wrap it properly for async compatibility.
""")
else:
    print("""
  Review the output above for [FAIL] and [WARN] items.
  Common issues:
  - Empty WABA_ID or wrong Business Account ID
  - Expired or invalid access token
  - No templates created in Meta Business Manager
  - Language code mismatch (e.g. en_US vs en)
""")
