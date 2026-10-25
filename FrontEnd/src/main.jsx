import './styles/savora-theme.css'
import './styles/savora-extended.css'
import { createRoot } from 'react-dom/client'
import React from 'react'
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom'
import App from './App'
import AboutPage from './components/AboutPage'
import LoginPage from './components/LoginPage'
import CartPage from './components/CartPage'
import HomePage from './components/HomePage'
import ProfilePage from './components/ProfilePage'
import OrdersPage from './components/Orders'
import ProtectedRoute from './components/ProtectedRoute'
import NotFoundPage from './components/NotFoundPage'

const router = createBrowserRouter([{
  path: '/', element: <App />, children: [
    { index: true, element: <HomePage /> },
    { path: 'about', element: <AboutPage /> },
    { path: 'login', element: <LoginPage /> },
    { path: 'cart', element: <CartPage /> },
    { path: 'profile', element: <ProtectedRoute><ProfilePage /></ProtectedRoute> },
    { path: 'orders', element: <ProtectedRoute><OrdersPage /></ProtectedRoute> },
    { path: 'home', element: <Navigate to="/" replace /> },
    { path: 'menu', element: <Navigate to="/#items" replace /> },
    { path: '*', element: <NotFoundPage /> },
  ],
}])

createRoot(document.getElementById('root')).render(
  <React.StrictMode><RouterProvider router={router} /></React.StrictMode>
)
