import { useContext, useState } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { ClipboardList, LogOut, Menu, ShoppingBag, UserRound, X } from 'lucide-react'
import './CSS/Navbar.css'
import { GlobalStateContext } from '../context/GlobalStateContext'

const Navbar = () => {
  const { isLoggedIn, user, logout, cartCount } = useContext(GlobalStateContext)
  const [showDropdown, setShowDropdown] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const getInitials = () => user?.name?.split(/\s+/).filter(Boolean).slice(0, 2).map(word => word[0]).join('').toUpperCase() || '?'
  const closeMenus = () => { setShowDropdown(false); setMobileOpen(false) }

  return (
    <header className="outerNavbar">
      <nav className="Navbar" aria-label="Main navigation">
        <Link to="/" className="savora-wordmark" aria-label="Savora home" onClick={closeMenus}>Savora<span>.</span></Link>
        <button type="button" className="mobile-nav-toggle" onClick={() => setMobileOpen(v => !v)} aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={mobileOpen}>{mobileOpen ? <X /> : <Menu />}</button>
        <div className={`NavButtons ${mobileOpen ? 'is-open' : ''}`}>
          <NavLink to="/" end className={({isActive}) => `navbut ${isActive ? 'active' : ''}`} onClick={closeMenus}>Home</NavLink>
          <NavLink to="/#items" className="navbut" onClick={closeMenus}>Menu</NavLink>
          <NavLink to="/about" className={({isActive}) => `navbut ${isActive ? 'active' : ''}`} onClick={closeMenus}>About</NavLink>
          <Link to="/cart" className="navbut cart-nav-link" onClick={closeMenus}><ShoppingBag size={17} aria-hidden="true" /> Cart <span className="cart-nav-count">{cartCount || 0}</span></Link>
          {isLoggedIn ? (
            <div className="user-profile">
              <button type="button" className="profile-circle" onClick={() => setShowDropdown(v => !v)} aria-label="Toggle profile menu" aria-expanded={showDropdown}>{getInitials()}</button>
              {showDropdown && <div className="profile-dropdown">
                <div className="dropdown-user-summary"><strong>{user?.name}</strong><small>{user?.email}</small></div>
                <Link to="/profile" className="dropdown-item" onClick={closeMenus}><UserRound size={18} aria-hidden="true" /> Profile</Link>
                <Link to="/orders" className="dropdown-item" onClick={closeMenus}><ClipboardList size={18} aria-hidden="true" /> My orders</Link>
                <button type="button" className="dropdown-item logout" onClick={() => { closeMenus(); logout() }}><LogOut size={18} aria-hidden="true" /> Sign out</button>
              </div>}
            </div>
          ) : <Link to="/login" className="navbutloin" onClick={closeMenus}>Sign in</Link>}
        </div>
      </nav>
    </header>
  )
}

export default Navbar
