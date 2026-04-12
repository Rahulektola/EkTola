"""
WhatsApp Token Refresh Task
Periodic Celery task to refresh expiring WhatsApp access tokens for jewellers
"""
import logging
from datetime import datetime, timedelta
from typing import List
import httpx
from sqlalchemy.orm import Session

from app.core.datetime_utils import now_utc
from app.celery_app import celery
from app.database import SessionLocal
from app.models.jeweller import Jeweller
from app.core.encryption import encrypt_token, decrypt_token, TokenEncryptionError
from app.config import settings

logger = logging.getLogger(__name__)


def refresh_whatsapp_token(jeweller_id: int, current_token: str) -> dict:
    """
    Refresh WhatsApp access token using Meta Graph API.
    
    Args:
        jeweller_id: ID of the jeweller
        current_token: Current access token to refresh
        
    Returns:
        dict with 'access_token' and 'expires_in' or raises exception
    """
    url = f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": settings.WHATSAPP_APP_ID,
        "client_secret": settings.WHATSAPP_APP_SECRET,
        "fb_exchange_token": current_token
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        access_token = data.get("access_token")
        expires_in = data.get("expires_in", 5184000)  # Default 60 days

        if not access_token:
            raise ValueError("No access token in response")

        logger.info(f"Token refreshed successfully for jeweller {jeweller_id}")
        return {
            "access_token": access_token,
            "expires_in": expires_in
        }

    except httpx.HTTPError as e:
        logger.error(f"HTTP error refreshing token for jeweller {jeweller_id}: {str(e)}")
        raise
    except ValueError as e:
        logger.error(f"Value error refreshing token for jeweller {jeweller_id}: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error refreshing token for jeweller {jeweller_id}: {str(e)}")
        raise


@celery.task(name="refresh_expiring_whatsapp_tokens")
def refresh_expiring_tokens():
    """
    Celery task: Refresh WhatsApp access tokens expiring within 7 days.
    
    Runs daily via Celery Beat schedule.
    
    Process:
    1. Find jewellers with tokens expiring within 7 days
    2. For each jeweller:
       - Decrypt current token
       - Call Meta API to refresh
       - Encrypt and store new token
       - Update expiry time
       - Log success/failure
    """
    db: Session = SessionLocal()
    
    try:
        # Calculate cutoff date (7 days from now)
        cutoff_date = now_utc() + timedelta(days=7)
        
        # Find jewellers with expiring tokens
        jewellers = db.query(Jeweller).filter(
            Jeweller.access_token.isnot(None),
            Jeweller.access_token_expires_at.isnot(None),
            Jeweller.access_token_expires_at < cutoff_date,
            Jeweller.is_active == True
        ).all()
        
        if not jewellers:
            logger.info("No jewellers with expiring WhatsApp tokens")
            return {
                "status": "success",
                "message": "No tokens to refresh",
                "refreshed": 0,
                "failed": 0
            }
        
        logger.info(f"Found {len(jewellers)} jewellers with expiring tokens")
        
        refreshed_count = 0
        failed_count = 0
        errors = []
        
        for jeweller in jewellers:
            try:
                # Calculate days until expiry
                days_until_expiry = (jeweller.access_token_expires_at - now_utc()).days
                logger.info(f"Refreshing token for jeweller {jeweller.id} ({jeweller.business_name}) - expires in {days_until_expiry} days")
                
                # Decrypt current token
                try:
                    current_token = decrypt_token(jeweller.access_token)
                except TokenEncryptionError as e:
                    logger.error(f"Failed to decrypt token for jeweller {jeweller.id}: {str(e)}")
                    failed_count += 1
                    errors.append({
                        "jeweller_id": jeweller.id,
                        "error": f"Decryption failed: {str(e)}"
                    })
                    continue
                
                refresh_data = refresh_whatsapp_token(jeweller.id, current_token)

                # Encrypt new token
                new_token = refresh_data["access_token"]
                expires_in = refresh_data["expires_in"]

                encrypted_token = encrypt_token(new_token)

                # Update database
                jeweller.access_token = encrypted_token
                jeweller.access_token_expires_at = now_utc() + timedelta(seconds=expires_in)
                jeweller.last_token_refresh = now_utc()
                jeweller.updated_at = now_utc()
                
                db.commit()
                
                refreshed_count += 1
                logger.info(f"Token refreshed successfully for jeweller {jeweller.id} - new expiry: {jeweller.access_token_expires_at}")
                
            except Exception as e:
                logger.error(f"Failed to refresh token for jeweller {jeweller.id}: {str(e)}")
                failed_count += 1
                errors.append({
                    "jeweller_id": jeweller.id,
                    "business_name": jeweller.business_name,
                    "error": str(e)
                })
                db.rollback()
        
        # Send notification to admins if there were failures
        if failed_count > 0:
            logger.warning(f"Token refresh completed with {failed_count} failures")
            # TODO: Send admin notification about failures
        
        result = {
            "status": "completed",
            "timestamp": now_utc().isoformat(),
            "total_jewellers": len(jewellers),
            "refreshed": refreshed_count,
            "failed": failed_count,
            "errors": errors
        }
        
        logger.info(f"Token refresh task completed: {refreshed_count} refreshed, {failed_count} failed")
        return result
        
    except Exception as e:
        logger.error(f"Token refresh task failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()


@celery.task(name="check_expired_whatsapp_tokens")
def check_expired_tokens():
    """
    Celery task: Check for expired WhatsApp tokens and log/notify.
    
    This is a monitoring task that runs separately from refresh.
    Helps identify jewellers who stopped using the platform or have issues.
    """
    db: Session = SessionLocal()
    
    try:
        # Find jewellers with expired tokens
        expired_jewellers = db.query(Jeweller).filter(
            Jeweller.access_token.isnot(None),
            Jeweller.access_token_expires_at.isnot(None),
            Jeweller.access_token_expires_at < now_utc(),
            Jeweller.is_active == True
        ).all()
        
        if not expired_jewellers:
            logger.info("No jewellers with expired WhatsApp tokens")
            return {
                "status": "success",
                "expired_count": 0
            }
        
        logger.warning(f"Found {len(expired_jewellers)} jewellers with expired tokens")
        
        expired_info = []
        for jeweller in expired_jewellers:
            days_expired = (now_utc() - jeweller.access_token_expires_at).days
            expired_info.append({
                "jeweller_id": jeweller.id,
                "business_name": jeweller.business_name,
                "days_expired": days_expired,
                "expired_at": jeweller.access_token_expires_at.isoformat()
            })
            logger.warning(f"Jeweller {jeweller.id} ({jeweller.business_name}) has expired token - {days_expired} days overdue")
        
        # TODO: Send admin notification about expired tokens
        
        return {
            "status": "completed",
            "expired_count": len(expired_jewellers),
            "expired_jewellers": expired_info
        }
        
    except Exception as e:
        logger.error(f"Check expired tokens task failed: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        db.close()
