import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { vacanciesApi, matchingApi } from '../api/client';
import { MatchResultCard } from '../components';
import { Spinner, Button, Card, Badge } from '../components/ui';
import { parseCompanyField } from '../utils/vacancyDisplay';

export default function Matching() {
  const { vacancyId } = useParams();
  const [minScore, setMinScore] = useState(0.3);
  const [limit, setLimit] = useState(20);
  
  // Загрузка вакансии
  const { data: vacancy, isLoading: loadingVacancy } = useQuery({
    queryKey: ['vacancy', vacancyId],
    queryFn: () => vacanciesApi.getById(vacancyId).then(res => res.data),
  });

  // Загрузка существующих результатов
  const { 
    data: matchResults, 
    isLoading: loadingResults,
    refetch: refetchResults 
  } = useQuery({
    queryKey: ['matchResults', vacancyId],
    queryFn: () => matchingApi.getResults(vacancyId, 0, 50).then(res => res.data),
    enabled: !!vacancyId,
  });

  // Мутация для запуска матчинга
  const matchMutation = useMutation({
    mutationFn: () => matchingApi.matchVacancy(parseInt(vacancyId), minScore, limit),
    onSuccess: () => {
      refetchResults();
    },
  });

  if (loadingVacancy) return <Spinner size="lg" />;

  const candidates = matchResults?.candidates || [];
  const company = vacancy ? parseCompanyField(vacancy.company) : { displayName: '', meta: null };

  return (
    <div className="animate-fade-in">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mb-4 text-sm">
        <Link to="/vacancies" className="text-primary-600 hover:underline">
          ← Вернуться к вакансиям
        </Link>
        <span className="text-gray-300 hidden sm:inline">|</span>
        <Link to="/candidates" className="text-primary-600 hover:underline">
          Все кандидаты
        </Link>
        <span className="text-gray-400">— каталог профилей</span>
      </div>

      {/* Vacancy Header */}
      <Card className="mb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{vacancy?.title}</h1>
            <p className="text-gray-600 mt-1">{company.displayName}</p>
            
            <div className="flex flex-wrap gap-2 mt-4">
              {vacancy?.skills?.map((skill, i) => (
                <span 
                  key={i}
                  className={`px-3 py-1 rounded-full text-sm ${
                    skill.is_required 
                      ? 'bg-red-100 text-red-700' 
                      : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {skill.skill_name}
                  {skill.is_required && ' *'}
                </span>
              ))}
            </div>
          </div>
          
          <Link to={`/vacancies/${vacancyId}`}>
            <Button variant="secondary" size="sm">
              Подробнее о вакансии
            </Button>
          </Link>
        </div>
      </Card>

      {/* Controls */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold mb-4">Параметры матчинга</h2>
        <div className="flex flex-wrap items-end gap-6">
          <div>
            <label className="block text-sm text-gray-600 mb-2">
              Минимальный скор: {Math.round(minScore * 100)}%
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={minScore}
              onChange={(e) => setMinScore(parseFloat(e.target.value))}
              className="w-48 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>
          
          <div>
            <label className="block text-sm text-gray-600 mb-2">
              Количество кандидатов: {limit}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
              className="w-48 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>
          
          <Button
            variant="success"
            size="lg"
            onClick={() => matchMutation.mutate()}
            loading={matchMutation.isPending}
          >
            {matchMutation.isPending ? '⏳ Поиск кандидатов...' : '🎯 Запустить матчинг'}
          </Button>
        </div>
        
        {matchMutation.isError && (
          <p className="text-red-500 mt-4">
            Ошибка: {matchMutation.error?.message || 'Не удалось выполнить матчинг'}
          </p>
        )}
      </Card>

      {/* Results */}
      <div>
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">
            Результаты матчинга
            {candidates.length > 0 && (
              <Badge variant="blue" className="ml-2">{candidates.length}</Badge>
            )}
          </h2>
          
          {candidates.length > 0 && (
            <div className="text-sm text-gray-500">
              Показаны кандидаты со скором ≥ {Math.round(minScore * 100)}%
            </div>
          )}
        </div>
        
        {loadingResults ? (
          <Spinner />
        ) : candidates.length > 0 ? (
          <div className="space-y-4">
            {candidates.map((item) => (
              <MatchResultCard 
                key={item.candidate?.id || item.rank}
                candidate={item.candidate}
                match={item.match}
                rank={item.rank}
                vacancyId={vacancyId}
              />
            ))}
          </div>
        ) : (
          <Card className="text-center py-12">
            <div className="text-5xl mb-4">🔍</div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              Результатов пока нет
            </h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Нажмите "Запустить матчинг" для поиска подходящих кандидатов.
              Система проанализирует навыки, опыт и другие параметры.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}





