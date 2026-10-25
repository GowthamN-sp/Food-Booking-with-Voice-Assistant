import { createContext, useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../config'

export const GlobalStateContext = createContext(null)

const getOrCreateSessionId = () => {
  if (typeof window === 'undefined') return 'guest_session'
  let id = localStorage.getItem('sessionId')
  if (!id) {
    id = `guest_${typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}_${Math.random().toString(36).slice(2)}`}`
    localStorage.setItem('sessionId', id)
  }
  return id
}

const readStoredUser = () => {
  try {
    const token = localStorage.getItem('savoraToken')
    const raw = localStorage.getItem('user')
    return token && raw ? JSON.parse(raw) : null
  } catch {
    localStorage.removeItem('user')
    localStorage.removeItem('savoraToken')
    return null
  }
}

export const GlobalStateProvider = ({ children }) => {
  const [Togg, setTogg] = useState(false)
  const [user, setUser] = useState(readStoredUser)
  const [isLoggedIn, setIsLoggedIn] = useState(() => Boolean(readStoredUser() && localStorage.getItem('savoraToken')))
  const [loading, setLoading] = useState(true)
  const [sessionId] = useState(getOrCreateSessionId)
  const [foodData, setFoodData] = useState([])
  const [foodError, setFoodError] = useState('')
  const navigate = useNavigate()

  const cartCount = useMemo(() => foodData.reduce((sum, item) => sum + Math.max(0, Number(item.Quantity) || 0), 0), [foodData])
  const displayCart = cartCount > 0

  const fetchFoodData = useCallback(async () => {
    setFoodError('')
    try {
      const response = await apiFetch(`/?sessionId=${encodeURIComponent(sessionId)}`)
      if (response.status === 401 && localStorage.getItem('savoraToken')) {
        localStorage.removeItem('savoraToken')
        localStorage.removeItem('user')
        localStorage.removeItem('isLoggedIn')
        setUser(null)
        setIsLoggedIn(false)
        throw new Error('Your session expired. Please sign in again.')
      }
      if (!response.ok) throw new Error(`Menu request failed (${response.status}).`)
      const data = await response.json()
      if (!Array.isArray(data)) throw new Error('The menu response was not in the expected format.')
      setFoodData(data.map(item => ({ ...item, Quantity: Math.max(0, Number(item.Quantity) || 0) })))
    } catch (error) {
      setFoodError(error.message || 'Could not load the menu. Check that the backend is running.')
      console.error('Savora menu load failed:', error)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => { fetchFoodData() }, [fetchFoodData, user?.user_id])

  const updateQuantity = useCallback(async (foodId, delta) => {
    const id = Number(foodId)
    const change = Number(delta)
    if (!Number.isInteger(id) || !Number.isInteger(change) || change === 0) return false
    const current = foodData.find(item => Number(item.FoodID) === id)
    if (!current) return false
    const optimistic = Math.max(0, (Number(current.Quantity) || 0) + change)
    if (optimistic > 25) {
      setFoodError('You can add up to 25 of one menu item.')
      return false
    }
    setFoodData(prev => prev.map(item => Number(item.FoodID) === id ? { ...item, Quantity: optimistic } : item))
    setFoodError('')
    try {
      let response
      if (isLoggedIn && user) {
        response = await apiFetch(`/update-quantity/${id}/`, { method: 'POST', body: JSON.stringify({ quantity: change }) })
      } else {
        response = await apiFetch('/session-cart/', { method: 'POST', body: JSON.stringify({ sessionId, foodId: id, delta: change }) })
      }
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not update the cart.')
      setFoodData(prev => prev.map(item => Number(item.FoodID) === id ? { ...item, Quantity: Number(data.newQuantity ?? optimistic) } : item))
      return true
    } catch (error) {
      setFoodError(error.message || 'Could not update the cart. Please try again.')
      await fetchFoodData()
      return false
    }
  }, [foodData, isLoggedIn, user, sessionId, fetchFoodData])

  const clearCart = useCallback(async () => {
    const cartKey = isLoggedIn && user ? `user_${user.user_id}` : sessionId
    try {
      const response = await apiFetch(`/session-cart/clear/${encodeURIComponent(cartKey)}/`, { method: 'DELETE' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.success) throw new Error(data.error || 'Could not clear the cart.')
      setFoodData(prev => prev.map(item => ({ ...item, Quantity: 0 })))
      setFoodError('')
      return true
    } catch (error) {
      setFoodError(error.message || 'Could not clear the cart.')
      await fetchFoodData()
      return false
    }
  }, [isLoggedIn, user, sessionId, fetchFoodData])

  const transferSessionCartToUser = useCallback(async () => {
    const response = await apiFetch('/session-cart/transfer/', {
      method: 'POST',
      body: JSON.stringify({ sessionId }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok || !data.success) throw new Error(data.error || 'Could not safely transfer your guest cart.')
  }, [sessionId])

  const login = useCallback(async (userData, authToken) => {
    if (!userData?.user_id || !authToken) throw new Error('The server did not return a valid sign-in session.')
    // Store token before transferring the guest cart: apiFetch attaches it automatically.
    localStorage.setItem('savoraToken', authToken)
    localStorage.setItem('user', JSON.stringify(userData))
    localStorage.setItem('isLoggedIn', 'true')
    try {
      await transferSessionCartToUser()
    } catch (error) {
      console.warn('Guest cart transfer did not fully complete:', error)
    }
    setUser(userData)
    setIsLoggedIn(true)
    setFoodError('')
  }, [transferSessionCartToUser])

  const logout = useCallback(async () => {
    if (user?.user_id) {
      try {
        await apiFetch(`/logout/${user.user_id}/`, { method: 'POST', body: JSON.stringify({}) })
      } catch (error) {
        console.warn('Server logout could not be reached:', error)
      }
    }
    localStorage.removeItem('savoraToken')
    localStorage.removeItem('user')
    localStorage.removeItem('isLoggedIn')
    setUser(null)
    setIsLoggedIn(false)
    setTogg(false)
    navigate('/')
  }, [user, navigate])

  const value = {
    Togg, setTogg, user, setUser, isLoggedIn, setIsLoggedIn, loading,
    sessionId, logout, login, updateQuantity, clearCart, foodData,
    fetchFoodData, foodError, cartCount, displayCart,
  }

  return <GlobalStateContext.Provider value={value}>{children}</GlobalStateContext.Provider>
}
