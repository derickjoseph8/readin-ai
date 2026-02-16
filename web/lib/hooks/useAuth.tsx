'use client'

import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { authApi, User, UserStatus } from '../api/auth'
import apiClient from '../api/client'

interface AuthContextType {
  user: User | null
  status: UserStatus | null
  isLoading: boolean
  isAuthenticated: boolean
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  refreshStatus: () => Promise<void>
  updateUser: (data: { full_name?: string; profession?: string; company?: string }) => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<UserStatus | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshStatus = useCallback(async () => {
    try {
      const statusData = await authApi.getStatus()
      setUser(statusData.user)
      setStatus(statusData)
    } catch {
      setUser(null)
      setStatus(null)
    }
  }, [])

  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        await refreshStatus()
      }
      setIsLoading(false)
    }
    checkAuth()
  }, [refreshStatus])

  const login = async (email: string, password: string) => {
    const response = await authApi.login({ email, password })
    setUser(response.user)
    await refreshStatus()
  }

  const register = async (email: string, password: string, fullName?: string) => {
    const response = await authApi.register({ email, password, full_name: fullName })
    setUser(response.user)
    await refreshStatus()
  }

  const logout = () => {
    authApi.logout()
    setUser(null)
    setStatus(null)
  }

  const updateUser = async (data: { full_name?: string; profession?: string; company?: string }) => {
    const updatedUser = await authApi.updateProfile(data)
    setUser(updatedUser)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        status,
        isLoading,
        isAuthenticated: !!user,
        token: apiClient.getToken(),
        login,
        register,
        logout,
        refreshStatus,
        updateUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default useAuth
