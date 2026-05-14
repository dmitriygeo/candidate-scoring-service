import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { vacanciesApi } from '../api/client';
import { VacancyCard } from '../components';
import { Spinner, Button, Card, Input } from '../components/ui';

export default function Vacancies() {
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const limit = 20;

  const { data: vacancies, isLoading, error, refetch } = useQuery({
    queryKey: ['vacancies', page],
    queryFn: () => vacanciesApi.getAll({ limit, offset: page * limit }).then(res => res.data),
  });

  // Фильтрация по поиску на клиенте
  const filteredVacancies = vacancies?.filter(v => 
    !search || 
    v.title.toLowerCase().includes(search.toLowerCase()) ||
    v.company.toLowerCase().includes(search.toLowerCase())
  );

  if (isLoading) return <Spinner size="lg" />;
  
  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500 mb-4">Ошибка загрузки: {error.message}</p>
        <Button onClick={() => refetch()}>Повторить</Button>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Вакансии</h1>
          <p className="text-gray-500 mt-1">Всего: {vacancies?.length || 0} на странице</p>
        </div>
        <Link to="/parser">
          <Button variant="primary">
            🔄 Спарсить новые
          </Button>
        </Link>
      </div>

      {/* Search */}
      <Card className="mb-6">
        <Input
          placeholder="Поиск по названию или компании..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </Card>

      {/* Vacancies List */}
      {filteredVacancies?.length > 0 ? (
        <div className="space-y-4">
          {filteredVacancies.map((vacancy) => (
            <VacancyCard key={vacancy.id} vacancy={vacancy} />
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <p className="text-4xl mb-4">💼</p>
          <p className="text-gray-500">
            {search ? 'Ничего не найдено' : 'Вакансий пока нет'}
          </p>
          <Link to="/parser" className="mt-4 inline-block">
            <Button>Загрузить вакансии</Button>
          </Link>
        </Card>
      )}

      {/* Pagination */}
      <div className="flex justify-center items-center gap-4 mt-8">
        <Button
          variant="secondary"
          onClick={() => setPage(p => Math.max(0, p - 1))}
          disabled={page === 0}
        >
          ← Назад
        </Button>
        <span className="text-gray-600">
          Страница {page + 1}
        </span>
        <Button
          variant="secondary"
          onClick={() => setPage(p => p + 1)}
          disabled={vacancies?.length < limit}
        >
          Вперёд →
        </Button>
      </div>
    </div>
  );
}





