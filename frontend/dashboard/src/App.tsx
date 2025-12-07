import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { GeneratePage } from './pages/GeneratePage'
import { TasksPage } from './pages/TasksPage'
import { OptimizePage } from './pages/OptimizePage'

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/generate" element={<GeneratePage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/optimize" element={<OptimizePage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}

export default App

