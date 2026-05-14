import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { skillsApi } from '../api/client';
import { Button, Card, Badge, Spinner } from '../components/ui';
import { Textarea } from '../components/ui/Input';

export default function Skills() {
  const [activeTab, setActiveTab] = useState('normalize');
  const [skillsInput, setSkillsInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [normalizeResults, setNormalizeResults] = useState(null);
  const [extractResults, setExtractResults] = useState(null);

  // Загрузка групп навыков
  const { data: skillGroups, isLoading: loadingGroups } = useQuery({
    queryKey: ['skillGroups'],
    queryFn: () => skillsApi.getGroups().then(res => res.data),
  });

  // Мутация для нормализации
  const normalizeMutation = useMutation({
    mutationFn: (skills) => skillsApi.normalize(skills),
    onSuccess: (response) => setNormalizeResults(response.data),
  });

  // Мутация для извлечения
  const extractMutation = useMutation({
    mutationFn: (text) => skillsApi.extract(text),
    onSuccess: (response) => setExtractResults(response.data),
  });

  const handleNormalize = () => {
    const skills = skillsInput
      .split(/[,\n]/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
    
    if (skills.length > 0) {
      normalizeMutation.mutate(skills);
    }
  };

  const handleExtract = () => {
    if (textInput.trim()) {
      extractMutation.mutate(textInput);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Анализ навыков</h1>
        <p className="text-gray-500 mt-1">Нормализация и извлечение навыков из текста</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('normalize')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'normalize'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          🔄 Нормализация
        </button>
        <button
          onClick={() => setActiveTab('extract')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'extract'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          📝 Извлечение
        </button>
        <button
          onClick={() => setActiveTab('groups')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTab === 'groups'
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          📂 Группы навыков
        </button>
      </div>

      {/* Normalize Tab */}
      {activeTab === 'normalize' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-lg font-semibold mb-4">Навыки для нормализации</h2>
            <Textarea
              placeholder="Введите навыки через запятую или каждый с новой строки:&#10;python3&#10;питон&#10;numpy&#10;sklearn"
              rows={8}
              value={skillsInput}
              onChange={(e) => setSkillsInput(e.target.value)}
            />
            <Button
              className="mt-4"
              onClick={handleNormalize}
              disabled={!skillsInput.trim()}
              loading={normalizeMutation.isPending}
            >
              🔄 Нормализовать
            </Button>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">Результаты</h2>
            {normalizeMutation.isPending ? (
              <Spinner />
            ) : normalizeResults ? (
              <div>
                {normalizeResults.specialization && (
                  <div className="mb-4 p-3 bg-purple-50 rounded-lg">
                    <span className="text-sm text-gray-600">Определённая специализация:</span>
                    <Badge variant="purple" className="ml-2">{normalizeResults.specialization}</Badge>
                  </div>
                )}
                
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {normalizeResults.normalized?.map((item, i) => (
                    <div 
                      key={i}
                      className={`p-3 rounded-lg border ${
                        item.found 
                          ? 'bg-green-50 border-green-200' 
                          : 'bg-red-50 border-red-200'
                      }`}
                    >
                      <div className="flex justify-between items-start">
                        <div>
                          <span className="font-medium">{item.original}</span>
                          <span className="mx-2">→</span>
                          <span className={item.found ? 'text-green-700 font-medium' : 'text-red-500'}>
                            {item.normalized || 'Не найдено'}
                          </span>
                        </div>
                        {item.found ? (
                          <Badge variant="green">✓</Badge>
                        ) : (
                          <Badge variant="red">✗</Badge>
                        )}
                      </div>
                      {item.groups?.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {item.groups.map((group, j) => (
                            <Badge key={j} variant="blue">{group}</Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-gray-500 italic">Введите навыки и нажмите "Нормализовать"</p>
            )}
          </Card>
        </div>
      )}

      {/* Extract Tab */}
      {activeTab === 'extract' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-lg font-semibold mb-4">Текст для анализа</h2>
            <Textarea
              placeholder="Вставьте текст вакансии или резюме...&#10;&#10;Пример: Ищем Python разработчика со знанием Django, PostgreSQL и Redis. Опыт работы с Docker и Kubernetes будет плюсом."
              rows={10}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
            />
            <Button
              className="mt-4"
              onClick={handleExtract}
              disabled={!textInput.trim()}
              loading={extractMutation.isPending}
            >
              📝 Извлечь навыки
            </Button>
          </Card>

          <Card>
            <h2 className="text-lg font-semibold mb-4">Найденные навыки</h2>
            {extractMutation.isPending ? (
              <Spinner />
            ) : extractResults ? (
              <div>
                {extractResults.specialization_group && (
                  <div className="mb-4 p-3 bg-purple-50 rounded-lg">
                    <span className="text-sm text-gray-600">Определённая специализация:</span>
                    <Badge variant="purple" className="ml-2">{extractResults.specialization_group}</Badge>
                  </div>
                )}
                
                {extractResults.skills?.length > 0 ? (
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {extractResults.skills.map((skill, i) => (
                      <div key={i} className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex justify-between items-center">
                          <span className="font-medium text-blue-800">{skill.normalized_name}</span>
                          <Badge variant="blue">{Math.round(skill.confidence * 100)}%</Badge>
                        </div>
                        {skill.context && (
                          <p className="text-sm text-gray-600 mt-1 italic">"{skill.context}"</p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-500 italic">Навыки не найдены в тексте</p>
                )}
              </div>
            ) : (
              <p className="text-gray-500 italic">Введите текст и нажмите "Извлечь навыки"</p>
            )}
          </Card>
        </div>
      )}

      {/* Groups Tab */}
      {activeTab === 'groups' && (
        <Card>
          <h2 className="text-lg font-semibold mb-4">Группы навыков в системе</h2>
          {loadingGroups ? (
            <Spinner />
          ) : skillGroups ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(skillGroups).map(([groupName, groupData]) => (
                <div key={groupName} className="p-4 bg-gray-50 rounded-xl">
                  <h3 className="font-semibold text-gray-800 mb-2 capitalize">
                    {groupName.replace(/_/g, ' ')}
                  </h3>
                  <div className="flex flex-wrap gap-1">
                    {groupData?.skills?.slice(0, 10).map((skill, i) => (
                      <Badge key={i} variant="gray">
                        {skill.name || skill}
                      </Badge>
                    ))}
                    {groupData?.skills?.length > 10 && (
                      <Badge variant="gray">+{groupData.skills.length - 10}</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 italic">Не удалось загрузить группы навыков</p>
          )}
        </Card>
      )}
    </div>
  );
}





