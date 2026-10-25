import { Link } from 'react-router-dom'
import { ArrowLeft, SearchX } from 'lucide-react'

const NotFoundPage = () => (
  <main className="savora-not-found"><span className="not-found-icon"><SearchX size={30} aria-hidden="true" /></span><span className="savora-eyebrow">404 · PAGE NOT FOUND</span><h1>This page isn't on the menu.</h1><p>The link may be outdated or the page may have moved. Let's get you back to something delicious.</p><Link to="/" className="not-found-home"><ArrowLeft size={16} aria-hidden="true" /> Back to Savora</Link></main>
)
export default NotFoundPage
