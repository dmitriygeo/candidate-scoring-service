import { parseCandidateAbout } from '../utils/candidateAbout';

/**
 * Блок «О себе»: без строки статуса отклика; skills_cv и т.п. — списком, без сырого JSON.
 */
export default function CandidateAbout({ about, skillNamesFromDb = [] }) {
  const { proseLines, skillSections, isEmpty } = parseCandidateAbout(about, skillNamesFromDb);

  if (isEmpty) return null;

  return (
    <div className="space-y-6 text-gray-800">
      {proseLines.length > 0 && (
        <div className="space-y-3 text-[15px] leading-relaxed">
          {proseLines.map((p, i) => (
            <p key={i} className="whitespace-pre-wrap">
              {p}
            </p>
          ))}
        </div>
      )}

      {skillSections.map((sec, i) => (
        <div key={i}>
          <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-2">
            {sec.title}
          </h3>
          <ul className="list-disc list-inside space-y-1.5 text-[15px] text-gray-700 pl-1">
            {sec.items.map((item, j) => (
              <li key={j} className="marker:text-primary-500">
                {item}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
