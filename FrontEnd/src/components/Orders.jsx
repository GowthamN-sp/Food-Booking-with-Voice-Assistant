import { useCallback, useEffect, useState, useContext } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Bike, ChefHat, CircleCheck, Clock3, ClipboardList, Package, RefreshCw, Utensils } from 'lucide-react'
import './CSS/Orders.css'
import { apiFetch } from '../config'
import { GlobalStateContext } from '../context/GlobalStateContext'
import { formatINR } from '../utils/currency'

const statusIcon = status => {
  const props = { size: 16, 'aria-hidden': true }
  switch (status) {
    case 'confirmed': return <CircleCheck {...props} />
    case 'preparing': return <ChefHat {...props} />
    case 'out-for-delivery': return <Bike {...props} />
    case 'delivered': return <Utensils {...props} />
    case 'cancelled': return <Package {...props} />
    default: return <ClipboardList {...props} />
  }
}
const statusClass = status => `status-${String(status || 'placed').toLowerCase().replace(/_/g, '-').replace(/[^a-z-]/g, '')}`

const OrdersPage = () => {
  const { user } = useContext(GlobalStateContext)
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const notice = location.state?.notice

  const fetchOrders = useCallback(async () => {
    try {
      const response = await apiFetch(`/orders/${user?.user_id}/`)
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Could not load order history.')
      if (!Array.isArray(data)) throw new Error('Unexpected response from the order service.')
      setOrders(data)
      setError('')
    } catch (err) {
      setError(err.message || 'Could not load orders. Please retry.')
    } finally {
      setLoading(false)
    }
  }, [user?.user_id])

  useEffect(() => {
    fetchOrders()
    const intervalId = window.setInterval(fetchOrders, 30000)
    return () => window.clearInterval(intervalId)
  }, [fetchOrders])

  return (
    <main className="orders-container savora-orders-page">
      <header className="orders-page-heading"><span className="savora-eyebrow">YOUR SAVORA ACTIVITY</span><h1>My orders</h1><p>See order items, payment state, and the latest available fulfillment status.</p></header>
      {notice && <div className="savora-success-message" role="status"><CircleCheck size={18} />{notice}</div>}
      {error && <div className="savora-order-error" role="alert"><span>{error}</span><button type="button" onClick={() => { setLoading(true); fetchOrders() }}><RefreshCw size={15} /> Retry</button></div>}
      {loading ? <div className="orders-loading" role="status"><Clock3 size={20} />Loading your orders…</div> : orders.length === 0 ? (
        <section className="no-orders savora-no-orders"><span className="empty-order-icon"><Package size={28} /></span><h2>No orders yet</h2><p>Your next favourite meal is waiting in the menu.</p><button type="button" onClick={() => navigate('/#items')}>Browse the menu <span aria-hidden="true">→</span></button></section>
      ) : <div className="orders-list">{orders.map(order => {
        const items = Array.isArray(order.items) ? order.items : []
        const status = order.order_status || 'placed'
        return <article key={order.order_id} className="order-card savora-order-card">
          <div className="order-header"><div><span className="order-id">Order #{order.order_id}</span><span className="order-date">{order.order_date ? new Date(order.order_date).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : 'Date unavailable'}</span></div><span className={`order-status ${statusClass(status)}`}>{statusIcon(status)} {String(status).replaceAll('-', ' ')}</span></div>
          <div className="order-items">{items.map((item, index) => <div key={`${item.food_id || item.name}-${index}`} className="order-item"><span className="item-name">{item.name || item.FoodName || 'Menu item'}</span><span className="item-quantity">×{Number(item.quantity ?? item.Quantity) || 1}</span><span className="item-price">{formatINR(item.price ?? item.Price)}</span></div>)}</div>
          {order.delivery_address && <p className="order-delivery-address"><strong>Deliver to:</strong> {order.delivery_address}</p>}
          <div className="order-footer"><div className="order-total">Total: <span>{formatINR(order.total_amount)}</span></div><div className="order-payment"><span>{order.payment_method === 'COD' ? 'Cash on Delivery' : 'Razorpay'}</span><small className={`payment-status payment-${String(order.payment_status || 'pending').replace(/[^a-z_]/g, '')}`}>{String(order.payment_status || 'pending').replaceAll('_', ' ')}</small></div></div>
        </article>
      })}</div>}
      <p className="orders-refresh-note"><RefreshCw size={13} /> Order status refreshes every 30 seconds while this page is open.</p>
    </main>
  )
}
export default OrdersPage
