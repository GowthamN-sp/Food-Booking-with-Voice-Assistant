import { useState, useContext, useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Eye, EyeOff, LockKeyhole, Mail, UserRound } from 'lucide-react'
import './CSS/Login.css'
import { GlobalStateContext } from '../context/GlobalStateContext'
import { apiFetch } from '../config'

const LoginPage = () => {
  const [isLogin, setIsLogin] = useState(true)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { login, isLoggedIn } = useContext(GlobalStateContext)
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/'

  useEffect(() => {
    if (isLoggedIn) navigate(from, { replace: true })
  }, [isLoggedIn, navigate, from])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setError('')
    try {
      const endpoint = isLogin ? '/login/' : '/signup/'
      const response = await apiFetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isLogin ? { email: email.trim(), password } : { name: name.trim(), email: email.trim(), password }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.success) throw new Error(data.error || 'Unable to continue. Please try again.')
      await login(data.user, data.token)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Could not connect to Savora. Check that the backend is running.')
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoggedIn) return null

  return (
    <main className="login-container savora-login-page">
      <section className="login-intro">
        <span className="savora-eyebrow">WELCOME TO SAVORA</span>
        <h1>Good food is closer than you think.</h1>
        <p>Sign in to manage your orders, keep your cart connected to your account, and enjoy voice-assisted ordering with Echo.</p>
        <Link to="/" className="login-back-link">Explore the menu first <span aria-hidden="true">→</span></Link>
      </section>
      <form onSubmit={handleSubmit} className="login-card" noValidate>
        <div className="login-card-heading">
          <span className="login-mark"><LockKeyhole size={22} aria-hidden="true" /></span>
          <h2>{isLogin ? 'Welcome back' : 'Create your account'}</h2>
          <p>{isLogin ? 'Sign in to continue to Savora.' : 'A few details to get started.'}</p>
        </div>
        {error && <div className="error-message" role="alert">{error}</div>}
        {!isLogin && (
          <label className="savora-field">
            <span>Full name</span>
            <span className="savora-input-wrap"><UserRound size={17} aria-hidden="true" /><input type="text" autoComplete="name" placeholder="Your name" value={name} onChange={e => setName(e.target.value)} minLength={2} maxLength={100} required /></span>
          </label>
        )}
        <label className="savora-field">
          <span>Email address</span>
          <span className="savora-input-wrap"><Mail size={17} aria-hidden="true" /><input type="email" autoComplete="email" placeholder="you@example.com" value={email} onChange={e => setEmail(e.target.value)} maxLength={100} required /></span>
        </label>
        <label className="savora-field">
          <span>Password</span>
          <span className="savora-input-wrap"><LockKeyhole size={17} aria-hidden="true" /><input type={showPassword ? 'text' : 'password'} autoComplete={isLogin ? 'current-password' : 'new-password'} placeholder={isLogin ? 'Enter your password' : 'At least 8 characters'} value={password} onChange={e => setPassword(e.target.value)} minLength={isLogin ? 1 : 8} maxLength={128} required /><button type="button" className="password-visibility" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(v => !v)}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></span>
        </label>
        <button type="submit" className="login-button" disabled={submitting}>{submitting ? 'Please wait…' : isLogin ? 'Sign in' : 'Create account'}</button>
        <p className="login-toggle">{isLogin ? 'New to Savora?' : 'Already have an account?'} <button type="button" onClick={() => { setIsLogin(v => !v); setError('') }}>{isLogin ? 'Create an account' : 'Sign in'}</button></p>
        <p className="login-security-note">Your password is processed by the Savora backend; never share it with the voice assistant.</p>
      </form>
    </main>
  )
}

export default LoginPage
