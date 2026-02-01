from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.otp import OTP, OTPPurpose
from app.models.jeweller import Jeweller
from app.services.whatsapp_service import WhatsAppService
from app.config import settings
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class OTPService:
    """Service for managing OTP authentication"""
    
    OTP_EXPIRY_MINUTES = 10
    
    def __init__(self, db: Session):
        self.db = db
    
    async def send_login_otp(self, phone_number: str) -> Dict[str, any]:
        """
        Send OTP to jeweller's WhatsApp for login
        
        Args:
            phone_number: Jeweller's phone number in international format
            
        Returns:
            Dict with success status and message
        """
        # Check if jeweller exists
        jeweller = self.db.query(Jeweller).filter(
            Jeweller.phone_number == phone_number,
            Jeweller.is_active == True
        ).first()
        
        if not jeweller:
            logger.warning(f"Login OTP requested for unregistered phone: {phone_number}")
            return {
                "success": False, 
                "message": "Phone number not registered. Please contact support."
            }
        
        # Invalidate previous OTPs for this phone number
        self.db.query(OTP).filter(
            OTP.phone_number == phone_number,
            OTP.is_verified == False
        ).update({"is_expired": True})
        self.db.commit()
        
        # Generate new OTP
        otp_code = OTP.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        otp = OTP(
            phone_number=phone_number,
            otp_code=otp_code,
            purpose=OTPPurpose.LOGIN,
            expires_at=expires_at
        )
        self.db.add(otp)
        self.db.commit()
        
        # Send OTP via WhatsApp
        try:
            # Use platform's WhatsApp account to send OTP
            platform_token = getattr(settings, 'PLATFORM_WHATSAPP_TOKEN', None)
            platform_phone_id = getattr(settings, 'PLATFORM_PHONE_NUMBER_ID', None)
            
            if not platform_token or not platform_phone_id:
                logger.error("Platform WhatsApp credentials not configured")
                return {
                    "success": False,
                    "message": "OTP service temporarily unavailable"
                }
            
            whatsapp = WhatsAppService(platform_token, platform_phone_id)
            
            message = f"""🔐 *EkTola Login OTP*

Your verification code is: *{otp_code}*

Valid for {self.OTP_EXPIRY_MINUTES} minutes.

⚠️ Do not share this code with anyone."""
            
            await whatsapp.send_text_message(phone_number, message)
            
            logger.info(f"OTP sent successfully to {phone_number}")
            return {
                "success": True,
                "message": "OTP sent to your WhatsApp",
                "expires_in_minutes": self.OTP_EXPIRY_MINUTES
            }
        except Exception as e:
            logger.error(f"Failed to send OTP to {phone_number}: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send OTP. Please try again."
            }
    
    def verify_signup_otp(self, phone_number: str, otp_code: str) -> Dict[str, any]:
        """
        Verify OTP for signup
        
        Args:
            phone_number: Phone number
            otp_code: 6-digit OTP code
            
        Returns:
            Dict with verification status
        """
        return self._verify_otp(phone_number, otp_code, OTPPurpose.SIGNUP)
    
    def verify_otp(self, phone_number: str, otp_code: str) -> Dict[str, any]:
        """
        Verify OTP and return jeweller if valid
        
        Args:
            phone_number: Jeweller's phone number
            otp_code: 6-digit OTP code
            
        Returns:
            Dict with verification status and jeweller object if successful
        """
        result = self._verify_otp(phone_number, otp_code, OTPPurpose.LOGIN)
        
        if result["success"]:
            # Get jeweller
            jeweller = self.db.query(Jeweller).filter(
                Jeweller.phone_number == phone_number
            ).first()
            
            if not jeweller:
                return {
                    "success": False,
                    "message": "Jeweller account not found"
                }
            
            result["jeweller"] = jeweller
        
        return result
    
    def _verify_otp(self, phone_number: str, otp_code: str, purpose: OTPPurpose) -> Dict[str, any]:
        """
        Internal method to verify OTP
        
        Args:
            phone_number: Phone number
            otp_code: OTP code
            purpose: OTP purpose (LOGIN or SIGNUP)
            
        Returns:
            Dict with verification status
        """
        # Find most recent valid OTP
        otp = self.db.query(OTP).filter(
            OTP.phone_number == phone_number,
            OTP.otp_code == otp_code,
            OTP.purpose == purpose,
            OTP.is_verified == False,
            OTP.is_expired == False
        ).order_by(OTP.created_at.desc()).first()
        
        if not otp:
            logger.warning(f"Invalid OTP attempt for {phone_number}")
            return {
                "success": False,
                "message": "Invalid or expired OTP"
            }
        
        # Increment attempts
        otp.attempts += 1
        
        # Check if OTP is still valid
        if not otp.is_valid():
            otp.is_expired = True
            self.db.commit()
            logger.warning(f"OTP expired or max attempts reached for {phone_number}")
            return {
                "success": False,
                "message": "OTP expired or maximum attempts exceeded"
            }
        
        # Mark OTP as verified
        otp.is_verified = True
        otp.verified_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"OTP verified successfully for {phone_number}")
        return {
            "success": True,
            "message": "OTP verified successfully"
        }
    
    async def send_signup_otp(self, phone_number: str) -> Dict[str, any]:
        """
        Send OTP for new jeweller registration
        
        Args:
            phone_number: New jeweller's phone number
            
        Returns:
            Dict with success status and message
        """
        # Check if phone number already registered
        existing = self.db.query(Jeweller).filter(
            Jeweller.phone_number == phone_number
        ).first()
        
        if existing:
            return {
                "success": False,
                "message": "Phone number already registered"
            }
        
        # Generate and send OTP (similar to login OTP)
        self.db.query(OTP).filter(
            OTP.phone_number == phone_number,
            OTP.is_verified == False
        ).update({"is_expired": True})
        self.db.commit()
        
        otp_code = OTP.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        
        otp = OTP(
            phone_number=phone_number,
            otp_code=otp_code,
            purpose=OTPPurpose.SIGNUP,
            expires_at=expires_at
        )
        self.db.add(otp)
        self.db.commit()
        
        try:
            platform_token = getattr(settings, 'PLATFORM_WHATSAPP_TOKEN', None)
            platform_phone_id = getattr(settings, 'PLATFORM_PHONE_NUMBER_ID', None)
            
            if not platform_token or not platform_phone_id:
                return {
                    "success": False,
                    "message": "OTP service temporarily unavailable"
                }
            
            whatsapp = WhatsAppService(platform_token, platform_phone_id)
            
            message = f"""🎉 *Welcome to EkTola!*

Your registration OTP is: *{otp_code}*

Valid for {self.OTP_EXPIRY_MINUTES} minutes.

⚠️ Do not share this code."""
            
            await whatsapp.send_text_message(phone_number, message)
            
            return {
                "success": True,
                "message": "OTP sent to your WhatsApp",
                "expires_in_minutes": self.OTP_EXPIRY_MINUTES
            }
        except Exception as e:
            logger.error(f"Failed to send signup OTP: {str(e)}")
            return {
                "success": False,
                "message": "Failed to send OTP. Please try again."
            }
