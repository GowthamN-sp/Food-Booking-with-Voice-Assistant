import { useMemo, useState, useContext, useEffect } from 'react'
import { AlertCircle, CakeSlice, CookingPot, CupSoda, Minus, Pizza, Plus, RefreshCw, Search, Sandwich, Soup, Utensils } from 'lucide-react'
import './CSS/Items.css'
import { GlobalStateContext } from '../context/GlobalStateContext'
import { formatINR, foodImageSrc, toAmount } from '../utils/currency'

const categoryIcons = {
  All: Utensils,
  Pizza,
  Burger: Sandwich,
  'Main Course': CookingPot,
  Snacks: Soup,
  'South Indian': CookingPot,
  Dessert: CakeSlice,
  Drinks: CupSoda,
}

const ItemsPage = () => {
  const { foodData, updateQuantity, loading, foodError, fetchFoodData } = useContext(GlobalStateContext)
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [searchTerm, setSearchTerm] = useState('')
  const categories = useMemo(() => ['All', ...new Set(foodData.map(item => item.Category).filter(Boolean))], [foodData])

  useEffect(() => {
    const filterFromVoice = event => {
      const requested = String(event.detail?.category || '')
      const matched = categories.find(category => category.toLowerCase() === requested.toLowerCase())
      if (matched) setSelectedCategory(matched)
      document.getElementById('items')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
    window.addEventListener('savora:filter-category', filterFromVoice)
    return () => window.removeEventListener('savora:filter-category', filterFromVoice)
  }, [categories])

  const filteredItems = useMemo(() => {
    const query = searchTerm.trim().toLowerCase()
    return foodData.filter(item => {
      const categoryMatch = selectedCategory === 'All' || item.Category === selectedCategory
      const searchMatch = !query || [item.FoodName, item.Description, item.Category].some(value => String(value || '').toLowerCase().includes(query))
      return categoryMatch && searchMatch
    })
  }, [foodData, selectedCategory, searchTerm])

  return (
    <section className="menu-section savora-menu-section" id="items" aria-labelledby="menu-title">
      <div className="menu-heading">
        <div><span className="menu-eyebrow">THE SAVORA MENU</span><h2 id="menu-title">Find your <span>favourite.</span></h2><p>Browse the menu, check current prices, and add dishes to your cart.</p></div>
        <div className="menu-count"><strong>{filteredItems.length}</strong><span>{filteredItems.length === 1 ? 'dish' : 'dishes'} shown</span></div>
      </div>
      <div className="menu-toolbar">
        <div className="categories-nav" aria-label="Filter food by category">
          {categories.map(category => {
            const Icon = categoryIcons[category] || Utensils
            return <button key={category} type="button" className={`category-btn ${selectedCategory === category ? 'active' : ''}`} aria-pressed={selectedCategory === category} onClick={() => setSelectedCategory(category)}><Icon size={16} aria-hidden="true" />{category}</button>
          })}
        </div>
        <label className="menu-search"><Search size={17} aria-hidden="true" /><input type="search" value={searchTerm} onChange={event => setSearchTerm(event.target.value)} placeholder="Search dishes…" aria-label="Search dishes" />{searchTerm && <button type="button" onClick={() => setSearchTerm('')} aria-label="Clear search">×</button>}</label>
      </div>
      {foodError && <div className="savora-menu-error" role="alert"><AlertCircle size={18} aria-hidden="true" /><span>{foodError}</span><button type="button" onClick={fetchFoodData}><RefreshCw size={15} aria-hidden="true" /> Retry</button></div>}
      {loading ? <div className="savora-menu-state" role="status"><span className="savora-spinner" />Loading the menu…</div> : filteredItems.length === 0 ? (
        <div className="empty-menu"><div className="empty-icon"><Utensils size={28} aria-hidden="true" /></div><h3>No dishes found</h3><p>Try a different search or category.</p><button type="button" onClick={() => { setSearchTerm(''); setSelectedCategory('All') }}>Clear filters</button></div>
      ) : (
        <div className="cards-grid">
          {filteredItems.map(item => {
            const quantity = Math.max(0, Number(item.Quantity) || 0)
            const price = toAmount(item.Price)
            const available = item.IsAvailable === undefined || Number(item.IsAvailable) === 1
            return <article key={item.FoodID} className={`card ${!available ? 'is-unavailable' : ''}`}>
              <div className="card-image"><img src={foodImageSrc(item.ImageName)} alt={item.FoodName} loading="lazy" onError={event => { event.currentTarget.onerror = null; event.currentTarget.src = '/food/default-food.svg' }} />{!available && <span className="unavailable-badge">Currently unavailable</span>}</div>
              <div className="card-content"><div className="card-meta"><span className="card-category">{item.Category || 'Menu'}</span></div><div className="card-title-row"><h3 className="card-title">{item.FoodName}</h3><span className="card-price">{price === null || price <= 0 ? 'Price unavailable' : formatINR(price)}</span></div><p className="card-description">{item.Description || 'Prepared fresh when you order.'}</p></div>
              <div className="card-footer">{!available ? <button type="button" className="add-btn" disabled>Unavailable</button> : quantity > 0 ? <div className="quantity-controls"><button type="button" className="quantity-btn" onClick={() => updateQuantity(item.FoodID, -1)} aria-label={`Remove one ${item.FoodName}`}><Minus size={16} aria-hidden="true" /></button><span className="quantity-display" aria-live="polite">{quantity}</span><button type="button" className="quantity-btn" onClick={() => updateQuantity(item.FoodID, 1)} aria-label={`Add one ${item.FoodName}`}><Plus size={16} aria-hidden="true" /></button></div> : <button type="button" className="add-btn" onClick={() => updateQuantity(item.FoodID, 1)} disabled={price === null || price <= 0}><Plus size={16} aria-hidden="true" /> Add to cart</button>}</div>
            </article>
          })}
        </div>
      )}
    </section>
  )
}

export default ItemsPage
