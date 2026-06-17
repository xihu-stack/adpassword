import request from './request'

// 用户相关 API
export const userApi = {
  // 获取用户信息
  getUserInfo() {
    return request({
      url: '/user/info',
      method: 'get',
    })
  },
  
  // 修改密码
  changePassword(data) {
    return request({
      url: '/user/change-password',
      method: 'post',
      data,
    })
  },
  
  // 绑定手机号
  bindPhone(data) {
    return request({
      url: '/user/bind-phone',
      method: 'post',
      data,
    })
  },
  
  // 发送短信验证码
  sendSmsCode(data) {
    return request({
      url: '/user/send-sms-code',
      method: 'post',
      data,
    })
  },
  
  // 设置 MFA
  setupMfa() {
    return request({
      url: '/user/mfa/setup',
      method: 'get',
    })
  },
  
  // 启用 MFA
  enableMfa(data) {
    return request({
      url: '/user/mfa/enable',
      method: 'post',
      data,
    })
  },
  
  // 禁用 MFA
  disableMfa(data) {
    return request({
      url: '/user/mfa/disable',
      method: 'post',
      data,
    })
  },
}

// 管理员相关 API
export const adminApi = {
  // 获取域列表
  getDomains() {
    return request({
      url: '/api/admin/domains',
      method: 'get',
    })
  },
  
  // 创建域
  createDomain(data) {
    return request({
      url: '/api/admin/domains',
      method: 'post',
      data,
    })
  },
  
  // 更新域
  updateDomain(id, data) {
    return request({
      url: `/api/admin/domains/${id}`,
      method: 'put',
      data,
    })
  },
  
  // 测试域连接
  testDomain(data) {
    // 如果传入的是对象，使用新的实时测试 API
    if (typeof data === 'object' && data !== null) {
      return request({
        url: '/api/admin/domains/test',
        method: 'post',
        data,
      })
    }
    // 否则使用原来的 API（使用数据库中的配置）
    return request({
      url: `/api/admin/domains/${data}/test`,
      method: 'post',
      data: {},
    })
  },
  
  // 获取用户列表
  getUsers(params) {
    return request({
      url: '/admin/users',
      method: 'get',
      params,
    })
  },
  
  // 更新用户
  updateUser(id, data) {
    return request({
      url: `/admin/users/${id}`,
      method: 'put',
      data,
    })
  },
  
  // 重置用户密码
  resetUserPassword(id, data) {
    return request({
      url: `/admin/users/${id}/reset-password`,
      method: 'post',
      data,
    })
  },
  
  // 获取短信配置
  getSmsConfig() {
    return request({
      url: '/admin/sms-config',
      method: 'get',
    })
  },
  
  // 保存短信配置
  saveSmsConfig(data) {
    return request({
      url: '/admin/sms-config',
      method: 'post',
      data,
    })
  },
  
  // 获取管理日志
  getAdminLogs(params) {
    return request({
      url: '/admin/logs',
      method: 'get',
      params,
    })
  },
}
