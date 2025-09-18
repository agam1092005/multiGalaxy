/**
 * Learning patterns chart component for visualizing learning behavior patterns
 */
import React from 'react';
import { LearningPatterns, LearningInsights } from '../../services/analyticsService';

interface LearningPatternsChartProps {
  patterns: LearningPatterns;
  insights?: LearningInsights | null;
}

export const LearningPatternsChart: React.FC<LearningPatternsChartProps> = ({
  patterns,
  insights
}) => {
  const formatHour = (hour: number) => {
    if (hour === 0) return '12 AM';
    if (hour < 12) return `${hour} AM`;
    if (hour === 12) return '12 PM';
    return `${hour - 12} PM`;
  };

  const getInteractionTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      problem_solving: 'Problem Solving',
      question_asking: 'Asking Questions',
      drawing: 'Drawing/Visual',
      speech_input: 'Voice Input',
      document_upload: 'Document Upload',
      whiteboard_interaction: 'Whiteboard Use'
    };
    return labels[type] || type;
  };

  const getInteractionTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      problem_solving: '🧮',
      question_asking: '❓',
      drawing: '🎨',
      speech_input: '🎤',
      document_upload: '📄',
      whiteboard_interaction: '📝'
    };
    return icons[type] || '📊';
  };

  return (
    <div className="space-y-6">
      {/* Study Time Preferences */}
      <div>
        <h3 className="font-medium text-gray-900 mb-3">Preferred Study Times</h3>
        {patterns.preferred_learning_times.length > 0 ? (
          <div className="grid grid-cols-3 gap-2">
            {patterns.preferred_learning_times.slice(0, 3).map((hour, index) => (
              <div
                key={hour}
                className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center"
              >
                <div className="text-lg font-semibold text-blue-900">
                  {formatHour(hour)}
                </div>
                <div className="text-xs text-blue-700">
                  Peak #{index + 1}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-sm">No clear time preferences yet</p>
        )}
      </div>

      {/* Session Patterns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="font-medium text-gray-900 mb-3">Session Frequency</h3>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-900">
              {patterns.session_frequency.toFixed(1)}
            </div>
            <div className="text-sm text-green-700">sessions per week</div>
            <div className="mt-2 text-xs text-green-600">
              {patterns.session_frequency >= 5 ? 'Excellent consistency!' :
               patterns.session_frequency >= 3 ? 'Good consistency' :
               'Room for improvement'}
            </div>
          </div>
        </div>

        <div>
          <h3 className="font-medium text-gray-900 mb-3">Attention Span</h3>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-purple-900">
              {Math.round(patterns.attention_span / 60)}
            </div>
            <div className="text-sm text-purple-700">minutes average</div>
            <div className="mt-2 text-xs text-purple-600">
              {patterns.attention_span >= 1800 ? 'Great focus!' :
               patterns.attention_span >= 900 ? 'Good focus' :
               'Consider shorter sessions'}
            </div>
          </div>
        </div>
      </div>

      {/* Interaction Preferences */}
      <div>
        <h3 className="font-medium text-gray-900 mb-3">Learning Style Preferences</h3>
        <div className="space-y-3">
          {Object.entries(patterns.interaction_preferences)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 4)
            .map(([type, percentage]) => (
              <div key={type} className="flex items-center">
                <div className="flex items-center w-40">
                  <span className="text-lg mr-2">
                    {getInteractionTypeIcon(type)}
                  </span>
                  <span className="text-sm text-gray-700">
                    {getInteractionTypeLabel(type)}
                  </span>
                </div>
                <div className="flex-1 mx-4">
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${percentage * 100}%` }}
                    />
                  </div>
                </div>
                <div className="text-sm text-gray-600 w-12 text-right">
                  {Math.round(percentage * 100)}%
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Difficulty Preference */}
      <div>
        <h3 className="font-medium text-gray-900 mb-3">Difficulty Preference</h3>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-yellow-700">Easier</span>
            <span className="text-sm text-yellow-700">Harder</span>
          </div>
          <div className="w-full bg-yellow-200 rounded-full h-3 relative">
            <div
              className="absolute top-0 left-0 h-3 bg-yellow-500 rounded-full transition-all duration-300"
              style={{ width: `${patterns.difficulty_preference * 100}%` }}
            />
            <div
              className="absolute top-0 w-3 h-3 bg-yellow-700 rounded-full transform -translate-x-1/2 transition-all duration-300"
              style={{ left: `${patterns.difficulty_preference * 100}%` }}
            />
          </div>
          <div className="mt-2 text-center text-sm text-yellow-700">
            {patterns.difficulty_preference < 0.3 ? 'Prefers easier problems' :
             patterns.difficulty_preference > 0.7 ? 'Enjoys challenging problems' :
             'Balanced difficulty preference'}
          </div>
        </div>
      </div>

      {/* Learning Insights Integration */}
      {insights && (
        <div className="bg-gray-50 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 mb-3">Pattern Insights</h3>
          <div className="space-y-2 text-sm">
            <div className="flex items-center">
              <span className="text-blue-500 mr-2">💡</span>
              <span className="text-gray-700">
                Your learning style is primarily <strong>{insights.learning_style}</strong>
              </span>
            </div>
            <div className="flex items-center">
              <span className="text-green-500 mr-2">⏰</span>
              <span className="text-gray-700">
                Optimal session length: <strong>{Math.round(insights.optimal_session_length / 60)} minutes</strong>
              </span>
            </div>
            <div className="flex items-center">
              <span className="text-purple-500 mr-2">📈</span>
              <span className="text-gray-700">
                Consistency score: <strong>{Math.round(insights.consistency_score * 100)}%</strong>
              </span>
            </div>
            {insights.challenge_readiness && (
              <div className="flex items-center">
                <span className="text-orange-500 mr-2">🚀</span>
                <span className="text-gray-700">
                  You're ready for more challenging content!
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};