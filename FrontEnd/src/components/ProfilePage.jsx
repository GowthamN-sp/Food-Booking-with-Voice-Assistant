import { useEffect, useState, useCallback, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { ClipboardList, LogOut, Mail, Package, RefreshCw, UserRound } from 'lucide-react'
import './CSS/Profile.css'
import { GlobalStateContext } from '../context/GlobalStateContext'
import { apiFetch } from '../config'
import { formatINR } from '../utils/currency'

const ProfilePage = () => {
  const { user, logout } = useContext(GlobalStateContext)
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('profile')
  const navigate = useNavigate()
  const fetchOrders = useCallback(async () => {
    try {
      const response = await apiFetch(`/orders/${user?.user_id}/`)
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !Array.isArray(data)) throw new Error(data.error || 'Unable to retrieve your orders.')
      setOrders(data); setError('')
    } catch (err) { setError(err.message || 'Unable to retrieve your orders.') }
    finally { setLoading(false) }
  }, [user?.user_id])
  useEffect(() => { fetchOrders() }, [fetchOrders])

  return <main className="profile-container savora-profile-page">
    <header className="profile-header savora-profile-header"><div className="profile-avatar">{user?.name?.trim()?.charAt(0)?.toUpperCase() || <UserRound />}</div><div className="profile-info"><span className="savora-eyebrow">YOUR ACCOUNT</span><h1>{user?.name || 'Savora customer'}</h1><p className="profile-email"><Mail size={15} aria-hidden="true" /> {user?.email}</p></div><button type="button" className="logout-btn savora-logout-btn" onClick={logout}><LogOut size={16} /> Sign out</button></header>
    {error && <div className="savora-order-error" role="alert"><span>{error}</span><button type="button" onClick={() => { setLoading(true); fetchOrders() }}><RefreshCw size={15} /> Retry</button></div>}
    <nav className="profile-tabs" aria-label="Profile sections"><button type="button" className={`tab-btn ${activeTab === 'profile' ? 'active' : ''}`} onClick={() => setActiveTab('profile')}>Profile details</button><button type="button" className={`tab-btn ${activeTab === 'orders' ? 'active' : ''}`} onClick={() => setActiveTab('orders')}>Order history ({orders.length})</button></nav>
    <section className="profile-content">{activeTab === 'profile' ? <div className="profile-details"><h2>Account overview</h2><div className="info-grid"><div className="info-item"><label>Full name</label><p>{user?.name || 'Not available'}</p></div><div className="info-item"><label>Email address</label><p>{user?.email || 'Not available'}</p></div><div className="info-item"><label>Total orders</label><p>{loading ? '…' : orders.length}</p></div></div><p className="profile-account-note">Keep your account details private. Password changes and profile editing are not available until a verified backend endpoint is configured.</p><div className="profile-actions"><button type="button" className="logout-btn" onClick={() => navigate('/orders')}><ClipboardList size={16} /> View my orders</button></div></div> : <div className="profile-orders"><h2>Recent orders</h2>{loading ? <div className="orders-loading">Loading orders…</div> : !orders.length ? <div className="no-orders"><Package size={22} /><p>You have not placed an order yet.</p><button type="button" onClick={() => navigate('/#items')}>Browse menu</button></div> : <div className="orders-list">{orders.slice(0, 10).map(order => <article key={order.order_id} className="order-card"><div className="order-header"><span className="order-id">Order #{order.order_id}</span><span className="order-date">{order.order_date ? new Date(order.order_date).toLocaleDateString('en-IN') : '—'}</span></div><div className="order-items">{(order.items || []).map((item,index) => <div key={`${item.food_id || item.name}-${index}`} className="order-item"><span>{item.name || item.FoodName}</span><span>×{Number(item.quantity ?? item.Quantity) || 1}</span><span>{formatINR(item.price ?? item.Price)}</span></div>)}</div><div className="order-footer"><span className="order-total">Total: {formatINR(order.total_amount)}</span><span className={`order-status status-${String(order.order_status || 'placed').replace(/_/g, '-').replace(/[^a-z-]/g, '')}`}>{String(order.order_status || 'placed').replaceAll('-', ' ')}</span></div></article>)}</div>}</div>}</section>
  </main>
}
export default ProfilePage
