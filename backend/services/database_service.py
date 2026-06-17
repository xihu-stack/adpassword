"""
数据库连接测试服务
支持 MySQL、PostgreSQL、SQL Server 三种数据库类型的连接测试
"""

import bcrypt


class DatabaseService:
    """数据库服务类"""
    
    # 数据库类型默认端口
    DEFAULT_PORTS = {
        'mysql': 3306,
        'pgsql': 5432,
        'sqlserver': 1433
    }
    
    @staticmethod
    def test_connection(db_type: str, host: str, port: int, database: str, 
                       username: str, password: str) -> dict:
        """
        测试数据库连接
        
        Args:
            db_type: 数据库类型 (mysql, pgsql, sqlserver)
            host: 数据库主机地址
            port: 数据库端口
            database: 数据库名称
            username: 用户名
            password: 密码
            
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            if db_type == 'mysql':
                return DatabaseService._test_mysql(host, port, database, username, password)
            elif db_type == 'pgsql':
                return DatabaseService._test_pgsql(host, port, database, username, password)
            elif db_type == 'sqlserver':
                return DatabaseService._test_sqlserver(host, port, database, username, password)
            else:
                return {
                    'success': False,
                    'message': f'不支持的数据库类型：{db_type}'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'连接测试失败：{str(e)}'
            }
    
    @staticmethod
    def _test_mysql(host: str, port: int, database: str, 
                    username: str, password: str) -> dict:
        """测试 MySQL 连接"""
        try:
            import pymysql
            
            connection = pymysql.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=5,
                charset='utf8mb4'
            )
            
            # 测试连接是否有效
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                result = cursor.fetchone()
                if result and result[0] == 1:
                    connection.close()
                    return {
                        'success': True,
                        'message': 'MySQL 连接成功！'
                    }
            
            connection.close()
            return {
                'success': False,
                'message': 'MySQL 连接测试失败'
            }
            
        except ImportError:
            return {
                'success': False,
                'message': '未安装 MySQL 驱动：pymysql，请运行 pip install pymysql'
            }
        except pymysql.err.OperationalError as e:
            return {
                'success': False,
                'message': f'MySQL 连接失败：{e.args[1] if len(e.args) > 1 else str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'MySQL 连接错误：{str(e)}'
            }
    
    @staticmethod
    def _test_pgsql(host: str, port: int, database: str, 
                    username: str, password: str) -> dict:
        """测试 PostgreSQL 连接"""
        try:
            import psycopg2
            
            connection = psycopg2.connect(
                host=host,
                port=port,
                database=database,
                user=username,
                password=password,
                connect_timeout=5
            )
            
            # 测试连接是否有效
            cursor = connection.cursor()
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result and result[0] == 1:
                return {
                    'success': True,
                    'message': 'PostgreSQL 连接成功！'
                }
            
            return {
                'success': False,
                'message': 'PostgreSQL 连接测试失败'
            }
            
        except ImportError:
            return {
                'success': False,
                'message': '未安装 PostgreSQL 驱动：psycopg2-binary，请运行 pip install psycopg2-binary'
            }
        except psycopg2.OperationalError as e:
            return {
                'success': False,
                'message': f'PostgreSQL 连接失败：{str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'PostgreSQL 连接错误：{str(e)}'
            }
    
    @staticmethod
    def _test_sqlserver(host: str, port: int, database: str, 
                        username: str, password: str) -> dict:
        """测试 SQL Server 连接"""
        try:
            import pyodbc
            
            # 构建连接字符串
            connection_string = (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={host},{port};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password}"
            )
            
            connection = pyodbc.connect(connection_string, timeout=5)
            
            # 测试连接是否有效
            cursor = connection.cursor()
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result and result[0] == 1:
                return {
                    'success': True,
                    'message': 'SQL Server 连接成功！'
                }
            
            return {
                'success': False,
                'message': 'SQL Server 连接测试失败'
            }
            
        except ImportError:
            return {
                'success': False,
                'message': '未安装 SQL Server 驱动：pyodbc，请运行 pip install pyodbc'
            }
        except pyodbc.Error as e:
            error_msg = str(e)
            if 'Data Source Name' in error_msg:
                return {
                    'success': False,
                    'message': 'SQL Server 连接失败：未找到 ODBC 驱动，请安装 ODBC Driver 17 for SQL Server'
                }
            return {
                'success': False,
                'message': f'SQL Server 连接失败：{error_msg}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'SQL Server 连接错误：{str(e)}'
            }
    
    @staticmethod
    def encrypt_password(password: str) -> str:
        """加密数据库密码"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """验证数据库密码"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    @staticmethod
    def get_connection_string(db_type: str, host: str, port: int, 
                             database: str, username: str, password: str) -> str:
        """
        生成数据库连接字符串
        
        Args:
            db_type: 数据库类型
            host: 主机地址
            port: 端口
            database: 数据库名
            username: 用户名
            password: 密码
            
        Returns:
            str: 连接字符串
        """
        if db_type == 'mysql':
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        elif db_type == 'pgsql':
            return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{database}"
        elif db_type == 'sqlserver':
            return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        else:
            raise ValueError(f'不支持的数据库类型：{db_type}')
