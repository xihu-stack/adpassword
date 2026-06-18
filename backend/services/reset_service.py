"""忘记密码自助重置核心服务。通过注入 ldap/sms 适配器实现可测试性。"""
from datetime import datetime, timedelta
import bcrypt
import secrets
import re

from models.models import db, SmsVerificationCode, SmsRateLimit, SystemSetting, Domain
from services import secret_crypto

# 限流参数
PHONE_COOLDOWN_SECONDS = 60
HOURLY_LIMIT_PHONE = 5
HOURLY_LIMIT_EMAIL = 5
HOURLY_LIMIT_IP = 20
CODE_TTL_MINUTES = 5
MAX_FAIL_COUNT = 5
RESET_SESSION_MINUTES = 10


class _DefaultLdapAdapter:
    def lookup_user_by_email(self, domain, email):
        from services.ldap_service import LdapService
        return LdapService.lookup_user_by_email(domain, email)

    def admin_set_password_by_dn(self, domain, user_dn, new_password):
        from services.ldap_service import LdapService
        return LdapService.admin_set_password_by_dn(domain, user_dn, new_password)


class _DefaultSmsAdapter:
    def send_verification_code(self, phone, code):
        from services.sms_service import SmsService
        from models.models import SmsConfig
        cfg = SmsConfig.query.filter_by(is_active=True).first()
        if not cfg:
            return False, '短信服务未配置'
        return SmsService(cfg).send_verification_code(phone, code)


class ResetService:
    def __init__(self, ldap_adapter=None, sms_adapter=None):
        self.ldap = ldap_adapter or _DefaultLdapAdapter()
        self.sms = sms_adapter or _DefaultSmsAdapter()

    # ---------- 限流 ----------
    def check_rate_limits(self, phone, email, ip):
        now = datetime.utcnow()
        # 手机号 60s 冷却：查最近一条该手机的验证码
        latest = SmsVerificationCode.query.filter_by(phone=phone).order_by(
            SmsVerificationCode.created_at.desc()).first()
        if latest and latest.created_at and now - latest.created_at < timedelta(seconds=PHONE_COOLDOWN_SECONDS):
            return False, '请稍候再试'

        limits = [
            ('phone', phone, HOURLY_LIMIT_PHONE),
            ('email', email, HOURLY_LIMIT_EMAIL),
            ('ip', ip, HOURLY_LIMIT_IP),
        ]
        for key_type, key_value, cap in limits:
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(key_type=key_type, key_value=key_value).first()
            if rl:
                if now - rl.window_start > timedelta(hours=1):
                    rl.sent_count = 0
                    rl.window_start = now
                if rl.sent_count >= cap:
                    return False, '请求过于频繁'
        return True, None

    def _increment_rate(self, phone, email, ip):
        now = datetime.utcnow()
        for key_type, key_value in (('phone', phone), ('email', email), ('ip', ip)):
            if not key_value:
                continue
            rl = SmsRateLimit.query.filter_by(key_type=key_type, key_value=key_value).first()
            if not rl:
                rl = SmsRateLimit(key_type=key_type, key_value=key_value,
                                  sent_count=0, window_start=now)
                db.session.add(rl)
            if now - rl.window_start > timedelta(hours=1):
                rl.sent_count = 0
                rl.window_start = now
            rl.sent_count += 1
        db.session.commit()
