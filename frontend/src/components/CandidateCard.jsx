import { Link } from 'react-router-dom';
import { Badge } from './ui';

function candidateDisplayName(candidate) {
  const name = [candidate.first_name, candidate.last_name].filter(Boolean).join(' ').trim();
  if (name) return name;
  if (candidate.position_title) return candidate.position_title;
  const ext = candidate.profiles?.[0]?.external_id;
  if (ext) return `Резюме ${ext.slice(0, 8)}…`;
  return `Кандидат #${candidate.id}`;
}

export default function CandidateCard({ candidate }) {
  const title = candidateDisplayName(candidate);
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 card-hover animate-fade-in">
      <div className="flex justify-between items-start">
        <div className="flex-1">
          <Link 
            to={`/candidates/${candidate.id}`}
            className="text-xl font-semibold text-primary-600 hover:underline"
          >
            {title}
          </Link>
          
          <p className="text-gray-600 mt-1">{candidate.position_title || 'Не указана должность'}</p>
          
          <div className="flex flex-wrap gap-2 mt-3">
            {candidate.city && (
              <Badge variant="gray">📍 {candidate.city}</Badge>
            )}
            {candidate.total_experience_months && (
              <Badge variant="blue">
                💼 {Math.floor(candidate.total_experience_months / 12)} лет {candidate.total_experience_months % 12} мес
              </Badge>
            )}
            {candidate.desired_salary_min && (
              <Badge variant="green">
                💰 от {candidate.desired_salary_min.toLocaleString()} ₽
              </Badge>
            )}
            {candidate.work_format && (
              <Badge variant="purple">{candidate.work_format}</Badge>
            )}
          </div>

          <div className="flex flex-wrap gap-1 mt-4">
            {candidate.skills?.slice(0, 6).map((skill, i) => (
              <span 
                key={i}
                className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
              >
                {skill.skill_name}
              </span>
            ))}
            {candidate.skills?.length > 6 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-500 text-xs rounded">
                +{candidate.skills.length - 6}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}





