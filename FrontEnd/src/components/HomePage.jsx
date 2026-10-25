import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './CSS/Hero.css'
import ItemsPage from './ItemsPage'

const HomePage = () => {
  const location = useLocation()
  useEffect(() => {
    if (location.hash === '#items') {
      const timer = window.setTimeout(() => document.getElementById('items')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120)
      return () => window.clearTimeout(timer)
    }
  }, [location.hash])
  return (
  <>
    <section className="outerHero savora-hero">
      <div className="Hero">
        <div className="HeroContent">
          <span className="savora-eyebrow">GOOD FOOD. YOUR WAY.</span>
          <h1><span className="line">Good food.</span><span className="line"><span className="gradient-text">Happier</span></span><span className="line">moments.</span></h1>
          <p>Discover your next favourite meal, add it to your cart, and make ordering easier with Echo, your voice-powered food assistant.</p>
          <div className="HeroButtons">
            <a href="#items" className="HeroButtonPrimary">Explore the menu <span aria-hidden="true">→</span></a>
            <Link to="/about" className="HeroButton">How Savora works</Link>
          </div>
          <div className="HeroFeatures" aria-label="Savora features">
            <div className="feature-item"><span className="feature-number">Fresh choices</span><span className="feature-label">Explore the menu</span></div>
            <div className="feature-item"><span className="feature-number">Easy ordering</span><span className="feature-label">Cart and checkout</span></div>
            <div className="feature-item"><span className="feature-number">Meet Echo</span><span className="feature-label">Voice-assisted ordering</span></div>
          </div>
        </div>
        <div className="HeroImage">
          <div className="blob-1" aria-hidden="true"></div><div className="blob-2" aria-hidden="true"></div>
          <img
          src="/food/south-indian-thali.jpg"
          alt="Fresh, colourful meal prepared for you"
          loading="eager"
        />
        <div className="savora-image-note"><span>✦</span><div><strong>Something delicious</strong><small>Just a few clicks away</small></div></div>
        </div>
      </div>
    </section>
    <ItemsPage />
  </>
  )
}

export default HomePage
