import React, { createContext, useContext, useState } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)

  const login = async (email, password) => {
    const result = await window.tk.login(email, password)
    if (result.success) setUser(result.user)
    return result
  }

  const register = async (data) => {
    const result = await window.tk.register(data)
    if (result.success) setUser(result.user)
    return result
  }

  const logout = async () => {
    await window.tk.logout()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
