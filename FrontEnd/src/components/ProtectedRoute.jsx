import { useContext } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { GlobalStateContext } from '../context/GlobalStateContext'

const ProtectedRoute = ({ children }) => {
  const { isLoggedIn, loading } = useContext(GlobalStateContext)
  const location = useLocation()
  if (loading) return <main className="route-loading" role="status">Loading your Savora account…</main>
  if (!isLoggedIn) return <Navigate to="/login" replace state={{ from: { pathname: location.pathname } }} />
  return children
}

export default ProtectedRoute
