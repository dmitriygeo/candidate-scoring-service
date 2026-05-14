import { splitDescriptionSections, sectionTitleFromKey } from '../utils/vacancyDisplay';

/**
 * Аккуратное отображение описания вакансии с секциями ## key.
 */
export default function VacancyDescription({ text }) {
  if (!text || !String(text).trim()) {
    return <p className="text-gray-500 italic">Описание не указано</p>;
  }

  const sections = splitDescriptionSections(text);

  return (
    <div className="space-y-8">
      {sections.map((sec, i) => (
        <section key={i} className="border-b border-gray-100 last:border-0 pb-8 last:pb-0">
          {sec.title && (
            <h3 className="text-lg font-semibold text-gray-900 mb-3 tracking-tight">
              {sectionTitleFromKey(sec.title)}
            </h3>
          )}
          <div className="text-gray-700 text-[15px] leading-relaxed whitespace-pre-wrap">
            {sec.body || '—'}
          </div>
        </section>
      ))}
    </div>
  );
}
