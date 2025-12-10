import { ReactNode, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getStoredCredentials } from '../api/auth'

interface ProtectedRouteProps {
  children: ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const navigate = useNavigate()
  const credentials = getStoredCredentials()

  useEffect(() => {
    if (!credentials) {
      navigate('/login')
    }
  }, [credentials, navigate])

  if (!credentials) {
    return null
  }

  return <>{children}</>
}

