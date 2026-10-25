import { Link } from 'react-router-dom'
import { ArrowUpRight, Mic, ShoppingBag, Utensils } from 'lucide-react'
import './CSS/Footer.css'

const Footer = () => (
  <footer className="outerFooter savora-footer">
    <div className="Footer">
      <div className="footer-brand-block">
        <Link to="/" className="savora-wordmark" aria-label="Savora home">Savora<span>.</span></Link>
        <p>Good food. Your way. Browse the menu, place an order, or let Echo help you find your next favourite.</p>
        <span className="footer-assistant-note"><Mic size={16} aria-hidden="true" /> Meet Echo by Savora</span>
      </div>
      <div className="FooterContent">
        <section className="FooterSection"><h3>Discover</h3><ul><li><Link to="/#items"><Utensils size={15} aria-hidden="true" /> Menu</Link></li><li><Link to="/about">About Savora</Link></li><li><Link to="/cart"><ShoppingBag size={15} aria-hidden="true" /> Your cart</Link></li></ul></section>
        <section className="FooterSection"><h3>Your account</h3><ul><li><Link to="/login">Sign in / Sign up</Link></li><li><Link to="/orders">My orders</Link></li><li><Link to="/profile">Profile</Link></li></ul></section>
        <section className="FooterSection"><h3>Project information</h3><ul><li><a href="https://razorpay.com/docs/" target="_blank" rel="noreferrer">Payment help <ArrowUpRight size={14} aria-hidden="true" /></a></li><li><a href="https://www.djangoproject.com/" target="_blank" rel="noreferrer">Built with Django <ArrowUpRight size={14} aria-hidden="true" /></a></li></ul></section>
      </div>
      <div className="FooterBottom"><p>© {new Date().getFullYear()} Savora. A food-ordering project with voice-assisted interaction.</p><p>Prices are shown in Indian rupees (₹).</p></div>
    </div>
  </footer>
)

export default Footer
