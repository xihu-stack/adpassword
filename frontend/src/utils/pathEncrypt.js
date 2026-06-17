/**
 * 路径加密工具类
 * 用于隐藏真实的 URL 路径，防止路径信息泄露
 */

// 简单的加密映射表
const PATH_MAPPING = {
  '/admin/dashboard': '/a/d',
  '/admin/domains': '/a/m',
  '/admin/users': '/a/u',
  '/admin/sms': '/a/s',
  '/admin/logs': '/a/l',
  '/admin/settings': '/a/t',
}

// 反向映射（用于解密）
const REVERSE_MAPPING = {}
Object.entries(PATH_MAPPING).forEach(([key, value]) => {
  REVERSE_MAPPING[value] = key
})

/**
 * 加密路径
 * @param {string} path - 原始路径
 * @returns {string} - 加密后的路径
 */
export function encryptPath(path) {
  return PATH_MAPPING[path] || path
}

/**
 * 解密路径
 * @param {string} encryptedPath - 加密的路径
 * @returns {string} - 原始路径
 */
export function decryptPath(encryptedPath) {
  return REVERSE_MAPPING[encryptedPath] || encryptedPath
}

/**
 * 获取所有加密路径
 * @returns {Object} - 路径映射对象
 */
export function getAllPathMappings() {
  return { ...PATH_MAPPING }
}

/**
 * 路由导航辅助函数
 * @param {string} path - 原始路径
 * @param {import('vue-router').Router} router - Vue Router 实例
 */
export function navigateTo(router, path) {
  const encryptedPath = encryptPath(path)
  router.push(encryptedPath)
}

export default {
  encryptPath,
  decryptPath,
  getAllPathMappings,
  navigateTo,
}
