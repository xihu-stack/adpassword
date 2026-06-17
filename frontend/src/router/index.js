import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
  },
  {
    path: '/',
    redirect: '/user/index',
  },
  {
    path: '/user/index',
    name: 'UserIndex',
    component: () => import('@/views/user/Index.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'change-password',
        name: 'ChangePassword',
        component: () => import('@/views/user/ChangePassword.vue'),
      },
      {
        path: 'phone',
        name: 'BindPhone',
        component: () => import('@/views/user/BindPhone.vue'),
      },
      {
        path: 'mfa',
        name: 'MfaSetup',
        component: () => import('@/views/user/MfaSetup.vue'),
      },
    ],
  },
  {
    path: '/admin/dashboard',
    name: 'AdminDashboard',
    component: () => import('@/views/admin/Dashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    alias: ['/admin/d', '/a/d'],
  },
  {
    path: '/admin/domains',
    name: 'DomainConfig',
    component: () => import('@/views/admin/DomainConfig.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    alias: ['/admin/dm', '/a/dm'],
  },
  {
    path: '/admin/users',
    name: 'UserManage',
    component: () => import('@/views/admin/UserManage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    alias: ['/admin/u', '/a/u'],
  },
  {
    path: '/admin/sms',
    name: 'SmsConfig',
    component: () => import('@/views/admin/SmsConfig.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    alias: ['/admin/s', '/a/s'],
  },
  {
    path: '/admin/logs',
    name: 'AdminLogs',
    component: () => import('@/views/admin/Dashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    alias: ['/admin/l', '/a/l', '/l'],
  },
  {
    path: '/admin/settings',
    name: 'AdminSettings',
    component: () => import('@/views/admin/Dashboard.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
    alias: ['/admin/st', '/a/st'],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 路径加密重定向：将完整路径重定向到加密路径
  const pathMapping = {
    '/admin/dashboard': '/a/d',
    '/admin/domains': '/a/dm',
    '/admin/users': '/a/u',
    '/admin/sms': '/a/s',
    '/admin/logs': '/a/l',
    '/admin/settings': '/a/st',
  }
  
  // 如果访问的是完整路径，重定向到加密路径
  if (pathMapping[to.path]) {
    next(pathMapping[to.path])
    return
  }
  
  let user = localStorage.getItem('user')
  let isAuthenticated = !!user
  
  if (to.meta.requiresAuth) {
    if (!isAuthenticated) {
      // 尝试从后端获取用户信息
      try {
        const response = await fetch('/api/user/info')
        if (response.ok) {
          const data = await response.json()
          if (data.success) {
            user = JSON.stringify(data.data)
            localStorage.setItem('user', user)
            isAuthenticated = true
          }
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
      }
    }
    
    if (!isAuthenticated) {
      next('/login')
      return
    }
    
    if (to.meta.requiresAdmin) {
      const userData = JSON.parse(user || '{}')
      if (userData.role !== 'admin') {
        next('/user/index')
        return
      }
    }
  }
  
  next()
})

export default router
