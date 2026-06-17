import pyotp
import qrcode
import base64
from io import BytesIO


class TotpService:
    @staticmethod
    def generate_secret(username, issuer="AD Password System"):
        """生成 MFA 密钥和二维码"""
        secret = pyotp.random_base32()
        
        # 生成 TOTP URI
        uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=issuer
        )
        
        # 生成二维码图片
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为 base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        return {
            'secret': secret,
            'uri': uri,
            'qr_code': qr_code_base64
        }
    
    @staticmethod
    def verify_code(secret, code):
        """验证 TOTP 码"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(code, valid_window=1)  # 允许前后 1 个时间窗口
        except Exception:
            return False
    
    @staticmethod
    def generate_backup_codes(count=10):
        """生成备用验证码"""
        import random
        import string
        
        codes = []
        for _ in range(count):
            code = ''.join(random.choices(string.digits, k=8))
            codes.append(code)
        
        return codes
