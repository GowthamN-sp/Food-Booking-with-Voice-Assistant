import { useEffect, useMemo, useState, useContext } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowLeft, Banknote, Minus, Plus, Smartphone, Trash2 } from 'lucide-react'
import './CSS/Cart.css'
import { GlobalStateContext } from '../context/GlobalStateContext'
import { apiFetch } from '../config'
import { foodImageSrc, formatINR, toAmount } from '../utils/currency'

const loadRazorpay = () => new Promise((resolve, reject) => {
  if (window.Razorpay) return resolve(true)
  const existing = document.getElementById('razorpay-checkout-script')
  if (existing) {
    existing.addEventListener('load', () => resolve(true), { once: true })
    existing.addEventListener('error', () => reject(new Error('Razorpay Checkout could not be loaded.')), { once: true })
    return
  }
  const script = document.createElement('script')
  script.id = 'razorpay-checkout-script'
  script.src = 'https://checkout.razorpay.com/v1/checkout.js'
  script.async = true
  script.onload = () => resolve(true)
  script.onerror = () => { script.remove(); reject(new Error('Razorpay Checkout could not be loaded. Check your connection and try again.')) }
  document.body.appendChild(script)
})

const CartPage = () => {
  const { isLoggedIn, user, foodData, updateQuantity, clearCart, foodError } = useContext(GlobalStateContext)
  const cartItems = useMemo(() => foodData.filter(item => (Number(item.Quantity) || 0) > 0), [foodData])
  const total = useMemo(() => cartItems.reduce((sum, item) => sum + (toAmount(item.Price) ?? 0) * (Number(item.Quantity) || 0), 0), [cartItems])
  const hasInvalidPrice = cartItems.some(item => toAmount(item.Price) === null || toAmount(item.Price) <= 0)
  const [loading, setLoading] = useState(false)
  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    if (window.location.hash === '#payment-modal' && isLoggedIn && cartItems.length) setShowPaymentModal(true)
  }, [isLoggedIn, cartItems.length])

  const createOrder = async (paymentMethod) => {
    const response = await apiFetch('/create-order/', {
      method: 'POST',
      body: JSON.stringify({
        items: cartItems.map(item => ({ FoodID: Number(item.FoodID), Quantity: Number(item.Quantity) })),
        paymentMethod,
        deliveryAddress: address.trim(),
        phone: phone.replace(/[\s-]/g, ''),
      }),
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok || !data.success) throw new Error(data.error || 'Could not create your order.')
    return data
  }

  const validateCheckout = () => {
    if (!isLoggedIn || !user) {
      navigate('/login', { state: { from: { pathname: '/cart' } } })
      return false
    }
    if (!address.trim() || address.trim().length < 10) {
      setError('Enter a complete delivery address (at least 10 characters).')
      return false
    }
    if (!/^[6-9]\d{9}$/.test(phone.replace(/[\s-]/g, ''))) {
      setError('Enter a valid 10-digit Indian mobile number.')
      return false
    }
    if (!cartItems.length || hasInvalidPrice) {
      setError('Your cart contains no items or a price that needs checking. Refresh the menu and try again.')
      return false
    }
    setError('')
    return true
  }

  const handleCOD = async () => {
    if (!validateCheckout()) return
    setLoading(true)
    setError('')
    try {
      const data = await createOrder('COD')
      setShowPaymentModal(false)
      window.location.hash = ''
      const cleared = await clearCart()
      navigate('/orders', { state: { notice: cleared ? `Order ${data.orderId} placed successfully.` : `Order ${data.orderId} was placed, but your cart could not be cleared. Review My Orders before trying checkout again.` } })
    } catch (err) {
      setError(err.message || 'Could not place your order.')
      setShowPaymentModal(true)
    } finally {
      setLoading(false)
    }
  }

  const handleRazorpay = async () => {
    if (!validateCheckout()) return
    setLoading(true)
    setError('')
    try {
      const order = await createOrder('RAZORPAY')
      if (!order.keyId || !order.razorpayOrderId || !order.amountPaise) throw new Error('The server did not return a complete Razorpay order. Check payment configuration.')
      await loadRazorpay()
      const checkout = new window.Razorpay({
        key: order.keyId,
        amount: order.amountPaise,
        currency: order.currency || 'INR',
        name: 'Savora',
        description: `Food order ${order.orderId}`,
        order_id: order.razorpayOrderId,
        prefill: { name: user?.name || '', email: user?.email || '', contact: phone.replace(/[\s-]/g, '') },
        notes: { savora_order_id: order.orderId },
        theme: { color: '#e6533d' },
        handler: async (gatewayResponse) => {
          setLoading(true)
          try {
            const verification = await apiFetch('/verify-payment/', {
              method: 'POST',
              body: JSON.stringify({ ...gatewayResponse, orderId: order.orderId }),
            })
            const result = await verification.json().catch(() => ({}))
            if (!verification.ok || !result.success) throw new Error(result.error || 'Payment verification is pending. Check My Orders before paying again.')
            const cleared = await clearCart()
            const notice = result.manualRefundReview
              ? `Payment was captured for ${order.orderId}, but that order is no longer fulfillable. Contact Savora support for refund/reconciliation before placing another order.`
              : cleared
                ? `Payment confirmed for ${order.orderId}.`
                : `Payment confirmed for ${order.orderId}, but your cart could not be cleared. Review My Orders before checking out again.`
            navigate('/orders', { state: { notice } })
          } catch (err) {
            setError(err.message || 'Payment verification failed. Check My Orders before retrying.')
          } finally {
            setLoading(false)
          }
        },
        modal: { ondismiss: () => setLoading(false) },
      })
      checkout.on('payment.failed', (response) => {
        const description = response?.error?.description
        setError(description ? `Payment was not completed: ${description}` : 'Payment was not completed. Your cart is unchanged.')
        setLoading(false)
      })
      checkout.open()
    } catch (err) {
      setError(err.message || 'Could not start online payment.')
      setLoading(false)
    }
  }

  return (
    <main className="cart-container savora-cart-page">
      <div className="cart-page-heading"><span className="savora-eyebrow">YOUR SELECTION</span><h1>Your cart</h1><p>Review your items and delivery details before checkout.</p></div>
      {(error || foodError) && <div className="cart-alert" role="alert"><AlertCircle size={18} aria-hidden="true" /><span>{error || foodError}</span></div>}
      {!cartItems.length ? (
        <section className="empty-cart savora-empty-cart"><div className="empty-cart-icon"><ShoppingBagFallback /></div><h2>Your cart is waiting for something delicious.</h2><p>Browse the menu and add a few favourites. Your cart will stay available while you explore.</p><button type="button" onClick={() => navigate('/#items')}>Explore the menu <span aria-hidden="true">→</span></button></section>
      ) : (
        <div className="savora-cart-layout">
          <section className="cart-items savora-cart-items" aria-label="Cart items">
            {cartItems.map(item => {
              const quantity = Math.max(0, Number(item.Quantity) || 0)
              const unitPrice = toAmount(item.Price)
              return <article key={item.FoodID} className="cart-item savora-cart-item">
                <img src={foodImageSrc(item.ImageName)} alt={item.FoodName} loading="lazy" onError={event => { event.currentTarget.onerror = null; event.currentTarget.src = '/food/default-food.svg' }} />
                <div className="cart-item-details"><span className="cart-item-category">{item.Category || 'Menu item'}</span><h3>{item.FoodName}</h3><p>{unitPrice === null ? 'Price unavailable' : formatINR(unitPrice)} <span>each</span></p></div>
                <div className="cart-item-quantity"><button type="button" onClick={() => updateQuantity(item.FoodID, -1)} aria-label={`Remove one ${item.FoodName}`} disabled={loading}><Minus size={15} /></button><span>{quantity}</span><button type="button" onClick={() => updateQuantity(item.FoodID, 1)} aria-label={`Add one ${item.FoodName}`} disabled={loading}><Plus size={15} /></button></div>
                <strong className="cart-item-total">{unitPrice === null ? '—' : formatINR(unitPrice * quantity)}</strong>
                <button type="button" className="remove-btn savora-remove-btn" onClick={() => updateQuantity(item.FoodID, -quantity)} aria-label={`Remove ${item.FoodName}`} disabled={loading}><Trash2 size={16} /><span>Remove</span></button>
              </article>
            })}
            <button type="button" className="cart-back-link" onClick={() => navigate('/#items')}><ArrowLeft size={16} /> Continue browsing</button>
          </section>
          <aside className="savora-checkout-card">
            <h2>Delivery details</h2>
            <label className="savora-field"><span>Delivery address</span><textarea value={address} onChange={event => setAddress(event.target.value)} placeholder="House / flat, street, area, city, PIN code" minLength={10} maxLength={500} rows={3} required /></label>
            <label className="savora-field"><span>Mobile number</span><input type="tel" inputMode="numeric" autoComplete="tel-national" value={phone} onChange={event => setPhone(event.target.value)} placeholder="10-digit Indian mobile number" maxLength={14} required /></label>
            <div className="savora-summary"><div><span>Items ({cartItems.reduce((sum, item) => sum + (Number(item.Quantity) || 0), 0)})</span><strong>{formatINR(total)}</strong></div><div className="summary-note">Delivery fees, if applicable, are calculated by the service. No fee is added by this screen.</div><div className="summary-total"><span>Estimated total</span><strong>{hasInvalidPrice ? '—' : formatINR(total)}</strong></div><p className="summary-note">The server recalculates the payable amount from the current menu prices at checkout.</p></div>
            <button type="button" className="checkout-btn savora-checkout-btn" onClick={() => { if (validateCheckout()) { setShowPaymentModal(true); window.location.hash = 'payment-modal' } }} disabled={loading || hasInvalidPrice}>{loading ? 'Processing…' : 'Continue to payment'}</button>
          </aside>
        </div>
      )}
      {showPaymentModal && <div className="payment-modal savora-payment-modal" id="payment-modal" role="dialog" aria-modal="true" aria-labelledby="payment-title"><div className="payment-modal-content"><span className="savora-eyebrow">SECURE CHECKOUT</span><h2 id="payment-title">Choose how to pay</h2><p className="payment-modal-total">Estimated total <strong>{formatINR(total)}</strong></p><button className="payment-option cod" type="button" onClick={handleCOD} disabled={loading}><Banknote size={19} aria-hidden="true" /><span><strong>Cash on Delivery</strong><small>Pay when your order arrives</small></span></button><button className="payment-option upi" type="button" onClick={handleRazorpay} disabled={loading}><Smartphone size={19} aria-hidden="true" /><span><strong>Pay online with Razorpay</strong><small>UPI, cards and methods enabled in your Razorpay account</small></span></button><button className="payment-option cancel" type="button" onClick={() => { setShowPaymentModal(false); window.location.hash = '' }} disabled={loading}>Back to cart</button>{loading && <p className="payment-processing" role="status">Preparing your order. Please don't refresh this page.</p>}</div></div>}
    </main>
  )
}

const ShoppingBagFallback = () => <span aria-hidden="true">▢</span>
export default CartPage
