/**
 * Отображение вакансий: компания (в т.ч. JSON из train_it), опыт по-русски, разбор описания.
 */

const SECTION_LABELS = {
  responsibilities: 'Обязанности',
  qualifications: 'Квалификация',
  positionrequirements: 'Требования к позиции',
  additionalrequirements: 'Дополнительные требования',
  требования: 'Требования',
  обязанности: 'Обязанности',
  ключевыенавыки: 'Ключевые навыки',
  овакансии: 'О вакансии',
  краткоеописание: 'Краткое описание',
};

/** Пары [отображаемое имя, RegExp по полному описанию] — длинные шаблоны раньше. */
const TECH_PATTERNS = [
  ['CI/CD', /\bCI\s*[/]\s*CD\b/i],
  ['REST API', /\bREST\s+API\b/i],
  ['GraphQL', /\bGraphQL\b/i],
  ['Node.js', /\bNode\.js\b/i],
  ['TypeScript', /\bTypeScript\b/i],
  ['JavaScript', /\bJavaScript\b/i],
  ['Python', /\bPython\b/i],
  ['Django', /\bDjango\b/i],
  ['FastAPI', /\bFastAPI\b/i],
  ['Flask', /\bFlask\b/i],
  ['Java', /\bJava\b/i],
  ['Spring', /\bSpring\b/i],
  ['Kotlin', /\bKotlin\b/i],
  ['Swift', /\bSwift\b/i],
  ['Go', /\bGo\b/i],
  ['Rust', /\bRust\b/i],
  ['C++', /C\+\+/],
  ['C#', /\bC#\b/],
  ['PHP', /\bPHP\b/i],
  ['Ruby', /\bRuby\b/i],
  ['React', /\bReact\b/i],
  ['Vue.js', /\bVue\.js\b/i],
  ['Angular', /\bAngular\b/i],
  ['PostgreSQL', /\bPostgreSQL\b/i],
  ['MySQL', /\bMySQL\b/i],
  ['MongoDB', /\bMongoDB\b/i],
  ['Redis', /\bRedis\b/i],
  ['Docker', /\bDocker\b/i],
  ['Kubernetes', /\bKubernetes\b/i],
  ['Linux', /\bLinux\b/i],
  ['Bash', /\bBash\b/i],
  ['Terraform', /\bTerraform\b/i],
  ['Ansible', /\bAnsible\b/i],
  ['AWS', /\bAWS\b/i],
  ['Azure', /\bAzure\b/i],
  ['GCP', /\bGCP\b/i],
  ['Kafka', /\bKafka\b/i],
  ['Selenium', /\bSelenium\b/i],
  ['pytest', /\bpytest\b/i],
  ['JUnit', /\bJUnit\b/i],
  ['Jenkins', /\bJenkins\b/i],
  ['Git', /\bGit\b/i],
  ['SQL', /\bSQL\b/i],
  ['HTML', /\bHTML\b/i],
  ['CSS', /\bCSS\b/i],
  ['1С', /\b1С\b/i],
  ['Excel', /\bExcel\b/i],
  ['Jira', /\bJira\b/i],
  ['Agile', /\bAgile\b/i],
  ['Scrum', /\bScrum\b/i],
  ['QA', /\bQA\b/i],
];

/**
 * Разбор поля company: иногда в БД лежит JSON (trudvsem / train_it).
 * @returns {{ displayName: string, meta: Record<string,string>|null }}
 */
export function parseCompanyField(company) {
  if (company == null || company === '') {
    return { displayName: 'Компания не указана', meta: null };
  }
  const raw = String(company).trim();
  if (!raw.startsWith('{')) {
    return { displayName: raw, meta: null };
  }
  try {
    const j = JSON.parse(raw);
    const displayName =
      j.fullCompanyName ||
      j.name ||
      j.companyName ||
      j.shortName ||
      (j.inn ? `Компания (ИНН ${j.inn})` : 'Компания');
    const meta = {};
    if (j.url) meta.url = String(j.url);
    if (j.email) meta.email = String(j.email);
    if (j.inn) meta.inn = String(j.inn);
    if (j.kpp) meta.kpp = String(j.kpp);
    if (j.ogrn) meta.ogrn = String(j.ogrn);
    if (j.companyCode) meta.companyCode = String(j.companyCode);
    const hasMeta = Object.keys(meta).length > 0;
    return { displayName: String(displayName).trim() || 'Компания', meta: hasMeta ? meta : null };
  } catch {
    return { displayName: raw.length > 120 ? `${raw.slice(0, 120)}…` : raw, meta: null };
  }
}

/** Склонение числа лет после «от / до» (21 год → «21 года» в родительном для «от» — как в разговорной норме «от 1 года», «от 2 лет»). */
export function ruYearsAfterNumber(n) {
  const y = Math.floor(Number(n));
  if (!Number.isFinite(y) || y <= 0) return '';
  const n100 = y % 100;
  const n10 = y % 10;
  if (n100 >= 11 && n100 <= 14) return `${y} лет`;
  if (n10 === 1) return `${y} года`;
  if (n10 >= 2 && n10 <= 4) return `${y} лет`;
  return `${y} лет`;
}

/**
 * Человекочитаемая строка требуемого опыта из месяцев.
 */
export function formatExperienceFromMonths(fromMonths, toMonths) {
  const from = Number(fromMonths);
  const to = toMonths != null ? Number(toMonths) : null;

  if (!Number.isFinite(from) || from <= 0) return null;

  if (from < 12) {
    const tail = Number.isFinite(to) && to > from ? ` до ${to} мес.` : '';
    return `от ${Math.round(from)} мес.${tail}`;
  }

  const yFrom = Math.floor(from / 12);
  const mFrom = Math.round(from % 12);
  let s = `от ${ruYearsAfterNumber(yFrom)}`;
  if (mFrom > 0) s += ` ${mFrom} мес.`;

  if (Number.isFinite(to) && to > from) {
    if (to < 12) {
      s += ` до ${Math.round(to)} мес.`;
    } else {
      const yTo = Math.floor(to / 12);
      const mTo = Math.round(to % 12);
      s += ` до ${ruYearsAfterNumber(yTo)}`;
      if (mTo > 0) s += ` ${mTo} мес.`;
    }
  }
  return s;
}

export function sectionTitleFromKey(key) {
  if (!key) return 'Раздел';
  const k = key.trim().toLowerCase().replace(/\s+/g, '');
  return SECTION_LABELS[k] || key.replace(/_/g, ' ');
}

/**
 * Разбивает описание с заголовками ## section на блоки { title, body }.
 */
export function splitDescriptionSections(text) {
  if (!text || !String(text).trim()) return [];
  const normalized = String(text).replace(/\r\n/g, '\n');
  const lines = normalized.split('\n');
  const sections = [];
  let current = { title: null, body: [] };

  const flush = () => {
    const body = current.body.join('\n').trim();
    if (current.title || body) {
      sections.push({ title: current.title, body });
    }
  };

  for (const line of lines) {
    const m = line.match(/^##\s+(.+)$/);
    if (m) {
      flush();
      current = { title: m[1].trim(), body: [] };
    } else {
      current.body.push(line);
    }
  }
  flush();
  return sections;
}

/** Навыки, найденные в тексте описания (если в БД не заполнены vacancy_skills). */
export function extractTechFromDescription(description) {
  if (!description) return [];
  const found = [];
  const seen = new Set();
  for (const [label, re] of TECH_PATTERNS) {
    if (re.test(description) && !seen.has(label.toLowerCase())) {
      seen.add(label.toLowerCase());
      found.push(label);
    }
  }
  return found;
}

const EMPLOYMENT_RU = {
  full_time: 'Полная занятость',
  part_time: 'Частичная занятость',
  project: 'Проектная работа',
  internship: 'Стажировка',
};

export function employmentLabel(value) {
  if (!value) return null;
  return EMPLOYMENT_RU[value] || value;
}

const WORK_FORMAT_RU = {
  remote: 'Удалённо',
  office: 'Офис',
  hybrid: 'Гибрид',
};

export function workFormatLabel(value) {
  if (!value) return null;
  return WORK_FORMAT_RU[value] || value;
}
