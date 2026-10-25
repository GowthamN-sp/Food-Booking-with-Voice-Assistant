import { Link } from 'react-router-dom'
import { Mic, ShoppingCart, Utensils } from 'lucide-react'
import './CSS/About.css'

const AboutPage = () => (
  <main className="about-container savora-about">
    <section className="about-header">
      <span className="savora-eyebrow">A BETTER WAY TO ORDER</span>
      <h1>Meet Savora</h1>
      <p>Good food. Your way. Browse the menu, manage your cart, and try voice-assisted ordering with Echo.</p>
      <Link to="/"><button className="HeroButtonPrimary">Explore the menu →</button></Link>
    </section>
    <section className="about-content savora-about-grid">
      <article className="about-section"><span className="savora-about-icon"><Utensils aria-hidden="true" /></span><h2>Discover your next favourite</h2><p>Explore the available menu, browse categories, and see item details and prices before adding dishes to your cart.</p></article>
      <article className="about-section"><span className="savora-about-icon"><ShoppingCart aria-hidden="true" /></span><h2>Ordering made clearer</h2><p>Manage quantities, review your cart, and continue through the checkout experience supported by this project.</p></article>
      <article className="about-section"><span className="savora-about-icon"><Mic aria-hidden="true" /></span><h2>Say hello to Echo</h2><p>Use the voice assistant to try supported commands for menu discovery and cart actions. Available commands depend on the assistant&apos;s current capabilities.</p></article>
    </section>
    <section className="about-section savora-story"><h2>Built around a simple idea</h2><p>Savora is a food-ordering project that brings together a React interface, a Django backend, and voice-assisted interaction. The goal is to make browsing and ordering feel straightforward, with a consistent experience from menu to cart.</p><p>Designed with care, improved through testing, and focused on making everyday food ordering easier.</p></section>
  </main>
)

export default AboutPage
