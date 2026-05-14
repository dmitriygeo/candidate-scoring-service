import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 600000, // 10 минут: Hybrid HGB + до 500 кандидатов могут долго считаться на CPU
});

// Interceptor для логирования
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor для обработки ошибок
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Произошла ошибка';
    console.error('[API Error]:', message);
    return Promise.reject(error);
  }
);

// ============ Vacancies ============
export const vacanciesApi = {
  getAll: (params = {}) => 
    api.get('/vacancies', { params }),
  
  getById: (id) => 
    api.get(`/vacancies/${id}`),
  
  analyze: (data) => 
    api.post('/vacancies/analyze', data),
};

// ============ Candidates ============
export const candidatesApi = {
  getAll: (params = {}) => 
    api.get('/candidates', { params }),
  
  getById: (id) => 
    api.get(`/candidates/${id}`),
};

// ============ Matching ============
export const matchingApi = {
  matchVacancy: (vacancyId, minScore = 0.3, limit = 20) =>
    api.post('/match/vacancy', { 
      vacancy_id: vacancyId, 
      min_score: minScore, 
      limit 
    }),
  
  simpleMatch: (data) => 
    api.post('/match/simple', data),
  
  getResults: (vacancyId, minScore = 0, limit = 20) =>
    api.get(`/match/vacancy/${vacancyId}/results`, { 
      params: { min_score: minScore, limit } 
    }),
};

// ============ Parsing ============
export const parsingApi = {
  parseVacancies: (query, area = 113, perPage = 10) =>
    api.post('/parse/hh/vacancies', { query, area, per_page: perPage }),
  
  parseResumes: (query, area = 113, perPage = 10, maxPages = 1, searchField = 'title', logic = 'normal') =>
    api.post('/parse/hh/resumes', { 
      query, 
      area, 
      per_page: perPage, 
      max_pages: maxPages,
      search_field: searchField,
      logic
    }),
  
  parseResumeByUrl: (url) =>
    api.post('/parse/hh/resume', { url }),
};

// ============ Skills ============
export const skillsApi = {
  normalize: (skills) => 
    api.post('/skills/normalize', { skills }),
  
  extract: (text, context = null, includeNerSpans = false) => 
    api.post('/skills/extract', { text, context, include_ner_spans: includeNerSpans }),
  
  /** NER по словарю навыков (только сущности SKILL) */
  ner: (text) => 
    api.post('/skills/ner', { text }),
  
  getGroups: () => 
    api.get('/skills/groups'),
};

// ============ Embeddings ============
export const embeddingsApi = {
  encode: (texts) => 
    api.post('/embeddings/encode', { texts }),
  
  similarity: (query, candidates, topK = 5) =>
    api.post('/embeddings/similarity', { query, candidates, top_k: topK }),
};

// ============ Stats ============
export const statsApi = {
  getStats: () => api.get('/stats'),
  getHealth: () => api.get('/health'),
};

export default api;





