import { useState, useContext, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, Check, LoaderCircle, Mic, MicOff, Send, ShoppingBag, Volume2, X } from 'lucide-react'
import { GlobalStateContext } from '../context/GlobalStateContext'
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition'
import { apiFetch } from '../config'
import { formatINR, toAmount } from '../utils/currency'
import './CSS/Voice.css'

const normalise = value => String(value || '').toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(/\s+/g, ' ').trim()

const VoiceAssistant = () => {
  const navigate = useNavigate()
  const { Togg, setTogg, updateQuantity, logout, foodData, isLoggedIn, user } = useContext(GlobalStateContext)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [responseText, setResponseText] = useState('I can help you find dishes, manage your cart, and navigate Savora.')
  const [inputText, setInputText] = useState('')
  const [error, setError] = useState('')
  const [pendingCommand, setPendingCommand] = useState(null)
  const [pendingPrompt, setPendingPrompt] = useState('')
  const transcriptTimer = useRef(null)
  const lastProcessed = useRef('')
  const responseRef = useRef(null)
  const { transcript, listening, resetTranscript, browserSupportsSpeechRecognition, isMicrophoneAvailable } = useSpeechRecognition()

  const speak = useCallback((message) => {
    setResponseText(message)
    if (!('speechSynthesis' in window) || !message) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(message)
    utterance.lang = 'en-IN'
    utterance.rate = 0.95
    utterance.onstart = () => setIsSpeaking(true)
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)
    window.speechSynthesis.speak(utterance)
  }, [])

  const matchFood = useCallback((name) => {
    const query = normalise(name)
    if (!query) return null
    const exact = foodData.filter(item => normalise(item.FoodName) === query)
    if (exact.length === 1) return exact[0]
    const partial = foodData.filter(item => normalise(item.FoodName).includes(query) || query.includes(normalise(item.FoodName)))
    return partial.length === 1 ? partial[0] : null
  }, [foodData])

  const executeCommand = useCallback(async (command) => {
    if (command.command === 'FILTER') {
      navigate('/')
      window.setTimeout(() => window.dispatchEvent(new CustomEvent('savora:filter-category', { detail: { category: command.category } })), 150)
      speak(`Showing ${command.category} dishes.`)
      return
    }
    if (command.command === 'NAVIGATE') {
      if (['/orders', '/profile'].includes(command.path) && !isLoggedIn) {
        navigate('/login', { state: { from: { pathname: command.path } } })
        speak('Please sign in first. I opened the sign-in page.')
        return
      }
      navigate(command.path || '/')
      if (command.path === '/#items') window.setTimeout(() => document.getElementById('items')?.scrollIntoView({ behavior: 'smooth' }), 180)
      speak(command.response || 'Opening that page.')
      return
    }
    if (command.command === 'ORDER' || command.command === 'REMOVE') {
      if (!Array.isArray(command.items) || !command.items.length) { speak('Please tell me which dish you mean.'); return }
      const changes = []
      for (const requested of command.items) {
        const food = matchFood(requested.name)
        if (!food) { speak(`I couldn't uniquely identify ${requested.name}. Please say the exact dish name.`); return }
        const qty = Math.max(1, Math.min(10, Number(requested.quantity) || 1))
        const current = Math.max(0, Number(food.Quantity) || 0)
        if (command.command === 'ORDER' && food.IsAvailable !== undefined && Number(food.IsAvailable) !== 1) { speak(`${food.FoodName} is currently unavailable.`); return }
        if (command.command === 'REMOVE' && current === 0) { speak(`${food.FoodName} isn't in your cart.`); return }
        changes.push({ food, quantity: command.command === 'REMOVE' ? -Math.min(qty, current) : qty })
      }
      for (const change of changes) {
        const ok = await updateQuantity(change.food.FoodID, change.quantity)
        if (!ok) { speak('I could not update every item. Please review your cart.'); return }
      }
      const summary = changes.map(change => `${Math.abs(change.quantity)} ${change.food.FoodName}`).join(' and ')
      speak(command.command === 'ORDER' ? `Added ${summary} to your cart.` : `Removed ${summary} from your cart.`)
      return
    }
    if (command.command === 'CART_SUMMARY') {
      const inCart = foodData.filter(item => Number(item.Quantity) > 0)
      if (!inCart.length) { speak('Your cart is empty. Ask me to find a dish or browse the menu.'); return }
      const total = inCart.reduce((sum, item) => sum + (toAmount(item.Price) || 0) * (Number(item.Quantity) || 0), 0)
      const details = inCart.map(item => `${item.Quantity} ${item.FoodName}`).join(', ')
      speak(`Your cart has ${details}. The displayed subtotal is ${formatINR(total)}. The server confirms the payable amount at checkout.`)
      return
    }
    if (command.command === 'ORDER_STATUS') {
      if (!isLoggedIn || !user) { navigate('/login', { state: { from: { pathname: '/orders' } } }); speak('Please sign in to check your orders.'); return }
      const res = await apiFetch(`/orders/${user.user_id}/`)
      const orders = await res.json()
      if (!res.ok || !Array.isArray(orders)) { speak('I could not retrieve your order status right now.'); return }
      if (!orders.length) { speak('You have not placed an order yet.'); return }
      const latest = orders[0]
      speak(`Your latest order ${latest.order_id} is ${String(latest.order_status || 'being processed').replaceAll('-', ' ')}. Payment status: ${String(latest.payment_status || 'unknown').replaceAll('_', ' ')}.`)
      return
    }
    if (command.command === 'LOGOUT') { await logout(); speak('You have signed out of Savora.'); return }
    speak(command.response || 'I did not understand that. Try saying, find pizza, add one masala dosa, show my cart, or open orders.')
  }, [navigate, speak, isLoggedIn, user, matchFood, updateQuantity, foodData, logout])

  const processVoiceCommand = useCallback(async (text) => {
    if (!text || isProcessing) return
    setIsProcessing(true)
    setError('')
    try {
      const response = await apiFetch('/voice/', { method: 'POST', body: JSON.stringify({ transcript: text }) })
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.aiResponse) throw new Error(data.error || 'Voice assistant request failed.')
      const command = data.aiResponse
      if (command.command === 'ORDER' || command.command === 'REMOVE') {
        const totalRequested = (command.items || []).reduce((sum, item) => sum + (Number(item.quantity) || 1), 0)
        if ((command.items || []).length > 1 || totalRequested > 3 || command.command === 'REMOVE' && totalRequested > 1) {
          setPendingCommand(command)
          setPendingPrompt((command.items || []).map(item => `${item.quantity} × ${item.name}`).join(', '))
          speak(`Please confirm: ${command.command === 'ORDER' ? 'add' : 'remove'} ${(command.items || []).map(item => `${item.quantity} ${item.name}`).join(' and ')}?`)
          return
        }
      }
      await executeCommand(command)
    } catch (err) {
      setError(err.message || 'Echo could not connect. You can still use the menu and cart.')
      speak('I could not process that request. Please try again or use the menu.')
    } finally {
      setIsProcessing(false)
    }
  }, [executeCommand, isProcessing, speak])

  const processTranscript = useCallback(async (text) => {
    const trimmed = String(text || '').trim()
    if (!trimmed || trimmed === lastProcessed.current) return
    lastProcessed.current = trimmed
    await processVoiceCommand(trimmed)
  }, [processVoiceCommand])

  useEffect(() => {
    if (!Togg || !transcript || !listening || isProcessing) return
    if (transcriptTimer.current) window.clearTimeout(transcriptTimer.current)
    transcriptTimer.current = window.setTimeout(() => {
      SpeechRecognition.stopListening()
      processTranscript(transcript)
    }, 1200)
    return () => { if (transcriptTimer.current) window.clearTimeout(transcriptTimer.current) }
  }, [Togg, transcript, listening, isProcessing, processTranscript])

  useEffect(() => () => {
    if (transcriptTimer.current) window.clearTimeout(transcriptTimer.current)
    window.speechSynthesis?.cancel()
    SpeechRecognition.stopListening()
  }, [])

  const startListening = () => {
    setError('')
    if (!browserSupportsSpeechRecognition) { setError('Speech recognition is not supported in this browser. Try the text command box or use Chrome.'); return }
    if (isMicrophoneAvailable === false) { setError('Microphone permission is unavailable. Check your browser permissions or use text input.'); return }
    lastProcessed.current = ''
    resetTranscript()
    window.speechSynthesis?.cancel()
    setIsSpeaking(false)
    try { SpeechRecognition.startListening({ continuous: true, language: 'en-IN' }) }
    catch { setError('Could not start the microphone. Check browser permissions and try again.') }
  }

  const submitText = async event => {
    event.preventDefault()
    const text = inputText.trim()
    if (!text || isProcessing) return
    setInputText('')
    await processVoiceCommand(text)
  }

  const confirmPending = async confirmed => {
    const command = pendingCommand
    setPendingCommand(null)
    setPendingPrompt('')
    if (!confirmed || !command) { speak('Okay, I did not change your cart.'); return }
    await executeCommand(command)
  }

  if (!Togg) return <div className="voice-assistant-floating"><button type="button" className="floating-voice-button" onClick={() => setTogg(true)} title="Open Echo by Savora" aria-label="Open Echo by Savora"><Mic className="mic-icon" aria-hidden="true" /></button></div>

  return (
    <aside className="voice-assistant-panel savora-voice-panel" aria-label="Echo voice assistant">
      <div className="voice-header"><div className="voice-header-icon"><Mic size={19} aria-hidden="true" /></div><div><h3>Echo <span>by Savora</span></h3><p className="voice-subtitle">Voice-powered food assistant</p></div><button type="button" className="voice-close-button" onClick={() => { setTogg(false); SpeechRecognition.stopListening(); window.speechSynthesis?.cancel(); setIsSpeaking(false); setPendingCommand(null) }} aria-label="Close Echo"><X size={18} /></button></div>
      <div className="voice-status" role="status">{isProcessing ? <><LoaderCircle size={16} className="voice-spin" /> Understanding your request…</> : listening ? <><span className="voice-status-dot" /> Listening in English (India)…</> : isSpeaking ? <><Volume2 size={16} /> Speaking…</> : <><span className="voice-status-dot idle" /> Ready when you are</>}</div>
      <div className="voice-conversation"><div className="assistant-message"><span className="assistant-message-label">ECHO</span><p ref={responseRef}>{responseText}</p></div>{transcript && <div className="user-transcript"><span>YOU SAID</span><p>{transcript}</p></div>}</div>
      {error && <div className="voice-error" role="alert"><AlertCircle size={16} />{error}</div>}
      {pendingCommand && <div className="voice-confirm-box"><p>Confirm cart change: <strong>{pendingPrompt}</strong></p><div><button type="button" onClick={() => confirmPending(true)}><Check size={15} /> Confirm</button><button type="button" onClick={() => confirmPending(false)}><X size={15} /> Cancel</button></div></div>}
      <div className="voice-examples"><span>TRY SAYING</span><button type="button" onClick={() => processVoiceCommand('Find pizza')}>Find pizza</button><button type="button" onClick={() => processVoiceCommand('Add one masala dosa')}>Add one masala dosa</button><button type="button" onClick={() => processVoiceCommand('Show my cart total')}>Cart total</button></div>
      <div className="voice-controls"><button type="button" className={`listen-button ${listening ? 'listening' : ''}`} onClick={() => listening ? SpeechRecognition.stopListening() : startListening()} disabled={isProcessing || Boolean(pendingCommand)}>{listening ? <MicOff size={18} /> : <Mic size={18} />}{listening ? 'Stop listening' : 'Start speaking'}</button><form className="voice-text-form" onSubmit={submitText}><input type="text" value={inputText} onChange={event => setInputText(event.target.value)} placeholder="Or type a command…" aria-label="Type a voice assistant command" maxLength={500} /><button type="submit" aria-label="Send command" disabled={isProcessing || !inputText.trim()}><Send size={17} /></button></form><button type="button" className="voice-cart-link" onClick={() => { navigate('/cart'); setTogg(false) }}><ShoppingBag size={16} /> Open cart</button></div>
    </aside>
  )
}

export default VoiceAssistant
