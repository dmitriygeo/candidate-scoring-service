import { Link } from 'react-router-dom';
import { ProgressBar, Badge } from './ui';

const profileLinkState = (vacancyId) =>
  vacancyId != null && vacancyId !== ''
    ? { fromMatching: true, vacancyId: String(vacancyId) }
    : undefined;

export default function MatchResultCard({ candidate, match, rank, vacancyId }) {
  const getScoreColor = (score) => {
    if (score >= 0.7) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getRankBadge = (rank) => {
    if (rank === 1) return 'bg-yellow-500';
    if (rank === 2) return 'bg-gray-400';
    if (rank === 3) return 'bg-orange-400';
    return 'bg-gray-300';
  };

  const scores = [
    { label: 'Навыки', value: match.skills_score, color: 'blue' },
    { label: 'Опыт', value: match.experience_score, color: 'green' },
    { label: 'Образование', value: match.education_score, color: 'purple' },
    { label: 'Зарплата', value: match.salary_score, color: 'yellow' },
    { label: 'Локация', value: match.location_score, color: 'cyan' },
    { label: 'Семантика', value: match.embedding_score, color: 'pink' },
  ];

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 card-hover animate-fade-in">
      <div className="flex items-start gap-4">
        {/* Rank Badge */}
        <div 
          className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg ${getRankBadge(rank)}`}
        >
          #{rank}
        </div>

        {/* Main Info */}
        <div className="flex-1">
          <div className="flex justify-between items-start">
            <div>
              {candidate?.id ? (
                <>
                  <Link
                    to={`/candidates/${candidate.id}`}
                    state={profileLinkState(vacancyId)}
                    className="text-xl font-semibold text-primary-600 hover:underline"
                  >
                    {candidate.first_name} {candidate.last_name}
                  </Link>
                  <div className="mt-1">
                    <Link
                      to={`/candidates/${candidate.id}`}
                      state={profileLinkState(vacancyId)}
                      className="inline-flex items-center justify-center font-medium rounded-lg transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 bg-gray-100 text-gray-700 hover:bg-gray-200 px-3 py-1.5 text-sm"
                    >
                      Профиль
                    </Link>
                  </div>
                </>
              ) : (
                <span className="text-xl font-semibold text-gray-700">
                  {candidate?.first_name} {candidate?.last_name}
                </span>
              )}
              <p className="text-gray-600">{candidate.position_title}</p>
              
              <div className="flex gap-4 mt-2 text-sm text-gray-500">
                {candidate.city && <span>📍 {candidate.city}</span>}
                {candidate.total_experience_months && (
                  <span>💼 {Math.floor(candidate.total_experience_months / 12)} лет опыта</span>
                )}
                {candidate.desired_salary_min && (
                  <span>💰 от {candidate.desired_salary_min.toLocaleString()} ₽</span>
                )}
              </div>
            </div>

            {/* Total Score (при наличии артефактов — Hybrid HGB перезаписывает total_score) */}
            <div className="text-right">
              <div className={`text-4xl font-bold ${getScoreColor(match.total_score)}`}>
                {Math.round(match.total_score * 100)}%
              </div>
              {typeof match.score_details?.heuristic_total_score === 'number' && (
                <p className="text-xs text-gray-500 mt-1 max-w-[11rem] ml-auto leading-snug">
                  Ранжирование: Hybrid HGB
                  <span className="block text-gray-400">
                    эвристика: {Math.round(match.score_details.heuristic_total_score * 100)}%
                  </span>
                </p>
              )}
            </div>
          </div>

          {/* Score Breakdown */}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mt-6">
            {scores.map((score) => (
              <div key={score.label}>
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>{score.label}</span>
                  <span className="font-medium">{Math.round(score.value * 100)}%</span>
                </div>
                <ProgressBar value={score.value} color={score.color} />
              </div>
            ))}
          </div>

          {/* Skills */}
          <div className="flex flex-wrap gap-1 mt-4">
            {candidate.skills?.slice(0, 10).map((skill, i) => (
              <span 
                key={i}
                className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
              >
                {skill.skill_name}
              </span>
            ))}
            {candidate.skills?.length > 10 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-500 text-xs rounded">
                +{candidate.skills.length - 10}
              </span>
            )}
          </div>

          {/* Match Details */}
          {match.score_details && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              {match.skills_score === 0 &&
                (match.score_details.matched_skills?.length || 0) === 0 &&
                (match.score_details.missing_required_skills?.length || 0) === 0 && (
                  <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-3">
                    В карточке вакансии нет структурированных навыков для сравнения — блок «Навыки» в
                    эвристике даёт 0%. Откройте вакансию в каталоге, чтобы подтянуть навыки из описания,
                    или добавьте ключевые навыки вручную.
                  </p>
                )}
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Совпавшие навыки</p>
                  <p className="font-medium text-green-600">
                    {match.score_details.matched_skills?.length || 0}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Отсутствуют</p>
                  <p className="font-medium text-red-600">
                    {match.score_details.missing_required_skills?.length || 0}
                  </p>
                </div>
                <div>
                  <p className="text-gray-500">Дополнительные</p>
                  <p className="font-medium text-blue-600">
                    {match.score_details.extra_skills?.length || 0}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}





