/**
 * Разбор поля about (train_IT / импорт): убрать служебные строки, аккуратно показать списки навыков.
 */

const SKILL_LINE_KEYS = {
  skills_cv: 'Навыки',
  hardskills_cv: 'Профессиональные навыки',
  softskills_cv: 'Гибкие навыки',
};

/**
 * @param {string|null|undefined} about
 * @param {string[]} existingSkillNames — имена из candidate.skills (без дублей в «О себе»)
 * @returns {{ proseLines: string[], skillSections: { title: string, items: string[] }[], isEmpty: boolean }}
 */
export function parseCandidateAbout(about, existingSkillNames = []) {
  if (!about || !String(about).trim()) {
    return { proseLines: [], skillSections: [], isEmpty: true };
  }

  const existing = new Set(
    (existingSkillNames || []).map((s) => String(s).trim().toLowerCase()).filter(Boolean)
  );

  const proseLines = [];
  const skillSections = [];

  for (const rawLine of String(about).split('\n')) {
    const line = rawLine.trim();
    if (!line) continue;

    if (/^статус отклика/i.test(line)) continue;
    if (/^cv_status\s*:/i.test(line)) continue;

    const m = line.match(/^(skills_cv|hardSkills_cv|softSkills_cv)\s*:\s*(.+)$/i);
    if (m) {
      const key = m[1].toLowerCase();
      let items = [];
      try {
        const parsed = JSON.parse(m[2]);
        if (Array.isArray(parsed)) {
          items = parsed
            .filter((x) => typeof x === 'string')
            .map((x) => x.trim())
            .filter(Boolean);
        }
      } catch {
        continue;
      }
      const seen = new Set();
      const unique = [];
      for (const it of items) {
        const low = it.toLowerCase();
        if (existing.has(low) || seen.has(low)) continue;
        seen.add(low);
        unique.push(it);
      }
      if (unique.length > 0) {
        skillSections.push({
          title: SKILL_LINE_KEYS[key] || m[1],
          items: unique,
        });
      }
      continue;
    }

    proseLines.push(line);
  }

  const isEmpty = proseLines.length === 0 && skillSections.length === 0;
  return { proseLines, skillSections, isEmpty };
}
