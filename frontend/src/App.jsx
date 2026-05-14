import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout';
import {
  Dashboard,
  Vacancies,
  VacancyDetail,
  Candidates,
  CandidateDetail,
  Matching,
  Parser,
  Skills,
} from './pages';

// Создаём Query Client для кэширования
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 30000, // 30 секунд
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            {/* Dashboard */}
            <Route path="/" element={<Dashboard />} />
            
            {/* Vacancies */}
            <Route path="/vacancies" element={<Vacancies />} />
            <Route path="/vacancies/:id" element={<VacancyDetail />} />
            
            {/* Candidates */}
            <Route path="/candidates" element={<Candidates />} />
            <Route path="/candidates/:id" element={<CandidateDetail />} />
            
            {/* Matching */}
            <Route path="/matching/:vacancyId" element={<Matching />} />
            
            {/* Parser */}
            <Route path="/parser" element={<Parser />} />
            
            {/* Skills */}
            <Route path="/skills" element={<Skills />} />
            
            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}





