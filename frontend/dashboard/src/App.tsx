import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { DashboardPage } from './pages/DashboardPage'
import { GeneratePage } from './pages/GeneratePage'
import { TasksPage } from './pages/TasksPage'
import { TaskDetailsPage } from './pages/TaskDetailsPage'
import { OptimizePage } from './pages/OptimizePage'
import { LoginPage } from './pages/LoginPage'
import { ProfilePage } from './pages/ProfilePage'
import { GigachatPage } from './pages/GigachatPage'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <ProfilePage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <DashboardPage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/generate"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <GeneratePage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <TasksPage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks/:taskId"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <TaskDetailsPage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/optimize"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <OptimizePage />
                </div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/gigachat"
            element={
              <ProtectedRoute>
                <div className="page-transition">
                  <GigachatPage />
                </div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App

