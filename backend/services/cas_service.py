import requests
from urllib.parse import urlencode, parse_qs
from flask import current_app


class CasService:
    @staticmethod
    def get_login_url(service_url):
        """获取 CAS 登录 URL"""
        params = {
            'service': service_url
        }
        return f"{current_app.config['CAS_SERVER_LOGIN_URL']}?{urlencode(params)}"
    
    @staticmethod
    def validate_ticket(ticket, service_url):
        """验证 CAS Ticket"""
        params = {
            'ticket': ticket,
            'service': service_url
        }
        
        try:
            response = requests.get(
                current_app.config['CAS_SERVER_VALIDATE_URL'],
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                # 解析 CAS 响应（假设是 CAS 3.0 XML 格式）
                xml_response = response.text
                
                # 简单解析 XML 获取用户名
                if 'authenticationSuccess' in xml_response:
                    # 提取用户名字段
                    start = xml_response.find('<cas:user>') + len('<cas:user>')
                    end = xml_response.find('</cas:user>')
                    if start >= 0 and end >= 0:
                        username = xml_response[start:end]
                        return True, username
                
                # 尝试从 attributes 中获取
                if 'attributes' in xml_response:
                    # 可能包含更多用户信息，可以根据需要解析
                    pass
                    
                return False, "无法解析 CAS 响应"
            else:
                return False, f"CAS 服务返回错误状态码：{response.status_code}"
        except Exception as e:
            return False, f"CAS 验证失败：{str(e)}"
    
    @staticmethod
    def logout(service_url=None):
        """获取 CAS 登出 URL"""
        if service_url:
            params = {'service': service_url}
            return f"{current_app.config['CAS_SERVER_LOGOUT_URL']}?{urlencode(params)}"
        return current_app.config['CAS_SERVER_LOGOUT_URL']
