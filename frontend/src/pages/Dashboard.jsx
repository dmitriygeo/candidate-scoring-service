import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { statsApi } from '../api/client';
import { Spinner, Card, Button } from '../components/ui';

export default function Dashboard() {
  const { data: stats, isLoading, error, refetch } = useQuery({
    queryKey: ['stats'],
    queryFn: () => statsApi.getStats().then(res => res.data),
    refetchInterval: 30000, // Обновление каждые 30 секунд
  });

  if (isLoading) return <Spinner size="lg" />;
  
  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">Ошибка загрузки: {error.message}</p>
        <Button onClick={() => refetch()}>Повторить</Button>
      </div>
    );
  }

  const statCards = [
    { 
      label: 'Вакансий', 
      value: stats?.vacancies_count || 0, 
      icon: '💼', 
      link: '/vacancies', 
      color: 'bg-blue-500',
      description: 'Всего в базе данных'
    },
    { 
      label: 'Кандидатов', 
      value: stats?.candidates_count || 0, 
      icon: '👥', 
      link: '/candidates', 
      color: 'bg-green-500',
      description: 'Резюме загружено'
    },
    { 
      label: 'Навыков', 
      value: stats?.skills_count || 0, 
      icon: '🎯', 
      link: '/skills', 
      color: 'bg-purple-500',
      description: 'В словаре системы'
    },
    { 
      label: 'Матчей', 
      value: stats?.matches_count || 0, 
      icon: '🔗', 
      color: 'bg-orange-500',
      description: 'Проведено сопоставлений'
    },
  ];

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Дашборд</h1>
        <p className="text-gray-500 mt-1">Обзор системы скоринга кандидатов</p>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => (
          <Link
            key={stat.label}
            to={stat.link || '#'}
            className="group"
          >
            <Card hover className="relative overflow-hidden">
              <div className={`absolute top-0 right-0 w-24 h-24 ${stat.color} opacity-10 rounded-full -mr-8 -mt-8 group-hover:scale-150 transition-transform duration-300`} />
              <div className="flex items-center justify-between relative">
                <div>
                  <p className="text-gray-500 text-sm">{stat.label}</p>
                  <p className="text-3xl font-bold mt-1 text-gray-900">
                    {stat.value.toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">{stat.description}</p>
                </div>
                <div className="text-4xl">{stat.icon}</div>
              </div>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <Card>
        <h2 className="text-xl font-semibold mb-6">Быстрые действия</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/parser">
            <div className="p-6 bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 transition-all duration-200 card-hover">
              <div className="text-3xl mb-3">🔄</div>
              <h3 className="font-semibold text-lg">Спарсить данные</h3>
              <p className="text-blue-100 text-sm mt-1">Загрузить вакансии и резюме с HH.ru</p>
            </div>
          </Link>
          
          <Link to="/vacancies">
            <div className="p-6 bg-gradient-to-br from-green-500 to-green-600 text-white rounded-xl hover:from-green-600 hover:to-green-700 transition-all duration-200 card-hover">
              <div className="text-3xl mb-3">🎯</div>
              <h3 className="font-semibold text-lg">Найти кандидатов</h3>
              <p className="text-green-100 text-sm mt-1">Выбрать вакансию для матчинга</p>
            </div>
          </Link>
          
          <Link to="/skills">
            <div className="p-6 bg-gradient-to-br from-purple-500 to-purple-600 text-white rounded-xl hover:from-purple-600 hover:to-purple-700 transition-all duration-200 card-hover">
              <div className="text-3xl mb-3">📝</div>
              <h3 className="font-semibold text-lg">Анализ навыков</h3>
              <p className="text-purple-100 text-sm mt-1">Нормализовать и извлечь навыки</p>
            </div>
          </Link>
        </div>
      </Card>

      {/* System Status */}
      <Card className="mt-6">
        <h2 className="text-xl font-semibold mb-4">Статус системы</h2>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse" />
          <span className="text-green-600 font-medium">Система работает нормально</span>
        </div>
        <p className="text-gray-500 text-sm mt-2">
          Backend API: {import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}
        </p>
      </Card>
    </div>
  );
}





