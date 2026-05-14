import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { candidatesApi } from '../api/client';
import { CandidateCard } from '../components';
import { Spinner, Button, Card, Input } from '../components/ui';

export default function Candidates() {
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const limit = 20;

  const { data: candidates, isLoading, error, refetch } = useQuery({
    queryKey: ['candidates', page],
    queryFn: () => candidatesApi.getAll({ limit, offset: page * limit }).then(res => res.data),
  });

  // Фильтрация по поиску на клиенте
  const filteredCandidates = candidates?.filter((c) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const fullName = [c.first_name, c.last_name].filter(Boolean).join(' ').toLowerCase();
    const ext = c.profiles?.map((p) => p.external_id).join(' ')?.toLowerCase() ?? '';
    return (
      fullName.includes(q) ||
      (c.position_title && c.position_title.toLowerCase().includes(q)) ||
      (c.about && c.about.toLowerCase().includes(q)) ||
      ext.includes(q)
    );
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

  return (
    <div className="animate-fade-in">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Кандидаты</h1>
          <p className="text-gray-500 mt-1">Всего: {candidates?.length || 0} на странице</p>
        </div>
        <Link to="/parser">
          <Button variant="primary">
            🔄 Спарсить резюме
          </Button>
        </Link>
      </div>

      {/* Search */}
      <Card className="mb-6">
        <Input
          placeholder="Поиск по имени или должности..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </Card>

      {/* Candidates List */}
      {filteredCandidates?.length > 0 ? (
        <div className="space-y-4">
          {filteredCandidates.map((candidate) => (
            <CandidateCard key={candidate.id} candidate={candidate} />
          ))}
        </div>
      ) : (
        <Card className="text-center py-12">
          <p className="text-4xl mb-4">👥</p>
          <p className="text-gray-500">
            {search ? 'Ничего не найдено' : 'Кандидатов пока нет'}
          </p>
          <Link to="/parser" className="mt-4 inline-block">
            <Button>Загрузить резюме</Button>
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
          disabled={candidates?.length < limit}
        >
          Вперёд →
        </Button>
      </div>
    </div>
  );
}





