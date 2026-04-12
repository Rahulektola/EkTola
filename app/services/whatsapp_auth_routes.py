"""
WhatsApp Embedded Signup Router
Handles Facebook Embedded Signup flow for jewellers to connect their WhatsApp Business Accounts
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta
import httpx
import secrets
import logging
from jose import jwt, JWTError

from app.core.datetime_utils import now_utc
from app.database import get_db
from app.core.dependencies import get_current_user
from app.core.encryption import encrypt_token, decrypt_token
from app.models.user import User
from app.models.jeweller import Jeweller
from app.schemas.auth import (
    WhatsAppConfigResponse,
    WhatsAppCallbackRequest,
    WhatsAppCallbackResponse,
    WhatsAppDisconnectResponse
)
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth/whatsapp", tags=["WhatsApp Authentication"])


# ============ Helper Functions ============

def generate_state_token(jeweller_id: int, user_id: int) -> str:
    """
    Generate signed state token for OAuth flow.
    Contains jeweller_id for security and tracking.
    """
    expiry = now_utc() + timedelta(minutes=10)
    payload = {
        "jeweller_id": jeweller_id,
        "user_id": user_id,
        "exp": expiry,
        "nonce": secrets.token_urlsafe(32)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def validate_state_token(state: str) -> dict:
    """
    Validate and decode state token.
    Returns payload if valid, raises HTTPException otherwise.
    """
    try:
        payload = jwt.decode(state, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Invalid state token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token"
        )


async def exchange_code_for_token(code: str) -> dict:
    """
    Exchange authorization code for access token via Meta Graph API.
    Returns token data including access_token and expires_in.
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/oauth/access_token"
    params = {
        "client_id": settings.WHATSAPP_APP_ID,
        "client_secret": settings.WHATSAPP_APP_SECRET,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to exchange authorization code: {str(e)}"
            )


async def get_long_lived_token(short_lived_token: str) -> dict:
    """
    Exchange short-lived token for long-lived token (60 days).
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": settings.WHATSAPP_APP_ID,
        "client_secret": settings.WHATSAPP_APP_SECRET,
        "fb_exchange_token": short_lived_token
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Long-lived token exchange failed: {str(e)}")
            return {"access_token": short_lived_token, "expires_in": 3600}


async def get_token_info(access_token: str) -> dict:
    """
    Debug access token to get WABA ID and user info.
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/debug_token"
    params = {
        "input_token": access_token,
        "access_token": f"{settings.WHATSAPP_APP_ID}|{settings.WHATSAPP_APP_SECRET}"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})
        except httpx.HTTPError as e:
            logger.error(f"Token debug failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to validate token: {str(e)}"
            )


async def get_waba_details(waba_id: str, access_token: str) -> dict:
    """
    Get WhatsApp Business Account details.
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{waba_id}"
    params = {
        "fields": "id,name,timezone_id,message_template_namespace,account_review_status",
        "access_token": access_token
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"WABA details fetch failed: {str(e)}")
            return {}


async def get_phone_numbers(waba_id: str, access_token: str) -> list:
    """
    Get phone numbers associated with WABA.
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{waba_id}/phone_numbers"
    params = {
        "access_token": access_token
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except httpx.HTTPError as e:
            logger.error(f"Phone numbers fetch failed: {str(e)}")
            return []


async def subscribe_waba_to_webhook(waba_id: str, access_token: str) -> bool:
    """
    Subscribe WABA to platform webhooks.
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{waba_id}/subscribed_apps"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url,
                params={"access_token": access_token},
                timeout=30.0
            )
            response.raise_for_status()
            return True
        except httpx.HTTPError as e:
            logger.error(f"Webhook subscription failed: {str(e)}")
            return False


async def notify_admin_whatsapp_connected(jeweller_id: int, db: Session):
    """
    Send notification to admins that jeweller connected WhatsApp.
    Uses platform WhatsApp account.
    """
    try:
        from app.services.whatsapp_service import send_admin_notification
        await send_admin_notification(jeweller_id, "whatsapp_connected", db)
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")


# ============ API Endpoints ============

@router.get("/config", response_model=WhatsAppConfigResponse)
async def get_embedded_signup_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Facebook SDK configuration for Embedded Signup.
    Returns app credentials and signed state token.

    **Requirements:**
    - User must be a jeweller (not admin)
    - Jeweller must be approved
    """
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == current_user.id).first()
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only jewellers can connect WhatsApp"
        )

    if jeweller.waba_id and jeweller.access_token:
        logger.warning(f"Jeweller {jeweller.id} already has WhatsApp connected")

    state_token = generate_state_token(jeweller.id, current_user.id)
    callback_url = f"{settings.WHATSAPP_CALLBACK_BASE_URL}/auth/whatsapp/callback"

    return WhatsAppConfigResponse(
        appId=settings.WHATSAPP_APP_ID,
        configId=settings.FACEBOOK_CONFIG_ID,
        redirectUri=callback_url,
        state=state_token
    )


@router.post("/callback", response_model=WhatsAppCallbackResponse)
async def embedded_signup_callback(
    request: WhatsAppCallbackRequest,
    db: Session = Depends(get_db)
):
    """
    Handle callback from Facebook Embedded Signup.
    Exchanges authorization code for access token and stores credentials.

    **Process:**
    1. Validate state token
    2. Exchange code for access token
    3. Get long-lived token (60 days)
    4. Fetch WABA and phone number details
    5. Store encrypted credentials
    6. Subscribe to webhooks
    7. Notify admins
    """
    state_payload = validate_state_token(request.state)
    jeweller_id = state_payload.get("jeweller_id")

    jeweller = db.query(Jeweller).filter(Jeweller.id == jeweller_id).first()
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Jeweller not found"
        )

    try:
        # Step 1: Exchange code for short-lived token
        logger.info(f"Exchanging code for token - Jeweller ID: {jeweller_id}")
        token_data = await exchange_code_for_token(request.code)
        short_lived_token = token_data.get("access_token")

        if not short_lived_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Facebook"
            )

        # Step 2: Get long-lived token
        logger.info(f"Exchanging for long-lived token - Jeweller ID: {jeweller_id}")
        long_lived_data = await get_long_lived_token(short_lived_token)
        access_token = long_lived_data.get("access_token", short_lived_token)
        expires_in = long_lived_data.get("expires_in", 3600)

        # Step 3: Debug token to get user ID and WABA ID
        logger.info(f"Getting token info - Jeweller ID: {jeweller_id}")
        token_info = await get_token_info(access_token)

        waba_id = None
        granular_scopes = token_info.get("granular_scopes", [])
        for scope in granular_scopes:
            if scope.get("scope") == "whatsapp_business_management":
                target_ids = scope.get("target_ids", [])
                if target_ids:
                    waba_id = target_ids[0]
                    break

        if not waba_id:
            waba_id = token_info.get("app_id")

        if not waba_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not determine WhatsApp Business Account ID from token"
            )

        fb_user_id = token_info.get("user_id", "")

        # Step 4: Get WABA details
        logger.info(f"Fetching WABA details - Jeweller ID: {jeweller_id}, WABA ID: {waba_id}")
        waba_details = await get_waba_details(waba_id, access_token)
        waba_name = waba_details.get("name", jeweller.business_name)
        verification_status = waba_details.get("account_review_status", "pending")

        # Step 5: Get phone numbers
        logger.info(f"Fetching phone numbers - Jeweller ID: {jeweller_id}, WABA ID: {waba_id}")
        phone_numbers = await get_phone_numbers(waba_id, access_token)

        phone_number_id = None
        phone_display_number = None

        if phone_numbers:
            primary_phone = next(
                (phone for phone in phone_numbers if phone.get("verified_name")),
                phone_numbers[0]
            )
            phone_number_id = primary_phone.get("id")
            phone_display_number = primary_phone.get("display_phone_number")

        if not phone_number_id:
            logger.warning(f"No phone numbers found for WABA {waba_id}")

        # Step 6: Encrypt and store credentials
        logger.info(f"Encrypting and storing credentials - Jeweller ID: {jeweller_id}")
        encrypted_token = encrypt_token(access_token)
        webhook_verify_token = secrets.token_urlsafe(32)
        token_expires_at = now_utc() + timedelta(seconds=expires_in)

        jeweller.fb_app_scoped_user_id = fb_user_id
        jeweller.waba_id = waba_id
        jeweller.waba_name = waba_name
        jeweller.phone_number_id = phone_number_id
        jeweller.phone_display_number = phone_display_number
        jeweller.access_token = encrypted_token
        jeweller.access_token_expires_at = token_expires_at
        jeweller.webhook_verify_token = webhook_verify_token
        jeweller.business_verification_status = verification_status
        jeweller.whatsapp_connected_at = now_utc()
        jeweller.updated_at = now_utc()

        db.commit()
        db.refresh(jeweller)

        # Step 7: Subscribe WABA to webhooks
        logger.info(f"Subscribing to webhooks - Jeweller ID: {jeweller_id}, WABA ID: {waba_id}")
        await subscribe_waba_to_webhook(waba_id, access_token)

        # Step 8: Notify admins
        logger.info(f"Notifying admins - Jeweller ID: {jeweller_id}")
        await notify_admin_whatsapp_connected(jeweller_id, db)

        logger.info(f"WhatsApp connected successfully - Jeweller ID: {jeweller_id}, WABA ID: {waba_id}")

        return WhatsAppCallbackResponse(
            success=True,
            waba_id=waba_id,
            phone_display_number=phone_display_number,
            business_name=waba_name
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedded Signup callback failed - Jeweller ID: {jeweller_id}, Error: {str(e)}")
        db.rollback()
        return WhatsAppCallbackResponse(
            success=False,
            error=f"Failed to complete WhatsApp connection: {str(e)}"
        )


@router.delete("/disconnect", response_model=WhatsAppDisconnectResponse)
async def disconnect_whatsapp(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect jeweller's WhatsApp Business Account.
    Removes all credentials and connection data.
    """
    jeweller = db.query(Jeweller).filter(Jeweller.user_id == current_user.id).first()
    if not jeweller:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only jewellers can disconnect WhatsApp"
        )

    if not jeweller.waba_id:
        return WhatsAppDisconnectResponse(
            success=True,
            message="WhatsApp was not connected"
        )

    logger.info(f"Disconnecting WhatsApp - Jeweller ID: {jeweller.id}, WABA ID: {jeweller.waba_id}")

    jeweller.fb_app_scoped_user_id = None
    jeweller.waba_id = None
    jeweller.waba_name = None
    jeweller.phone_number_id = None
    jeweller.phone_display_number = None
    jeweller.access_token = None
    jeweller.access_token_expires_at = None
    jeweller.webhook_verify_token = None
    jeweller.business_verification_status = None
    jeweller.whatsapp_connected_at = None
    jeweller.last_token_refresh = None
    jeweller.updated_at = now_utc()

    db.commit()

    logger.info(f"WhatsApp disconnected successfully - Jeweller ID: {jeweller.id}")

    return WhatsAppDisconnectResponse(
        success=True,
        message="WhatsApp Business Account disconnected successfully"
    )