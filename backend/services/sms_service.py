from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
from aliyunsdkdysmsapi.request.v20170525 import SendSmsRequest
import json
from models.models import SmsConfig


class SmsService:
    def __init__(self, sms_config: SmsConfig):
        self.client = AcsClient(
            sms_config.access_key,
            sms_config.access_secret,
            "cn-hangzhou"
        )
        self.sign_name = sms_config.sign_name
        self.template_code = sms_config.template_code
    
    def send_verification_code(self, phone_number: str, code: str):
        """发送验证码短信"""
        try:
            request = SendSmsRequest()
            request.set_accept_format('json')
            
            request.set_PhoneNumbers(phone_number)
            request.set_SignName(self.sign_name)
            request.set_TemplateCode(self.template_code)
            request.set_TemplateParam(json.dumps({'code': code}))
            
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            
            if result.get('Code') == 'OK':
                return True, "发送成功"
            else:
                return False, f"发送失败：{result.get('Message')}"
        except Exception as e:
            return False, f"发送异常：{str(e)}"
    
    def send_password_change_notification(self, phone_number: str, username: str):
        """发送密码修改通知短信"""
        # 注意：需要配置不同的模板
        try:
            request = SendSmsRequest()
            request.set_accept_format('json')
            
            request.set_PhoneNumbers(phone_number)
            request.set_SignName(self.sign_name)
            request.set_TemplateCode(self.template_code)
            request.set_TemplateParam(json.dumps({
                'username': username,
                'type': '密码修改'
            }))
            
            response = self.client.do_action_with_exception(request)
            result = json.loads(response)
            
            return result.get('Code') == 'OK', result.get('Message')
        except Exception as e:
            return False, f"发送异常：{str(e)}"
