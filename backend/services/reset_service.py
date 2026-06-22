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

    # ---------- 身份匹配 ----------
    def _protected_list(self):
        import json
        st = SystemSetting.query.filter_by(setting_key='reset_protected_accounts').first()
        if not st or not st.setting_value:
            return []
        try:
            return [str(x).strip().lower() for x in json.loads(st.setting_value) if x]
        except Exception:
            return []

    def find_user_by_email_phone(self, email, phone):
        """返回 (matched: bool, info|None)。"""
        email = normalize_email(email)
        phone = normalize_phone(phone)
        if not email or not phone:
            return False, None

        domain = Domain.query.filter_by(is_active=True).first()
        if not domain:
            return False, None

        info = self.ldap.lookup_user_by_email(domain, email)
        if not info:
            return False, None
        if info.get('disabled'):
            return False, None
        if normalize_phone(info.get('mobile', '')) != phone:
            return False, None

        # 保护名单：DN / sAMAccountName / memberOf 任一命中
        protected = self._protected_list()
        candidates = {
            (info.get('user_dn') or '').lower(),
            (info.get('sam_account_name') or '').lower(),
        }
        candidates.update(m.lower() for m in info.get('member_of', []))
        if any(p in candidates for p in protected):
            return False, None

        return True, info

    # ---------- 发码与校验 ----------
    def issue_sms_code(self, user_dn, phone):
        allowed, reason = self.check_rate_limits(phone, None, None)
        if not allowed:
            return False, reason or '请求过于频繁'
        code = '%06d' % secrets.randbelow(1000000)
        hashed = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        rec = SmsVerificationCode(
            phone=phone, code=hashed, purpose='reset', fail_count=0,
            expires_at=datetime.utcnow() + timedelta(minutes=CODE_TTL_MINUTES))
        db.session.add(rec)
        db.session.commit()
        self._increment_rate(phone, None, None)
        ok, msg = self.sms.send_verification_code(phone, code)
        if not ok:
            return False, '验证码发送失败，请稍后重试'
        return True, 'OK'

    def verify_sms_code(self, phone, code):
        rec = (SmsVerificationCode.query
               .filter_by(phone=phone, is_used=False, purpose='reset')
               .order_by(SmsVerificationCode.created_at.desc()).first())
        if not rec:
            return False, '请先获取验证码'
        if datetime.utcnow() > rec.expires_at:
            rec.is_used = True
            db.session.commit()
            return False, '验证码已失效，请重新获取'
        if rec.fail_count >= MAX_FAIL_COUNT:
            rec.is_used = True
            db.session.commit()
            return False, '错误次数过多，请重新获取验证码'
        if not bcrypt.checkpw((code or '').encode('utf-8'), rec.code.encode('utf-8')):
            rec.fail_count += 1
            db.session.commit()
            remaining = MAX_FAIL_COUNT - rec.fail_count
            if remaining <= 0:
                rec.is_used = True
                db.session.commit()
                return False, '错误次数过多，请重新获取验证码'
            return False, '验证码错误，还剩 %d 次' % remaining
        rec.is_used = True
        db.session.commit()
        return True, 'OK'


def normalize_email(email):
    return (email or '').strip().lower()


def normalize_phone(phone):
    digits = re.sub(r'\D', '', phone or '')
    if len(digits) == 13 and digits.startswith('86'):
        digits = digits[2:]
    return digits


def validate_password(pw, config):
    if not pw:
        return False, '请输入新密码'
    if len(pw) < int(config.get('PASSWORD_MIN_LENGTH', 8)):
        return False, '新密码长度至少 %d 位' % config.get('PASSWORD_MIN_LENGTH', 8)
    if config.get('PASSWORD_REQUIRE_LOWERCASE') and not re.search(r'[a-z]', pw):
        return False, '密码必须包含小写字母'
    if config.get('PASSWORD_REQUIRE_UPPERCASE') and not re.search(r'[A-Z]', pw):
        return False, '密码必须包含大写字母'
    if config.get('PASSWORD_REQUIRE_NUMBER') and not re.search(r'\d', pw):
        return False, '密码必须包含数字'
    if config.get('PASSWORD_REQUIRE_SPECIAL') and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", pw):
        return False, '密码必须包含特殊字符'
    return True, None
