import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Дашборд', icon: '📊' },
  { path: '/vacancies', label: 'Вакансии', icon: '💼' },
  { path: '/candidates', label: 'Кандидаты', icon: '👥' },
  { path: '/skills', label: 'Анализ навыков', icon: '🎯' },
  { path: '/parser', label: 'Парсер HH', icon: '🔄' },
];

export default function Layout({ children }) {
  const location = useLocation();

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col fixed h-full">
        <div className="p-6 border-b border-gray-800">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <span>📊</span>
            <span>Candidate Scoring</span>
          </h1>
          <p className="text-xs text-gray-400 mt-1">Система скоринга кандидатов</p>
        </div>
        
        <nav className="flex-1 px-4 py-6 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || 
              (item.path !== '/' && location.pathname.startsWith(item.path));
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                  ${isActive
                    ? 'bg-primary-600 text-white shadow-lg shadow-primary-600/30'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }
                `}
              >
                <span className="text-lg">{item.icon}</span>
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
        
        <div className="p-4 border-t border-gray-800">
          <div className="text-xs text-gray-500">
            <p>v1.0.0</p>
            <p>FastAPI Backend</p>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 ml-64">
        <div className="p-8 min-h-screen">
          {children}
        </div>
      </main>
    </div>
  );
}





