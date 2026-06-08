import React from 'react'
import './CSS/About.css'

const AboutPage = () => {
  return (
    <div className="about-container">
      <div className="about-header">
        <h1>About EchoEats</h1>
        <p>Voice Based Food Ordering System | Order with your voice, eat with pleasure</p>
      </div>

      <div className="about-content">
        <div className="highlight-section">
          <div className="highlight-badge">🚀 INNOVATION</div>
          <h2 className="highlight-title">Voice Based Food Ordering System</h2>
          <p className="highlight-description">
            EchoEats introduces a revolutionary way to order food - just use your voice! 
            Our advanced voice recognition technology allows you to browse menus, place orders, 
            and track deliveries hands-free. Simply speak your cravings and we'll handle the rest.
          </p>
          <div className="voice-features">
            <div className="voice-feature">
              <span className="voice-icon">🎤</span>
              <span>Hands-free ordering</span>
            </div>
            <div className="voice-feature">
              <span className="voice-icon">🗣️</span>
              <span>Multi-language support</span>
            </div>
            <div className="voice-feature">
              <span className="voice-icon">⚡</span>
              <span>Instant voice recognition</span>
            </div>
            <div className="voice-feature">
              <span className="voice-icon">🔊</span>
              <span>Voice confirmation</span>
            </div>
          </div>
        </div>

        <div className="about-section">
          <h2>Our Story</h2>
          <p>
            EchoEats was born from a simple idea: everyone deserves access to delicious, 
            high-quality food delivered fast and fresh. What started as a small kitchen 
            in 2020 has now grown into a trusted food delivery platform connecting 
            customers with the best restaurants in town.
          </p>
        </div>

        <div className="about-section">
          <h2>Our Mission</h2>
          <p>
            To bring restaurant-quality meals to your doorstep with unprecedented speed 
            and care. We believe that great food has the power to bring people together 
            and make every moment special.
          </p>
        </div>

        <div className="team-section">
          {/* <h2>Meet Our Team</h2> */}
          <div className="team-grid">
            <div className="team-card lead">
              <div className="team-icon">👨‍💻</div>
              <h3>Gowtham N</h3>
              <p className="team-role">Full Stack Developer</p>
              <p className="team-dept">Computer Science Engineering</p>
             
              <p className="team-desc">
                Leading the development of EchoEats with expertise in both frontend and backend technologies.
                Implemented the voice recognition system and full stack architecture.
              </p>
            </div>

           

            
          </div>
        </div>

        <div className="stats-section">
          <div className="stat-item">
            <h3>500+</h3>
            <p>Restaurant Partners</p>
          </div>
          <div className="stat-item">
            <h3>50k+</h3>
            <p>Happy Customers</p>
          </div>
          <div className="stat-item">
            <h3>20min</h3>
            <p>Avg. Delivery Time</p>
          </div>
          <div className="stat-item">
            <h3>4.8★</h3>
            <p>Customer Rating</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default AboutPage