import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { parsingApi } from '../api/client';
import { Button, Card, Input, Badge } from '../components/ui';
import { Select } from '../components/ui/Input';

const AREAS = [
  { value: '113', label: '🇷🇺 Россия (вся)' },
  { value: '1', label: '🏙️ Москва' },
  { value: '2', label: '🏙️ Санкт-Петербург' },
  { value: '3', label: '🏙️ Екатеринбург' },
  { value: '4', label: '🏙️ Новосибирск' },
  { value: '66', label: '🏙️ Нижний Новгород' },
  { value: '88', label: '🏙️ Казань' },
];

const SEARCH_FIELDS = [
  { value: 'title', label: 'В заголовке резюме' },
  { value: 'everywhere', label: 'Везде' },
];

export default function Parser() {
  const [type, setType] = useState('vacancies');
  const [query, setQuery] = useState('');
  const [area, setArea] = useState('113');
  const [perPage, setPerPage] = useState(10);
  const [maxPages, setMaxPages] = useState(1);
  const [searchField, setSearchField] = useState('title');
  const [results, setResults] = useState(null);

  // Мутация для парсинга вакансий
  const vacanciesMutation = useMutation({
    mutationFn: () => parsingApi.parseVacancies(query, parseInt(area), perPage),
    onSuccess: (response) => setResults(response.data),
  });

  // Мутация для парсинга резюме
  const resumesMutation = useMutation({
    mutationFn: () => parsingApi.parseResumes(query, parseInt(area), perPage, maxPages, searchField),
    onSuccess: (response) => setResults(response.data),
  });

  const isLoading = vacanciesMutation.isPending || resumesMutation.isPending;
  const error = vacanciesMutation.error || resumesMutation.error;

  const handleParse = () => {
    setResults(null);
    if (type === 'vacancies') {
      vacanciesMutation.mutate();
    } else {
      resumesMutation.mutate();
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Парсер HH.ru</h1>
        <p className="text-gray-500 mt-1">Загрузка вакансий и резюме с HeadHunter</p>
      </div>

      {/* Type Selection */}
      <Card className="mb-6">
        <div className="flex gap-4">
          <button
            onClick={() => setType('vacancies')}
            className={`flex-1 p-4 rounded-xl border-2 transition-all ${
              type === 'vacancies'
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="text-3xl mb-2">💼</div>
            <h3 className="font-semibold">Вакансии</h3>
            <p className="text-sm text-gray-500 mt-1">Парсинг через HH API</p>
          </button>
          
          <button
            onClick={() => setType('resumes')}
            className={`flex-1 p-4 rounded-xl border-2 transition-all ${
              type === 'resumes'
                ? 'border-green-500 bg-green-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="text-3xl mb-2">👥</div>
            <h3 className="font-semibold">Резюме</h3>
            <p className="text-sm text-gray-500 mt-1">Парсинг HTML страниц</p>
          </button>
        </div>
      </Card>

      {/* Settings */}
      <Card className="mb-6">
        <h2 className="text-lg font-semibold mb-4">Параметры поиска</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Input
            label="Поисковый запрос"
            placeholder="Например: Python developer, Data Scientist"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          
          <Select
            label="Регион"
            options={AREAS}
            value={area}
            onChange={(e) => setArea(e.target.value)}
          />
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Количество: {perPage}
            </label>
            <input
              type="range"
              min="5"
              max="50"
              step="5"
              value={perPage}
              onChange={(e) => setPerPage(parseInt(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
            />
          </div>

          {type === 'resumes' && (
            <>
              <Select
                label="Где искать"
                options={SEARCH_FIELDS}
                value={searchField}
                onChange={(e) => setSearchField(e.target.value)}
              />
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Страниц для парсинга: {maxPages}
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  step="1"
                  value={maxPages}
                  onChange={(e) => setMaxPages(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </>
          )}
        </div>

        <div className="mt-6">
          <Button
            variant={type === 'vacancies' ? 'primary' : 'success'}
            size="lg"
            onClick={handleParse}
            disabled={!query || isLoading}
            loading={isLoading}
          >
            {isLoading ? '⏳ Парсинг...' : `🔄 Спарсить ${type === 'vacancies' ? 'вакансии' : 'резюме'}`}
          </Button>
        </div>

        {error && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600">Ошибка: {error.message || 'Не удалось выполнить парсинг'}</p>
          </div>
        )}
      </Card>

      {/* Results */}
      {results && (
        <Card className="animate-fade-in">
          <h2 className="text-lg font-semibold mb-4">Результаты парсинга</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="p-4 bg-blue-50 rounded-xl">
              <p className="text-3xl font-bold text-blue-600">
                {results.vacancies_parsed || results.resumes_parsed || 0}
              </p>
              <p className="text-sm text-blue-600 mt-1">Спарсено</p>
            </div>
            
            <div className="p-4 bg-green-50 rounded-xl">
              <p className="text-3xl font-bold text-green-600">
                {results.vacancies_saved || results.candidates_saved || 0}
              </p>
              <p className="text-sm text-green-600 mt-1">Сохранено в БД</p>
            </div>
            
            <div className="p-4 bg-red-50 rounded-xl">
              <p className="text-3xl font-bold text-red-600">
                {results.errors?.length || 0}
              </p>
              <p className="text-sm text-red-600 mt-1">Ошибок</p>
            </div>
          </div>

          <div className="flex justify-between items-center">
            <Badge variant={results.status === 'success' ? 'green' : results.status === 'partial' ? 'yellow' : 'red'}>
              Статус: {results.status}
            </Badge>
            
            <Link to={type === 'vacancies' ? '/vacancies' : '/candidates'}>
              <Button variant="secondary">
                Перейти к {type === 'vacancies' ? 'вакансиям' : 'кандидатам'} →
              </Button>
            </Link>
          </div>

          {results.errors?.length > 0 && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="font-medium text-red-700 mb-2">Ошибки ({results.errors.length}):</p>
              <ul className="text-sm text-red-600 list-disc list-inside max-h-40 overflow-y-auto">
                {results.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}

      {/* Tips */}
      <Card className="mt-6 bg-yellow-50 border border-yellow-200">
        <h3 className="font-semibold text-yellow-800 mb-2">💡 Советы</h3>
        <ul className="text-sm text-yellow-700 space-y-1">
          <li>• Для резюме: поиск "В заголовке" даёт более релевантные результаты</li>
          <li>• Между запросами есть задержка 2-5 сек для избежания блокировки</li>
          <li>• Если получаете ошибки 429 — подождите несколько минут</li>
          <li>• Дубликаты автоматически пропускаются при сохранении</li>
        </ul>
      </Card>
    </div>
  );
}





