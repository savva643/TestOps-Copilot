import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DashboardPage } from './pages/DashboardPage'
import { GeneratePage } from './pages/GeneratePage'
import { TasksPage } from './pages/TasksPage'
import { TaskDetailsPage } from './pages/TaskDetailsPage'
import { OptimizePage } from './pages/OptimizePage'
import { LoginPage } from './pages/LoginPage'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/generate" element={<GeneratePage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/tasks/:taskId" element={<TaskDetailsPage />} />
          <Route path="/optimize" element={<OptimizePage />} />
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App

