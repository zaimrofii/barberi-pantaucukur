import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/dashboard';
import SessionHistory from './pages/session-history';
import AnalyticsPage from './pages/analytic-page';

function App() {
  return (
    <Router>

      {/* Area Konten yang berubah-ubah */}
      <div>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/session-history" element={<SessionHistory />} />
          <Route path="/analytic-page" element={<AnalyticsPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;