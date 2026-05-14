import { Link } from 'react-router-dom';
import { Badge, Button } from './ui';
import { parseCompanyField, formatExperienceFromMonths } from '../utils/vacancyDisplay';

export default function VacancyCard({ vacancy, showMatchButton = true }) {
  const formatSalary = (from, to, currency = 'RUB') => {
    const symbol = currency === 'RUB' ? '₽' : currency;
    if (from && to) {
      return `${from.toLocaleString()} - ${to.toLocaleString()} ${symbol}`;
    } else if (from) {
      return `от ${from.toLocaleString()} ${symbol}`;
    } else if (to) {
      return `до ${to.toLocaleString()} ${symbol}`;
    }
    return null;
  };

  const salary = formatSalary(vacancy.salary_from, vacancy.salary_to, vacancy.salary_currency);
  const company = parseCompanyField(vacancy.company);
  const expLabel = formatExperienceFromMonths(vacancy.experience_from, vacancy.experience_to);

  return (
    <div className="bg-white rounded-xl shadow-sm p-6 card-hover animate-fade-in">
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1">
          <Link 
            to={`/vacancies/${vacancy.id}`}
            className="text-xl font-semibold text-primary-600 hover:underline"
          >
            {vacancy.title}
          </Link>
          <p className="text-gray-600 mt-1">{company.displayName}</p>
          
          <div className="flex flex-wrap gap-2 mt-3">
            {vacancy.city && (
              <Badge variant="gray">📍 {vacancy.city}</Badge>
            )}
            {salary && (
              <Badge variant="green">💰 {salary}</Badge>
            )}
            {vacancy.work_format && (
              <Badge variant="blue">{vacancy.work_format}</Badge>
            )}
            {expLabel && (
              <Badge variant="purple" title="Требуемый опыт">
                {expLabel}
              </Badge>
            )}
          </div>

          <div className="flex flex-wrap gap-1 mt-4">
            {vacancy.skills?.slice(0, 6).map((skill, i) => (
              <span 
                key={i}
                className={`px-2 py-1 text-xs rounded ${
                  skill.is_required 
                    ? 'bg-red-100 text-red-700' 
                    : 'bg-gray-100 text-gray-700'
                }`}
              >
                {skill.skill_name}
                {skill.is_required && ' *'}
              </span>
            ))}
            {vacancy.skills?.length > 6 && (
              <span className="px-2 py-1 bg-gray-100 text-gray-500 text-xs rounded">
                +{vacancy.skills.length - 6}
              </span>
            )}
          </div>
        </div>
        
        {showMatchButton && (
          <Link to={`/matching/${vacancy.id}`}>
            <Button variant="success" size="md">
              🎯 Найти кандидатов
            </Button>
          </Link>
        )}
      </div>
    </div>
  );
}





