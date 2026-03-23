import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { useState, createContext, useContext, useEffect } from 'react'
import Login from './pages/auth/Login'
import Register from './pages/auth/Register'
import ForgotPassword from './pages/auth/ForgotPassword'
import ResetPassword from './pages/auth/ResetPassword'
import Dashboard from './pages/dashboard/Dashboard'
import TradingDashboard from './pages/trading/TradingDashboard'
import StrategyDashboard from './pages/strategies/StrategyDashboard'
import StrategyBuilder from './pages/strategies/EnhancedStrategyBuilder'
import Portfolio from './pages/portfolio/Portfolio'
import Orders from './pages/orders/Orders'
import Notifications from './pages/notifications/Notifications'
import Settings from './pages/settings/Settings'
import BrokerConnections from './pages/settings/BrokerConnections'
import RiskRules from './pages/settings/RiskRules'
import ProfileSettings from './pages/settings/ProfileSettings'
import SecuritySettings from './pages/settings/SecuritySettings'
import TradingPreferences from './pages/settings/TradingPreferences'
import Backtest from './pages/backtesting/Backtest'
import Analytics from './pages/analytics/Analytics'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminUserManagement from './pages/admin/AdminUserManagement'
import StrategyAssignment from './pages/admin/StrategyAssignment'
import PaperTrading from './pages/trading/PaperTrading'
import LiveTrading from './pages/trading/LiveTrading'
import { Layout } from './components/Layout'

interface User {
  id: string
  email: string
  role: string
  first_name?: string
}

interface AuthContextType {
  isAuthenticated: boolean
  token: string | null
  user: User | null
  login: (token: string, userData?: User) => void
  logout: () => void
}

export const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  token: null,
  user: null,
  login: () => {},
  logout: () => {},
})

export const useAuth = () => useContext(AuthContext)

function ProtectedRoute() {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

function AdminRoute() {
  const { isAuthenticated, user } = useAuth()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  if (user?.role !== 'admin') {
    return <Navigate to="/trading" replace />
  }
  
  return <Outlet />
}

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [user, setUser] = useState<User | null>(null)
  
  useEffect(() => {
    const userStr = localStorage.getItem('user')
    if (userStr) {
      try {
        setUser(JSON.parse(userStr))
      } catch {
        setUser(null)
      }
    }
  }, [token])
  
  const login = (newToken: string, userData?: User) => {
    localStorage.setItem('token', newToken)
    if (userData) {
      localStorage.setItem('user', JSON.stringify(userData))
      setUser(userData)
    }
    setToken(newToken)
  }
  
  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }
  
  return (
    <AuthContext.Provider value={{ isAuthenticated: !!token, token, user, login, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          
          <Route element={<ProtectedRoute />}>
            <Route element={<Layout />}>
              <Route path="/trading" element={<TradingDashboard />} />
              <Route path="/strategies" element={<StrategyDashboard />} />
              <Route path="/strategies/builder" element={<StrategyBuilder />} />
              <Route path="/strategies/new" element={<StrategyBuilder />} />
              <Route path="/strategies/:id" element={<StrategyBuilder />} />
              <Route path="/portfolio" element={<Portfolio />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/settings/brokers" element={<BrokerConnections />} />
              <Route path="/settings/risk" element={<RiskRules />} />
              <Route path="/settings/profile" element={<ProfileSettings />} />
              <Route path="/settings/security" element={<SecuritySettings />} />
              <Route path="/settings/trading" element={<TradingPreferences />} />
              <Route path="/backtest" element={<Backtest />} />
              <Route path="/paper-trading" element={<PaperTrading />} />
              <Route path="/live-trading" element={<LiveTrading />} />
            </Route>
          </Route>
          
            <Route element={<AdminRoute />}>
              <Route element={<Layout />}>
                <Route path="/admin" element={<AdminDashboard />} />
                <Route path="/admin/users" element={<AdminUserManagement />} />
                <Route path="/admin/assign-strategies" element={<StrategyAssignment />} />
              </Route>
            </Route>
          
          <Route path="/" element={<Navigate to="/trading" replace />} />
          <Route path="*" element={<Navigate to="/trading" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}

export default App