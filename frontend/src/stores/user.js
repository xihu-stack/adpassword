import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref(JSON.parse(localStorage.getItem('user') || '{}'))
  
  const isLoggedIn = computed(() => !!userInfo.value.id)
  const isAdmin = computed(() => userInfo.value.role === 'admin')
  
  function setUserInfo(user) {
    userInfo.value = user
    localStorage.setItem('user', JSON.stringify(user))
  }
  
  function clearUserInfo() {
    userInfo.value = {}
    localStorage.removeItem('user')
  }
  
  return {
    userInfo,
    isLoggedIn,
    isAdmin,
    setUserInfo,
    clearUserInfo,
  }
})
