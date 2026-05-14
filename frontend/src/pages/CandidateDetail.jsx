import { useParams, Link, useLocation } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { candidatesApi } from '../api/client';
import { Spinner, Button, Card, Badge } from '../components/ui';
import CandidateAbout from '../components/CandidateAbout';
import { parseCandidateAbout } from '../utils/candidateAbout';

export default function CandidateDetail() {
  const { id } = useParams();
  const location = useLocation();
  const matchBack =
    location.state?.fromMatching && location.state?.vacancyId
      ? `/matching/${location.state.vacancyId}`
      : null;

  const { data: candidate, isLoading, error } = useQuery({
    queryKey: ['candidate', id],
    queryFn: () => candidatesApi.getById(id).then(res => res.data),
  });

  if (isLoading) return <Spinner size="lg" />;
  
  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-500">Ошибка загрузки кандидата</p>
        <Link to="/candidates" className="mt-4 inline-block">
          <Button>Вернуться к списку</Button>
        </Link>
      </div>
    );
  }

  if (!candidate) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Кандидат не найден</p>
        <Link to="/candidates" className="mt-4 inline-block">
          <Button>Вернуться к списку</Button>
        </Link>
      </div>
    );
  }

  const displayName = (() => {
    const name = [candidate.first_name, candidate.last_name].filter(Boolean).join(' ').trim();
    if (name) return name;
    if (candidate.position_title) return candidate.position_title;
    const ext = candidate.profiles?.[0]?.external_id;
    if (ext) return `Резюме ${ext.slice(0, 8)}…`;
    return `Кандидат #${candidate.id}`;
  })();

  const skillNamesFromDb = (candidate.skills || []).map((s) => s.skill_name).filter(Boolean);
  const aboutParsed = parseCandidateAbout(candidate.about, skillNamesFromDb);
  const showAboutBlock = candidate.about && !aboutParsed.isEmpty;

  const formatExperience = (months) => {
    if (!months) return 'Не указан';
    const years = Math.floor(months / 12);
    const remainingMonths = months % 12;
    if (years > 0 && remainingMonths > 0) {
      return `${years} лет ${remainingMonths} мес`;
    } else if (years > 0) {
      return `${years} лет`;
    }
    return `${remainingMonths} мес`;
  };

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm mb-2">
          <Link to="/candidates" className="text-primary-600 hover:underline">
            ← Вернуться к списку
          </Link>
          {matchBack && (
            <>
              <span className="text-gray-300 hidden sm:inline">|</span>
              <Link to={matchBack} className="text-primary-600 hover:underline">
                ← К матчингу по вакансии
              </Link>
            </>
          )}
        </div>
        <h1 className="text-3xl font-bold text-gray-900">
          {displayName}
        </h1>
        <p className="text-xl text-gray-600 mt-1">{candidate.position_title || 'Не указана должность'}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* About */}
          {showAboutBlock && (
            <Card>
              <h2 className="text-xl font-semibold mb-4">О себе</h2>
              <CandidateAbout about={candidate.about} skillNamesFromDb={skillNamesFromDb} />
            </Card>
          )}

          {/* Work Experience */}
          <Card>
            <h2 className="text-xl font-semibold mb-4">Опыт работы</h2>
            {candidate.work_experience?.length > 0 ? (
              <div className="space-y-6">
                {candidate.work_experience.map((exp, i) => (
                  <div key={i} className="border-l-4 border-primary-500 pl-4">
                    <h3 className="font-semibold text-lg">{exp.position}</h3>
                    <p className="text-gray-600">{exp.company}</p>
                    <div className="flex gap-4 text-sm text-gray-500 mt-1">
                      {exp.start_date && (
                        <span>
                          {new Date(exp.start_date).toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' })}
                          {' — '}
                          {exp.is_current 
                            ? 'по настоящее время' 
                            : exp.end_date 
                              ? new Date(exp.end_date).toLocaleDateString('ru-RU', { month: 'short', year: 'numeric' })
                              : ''
                          }
                        </span>
                      )}
                      {exp.duration_months && (
                        <Badge variant="gray">{formatExperience(exp.duration_months)}</Badge>
                      )}
                    </div>
                    {exp.description && (
                      <p className="text-gray-700 mt-2 text-sm whitespace-pre-wrap">{exp.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">Опыт работы не указан</p>
            )}
          </Card>

          {/* Education */}
          <Card>
            <h2 className="text-xl font-semibold mb-4">Образование</h2>
            {candidate.education?.length > 0 ? (
              <div className="space-y-4">
                {candidate.education.map((edu, i) => (
                  <div key={i} className="border-l-4 border-purple-500 pl-4">
                    <h3 className="font-semibold">{edu.institution}</h3>
                    {edu.faculty && <p className="text-gray-600">{edu.faculty}</p>}
                    {edu.specialization && <p className="text-gray-600">{edu.specialization}</p>}
                    <div className="flex gap-4 text-sm text-gray-500 mt-1">
                      {edu.degree && <Badge variant="purple">{edu.degree}</Badge>}
                      {edu.end_year && <span>Выпуск: {edu.end_year}</span>}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">Образование не указано</p>
            )}
          </Card>

          {/* Skills */}
          <Card>
            <h2 className="text-xl font-semibold mb-4">Навыки</h2>
            {candidate.skills?.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {candidate.skills.map((skill, i) => (
                  <span 
                    key={i}
                    className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-full text-sm font-medium"
                  >
                    {skill.skill_name}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-gray-500 italic">Навыки не указаны</p>
            )}
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Contact */}
          <Card>
            <h2 className="text-lg font-semibold mb-4">Информация</h2>
            <div className="space-y-4">
              {candidate.city && (
                <div>
                  <p className="text-sm text-gray-500">Город</p>
                  <p className="font-medium">📍 {candidate.city}</p>
                </div>
              )}
              
              <div>
                <p className="text-sm text-gray-500">Общий опыт</p>
                <p className="font-medium">💼 {formatExperience(candidate.total_experience_months)}</p>
              </div>
              
              {candidate.desired_salary_min && (
                <div>
                  <p className="text-sm text-gray-500">Желаемая зарплата</p>
                  <p className="font-medium text-green-600">
                    💰 от {candidate.desired_salary_min.toLocaleString()} {candidate.salary_currency || '₽'}
                  </p>
                </div>
              )}
              
              {candidate.work_format && (
                <div>
                  <p className="text-sm text-gray-500">Формат работы</p>
                  <Badge variant="blue">{candidate.work_format}</Badge>
                </div>
              )}
            </div>
          </Card>

          {/* Profile Links */}
          {candidate.profiles?.length > 0 && (
            <Card>
              <h2 className="text-lg font-semibold mb-4">Профили</h2>
              <div className="space-y-2">
                {candidate.profiles.map((profile, i) => (
                  <div key={i}>
                    {profile.profile_url && (
                      <a 
                        href={profile.profile_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:underline text-sm flex items-center gap-1"
                      >
                        <span>🔗</span>
                        <span>{profile.source?.toUpperCase()} профиль</span>
                      </a>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Metadata */}
          <Card className="bg-gray-50">
            <div className="text-sm text-gray-500 space-y-2">
              <p>ID: {candidate.id}</p>
              <p>Создано: {new Date(candidate.created_at).toLocaleDateString('ru-RU')}</p>
              <p>Обновлено: {new Date(candidate.updated_at).toLocaleDateString('ru-RU')}</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}





