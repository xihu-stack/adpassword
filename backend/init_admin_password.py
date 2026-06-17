"""
初始化 admin 账户密码脚本
用于设置或重置 admin 账户的密码为 admin
"""

from models.models import db, User
import bcrypt

def init_admin_password():
    """初始化 admin 密码为 admin (bcrypt 加密)"""
    
    # 查询 admin 用户
    admin_user = User.query.filter_by(username='admin').first()
    
    if not admin_user:
        print('❌ admin 用户不存在，请先创建 admin 用户')
        return
    
    # 设置默认密码为 admin (bcrypt 加密)
    password = 'admin'
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    admin_user.password_hash = password_hash
    db.session.commit()
    
    print('✅ admin 密码已重置为：admin')
    print(f'密码哈希：{password_hash}')

if __name__ == '__main__':
    init_admin_password()
