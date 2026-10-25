const indianRupees = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
})

export const toAmount = (value) => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null
  }

  if (typeof value !== 'string' || value.trim() === '') {
    return null
  }

  const amount = Number(value)
  return Number.isFinite(amount) ? amount : null
}

export const formatINR = (value) => {
  const amount = toAmount(value)
  return amount === null ? '—' : indianRupees.format(amount)
}


/** Resolve legacy database image names consistently from every route. */
export const foodImageSrc = (value) => {
  const raw = String(value || '').trim().replace(/\\/g, '/')
  if (!raw) return '/food/default-food.svg'
  if (/^https?:\/\//i.test(raw)) return raw
  if (raw.startsWith('/')) return raw
  return `/${raw.replace(/^\.\//, '')}`
}
