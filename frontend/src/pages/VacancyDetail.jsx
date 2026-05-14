import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { vacanciesApi } from '../api/client';
import { Spinner, Button, Card, Badge } from '../components/ui';
import VacancyDescription from '../components/VacancyDescription';
import {
  parseCompanyField,
  formatExperienceFromMonths,
  extractTechFromDescription,
  employmentLabel,
  workFormatLabel,
} from '../utils/vacancyDisplay';

export default function VacancyDetail() {
  const { id } = useParams();

  const { data: vacancy, isLoading, error } = useQuery({
    queryKey: ['vacancy', id],
    queryFn: () => vacanciesApi.getById(id).then(res => res.data),
  });

  if (isLoading) return <Spinner size="lg" />;
  
  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Ошибка загрузки вакансии</p>
        <Link to="/vacancies" className="mt-4 inline-block">
          <Button>Вернуться к списку</Button>
        </Link>
      </div>
    );
  }

  if (!vacancy) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Вакансия не найдена</p>
        <Link to="/vacancies" className="mt-4 inline-block">
          <Button>Вернуться к списку</Button>
        </Link>
      </div>
    );
  }

  const company = parseCompanyField(vacancy.company);
  const inferredSkills = extractTechFromDescription(vacancy.description || '');
  const hasDbSkills = vacancy.skills?.length > 0;
  const extraSkillNames = inferredSkills.filter(
    (name) => !vacancy.skills?.some((s) => s.skill_name?.toLowerCase() === name.toLowerCase())
  );

  const formatSalary = () => {
    const symbol = vacancy.salary_currency === 'RUB' ? '₽' : vacancy.salary_currency;
    if (vacancy.salary_from && vacancy.salary_to) {
      return `${vacancy.salary_from.toLocaleString()} - ${vacancy.salary_to.toLocaleString()} ${symbol}`;
    } else if (vacancy.salary_from) {
      return `от ${vacancy.salary_from.toLocaleString()} ${symbol}`;
    } else if (vacancy.salary_to) {
      return `до ${vacancy.salary_to.toLocaleString()} ${symbol}`;
    }
    return 'Не указана';
  };

  const experienceText = formatExperienceFromMonths(
    vacancy.experience_from,
    vacancy.experience_to
  );

  return (
    <div className="animate-fade-in max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <Link to="/vacancies" className="text-primary-600 hover:underline text-sm mb-3 inline-block">
          ← Вернуться к списку
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">{vacancy.title}</h1>
        <p className="text-xl text-gray-800 font-medium mt-2">{company.displayName}</p>

        {company.meta && (
          <div className="mt-4 rounded-xl border border-gray-200 bg-gray-50/80 p-4 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-2">
              Реквизиты и контакты
            </p>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-gray-700">
              {company.meta.url && (
                <div className="sm:col-span-2">
                  <dt className="text-gray-500 inline mr-2">Сайт:</dt>
                  <dd className="inline">
                    <a
                      href={company.meta.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-primary-600 hover:underline break-all"
                    >
                      {company.meta.url}
                    </a>
                  </dd>
                </div>
              )}
              {company.meta.email && (
                <div>
                  <dt className="text-gray-500 inline mr-2">Email:</dt>
                  <dd className="inline">
                    <a href={`mailto:${company.meta.email}`} className="text-primary-600 hover:underline">
                      {company.meta.email}
                    </a>
                  </dd>
                </div>
              )}
              {company.meta.inn && (
                <div>
                  <dt className="text-gray-500 inline mr-2">ИНН:</dt>
                  <dd className="inline font-mono">{company.meta.inn}</dd>
                </div>
              )}
              {company.meta.kpp && (
                <div>
                  <dt className="text-gray-500 inline mr-2">КПП:</dt>
                  <dd className="inline font-mono">{company.meta.kpp}</dd>
                </div>
              )}
              {company.meta.ogrn && (
                <div>
                  <dt className="text-gray-500 inline mr-2">ОГРН:</dt>
                  <dd className="inline font-mono">{company.meta.ogrn}</dd>
                </div>
              )}
            </dl>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main */}
        <div className="lg:col-span-2 space-y-8">
          <Card className="shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Описание</h2>
            <VacancyDescription text={vacancy.description} />
          </Card>

          <Card className="shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Требуемые навыки</h2>
            {hasDbSkills ? (
              <div className="flex flex-wrap gap-2">
                {vacancy.skills.map((skill, i) => (
                  <span
                    key={i}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium ${
                      skill.is_required
                        ? 'bg-red-50 text-red-800 border border-red-200'
                        : 'bg-slate-100 text-slate-700 border border-slate-200'
                    }`}
                  >
                    {skill.skill_name}
                    {skill.is_required && <span className="text-red-600"> *</span>}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 text-sm mb-3">В карточке не указан структурированный список навыков.</p>
            )}

            {extraSkillNames.length > 0 && (
              <div className="mt-5">
                <p className="text-sm text-gray-500 mb-2">Упоминаются в описании</p>
                <div className="flex flex-wrap gap-2">
                  {extraSkillNames.map((name) => (
                    <span
                      key={name}
                      className="px-3 py-1.5 rounded-full text-sm bg-amber-50 text-amber-900 border border-amber-200"
                    >
                      {name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {!hasDbSkills && extraSkillNames.length === 0 && (
              <p className="text-gray-400 italic text-sm">Ключевые технологии по тексту не распознаны.</p>
            )}

            {hasDbSkills && (
              <p className="text-sm text-gray-400 mt-4">* — обязательный навык</p>
            )}
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <Card className="shadow-sm">
            <Link to={`/matching/${vacancy.id}`}>
              <Button variant="success" size="lg" className="w-full">
                Найти кандидатов
              </Button>
            </Link>
          </Card>

          <Card className="shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Детали вакансии</h2>
            <div className="space-y-4 text-[15px]">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Зарплата</p>
                <p className="font-semibold text-green-700">{formatSalary()}</p>
              </div>

              {vacancy.city && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Локация</p>
                  <p className="text-gray-800">{vacancy.city}</p>
                </div>
              )}

              {vacancy.work_format && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Формат работы</p>
                  <Badge variant="blue">{workFormatLabel(vacancy.work_format)}</Badge>
                </div>
              )}

              {vacancy.employment_type && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Занятость</p>
                  <p className="text-gray-800">{employmentLabel(vacancy.employment_type)}</p>
                </div>
              )}

              {experienceText && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Требуемый опыт</p>
                  <p className="text-gray-800">{experienceText}</p>
                </div>
              )}

              {vacancy.source_url && (
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-1">Источник</p>
                  <a
                    href={vacancy.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:underline break-all"
                  >
                    Открыть на сайте →
                  </a>
                </div>
              )}
            </div>
          </Card>

          <Card className="bg-gray-50/90 border border-gray-100 shadow-none">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">Служебное</p>
            <div className="text-sm text-gray-600 space-y-2 font-mono">
              <p>
                <span className="text-gray-500 font-sans">ID:</span> {vacancy.id}
              </p>
              {vacancy.external_id && (
                <p className="break-all">
                  <span className="text-gray-500 font-sans">Внешний ID:</span> {vacancy.external_id}
                </p>
              )}
              <p>
                <span className="text-gray-500 font-sans">Источник:</span> {vacancy.source}
              </p>
              <p>
                <span className="text-gray-500 font-sans">Создано:</span>{' '}
                {vacancy.created_at && new Date(vacancy.created_at).toLocaleString('ru-RU')}
              </p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
