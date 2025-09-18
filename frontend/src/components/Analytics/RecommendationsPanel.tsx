/**
 * Recommendations panel component for displaying personalized learning suggestions
 */
import React from 'react';
import { Recommendation } from '../../services/analyticsService';

interface RecommendationsPanelProps {
  recommendations: Recommendation[];
  onRefresh: () => void;
}

export const RecommendationsPanel: React.FC<RecommendationsPanelProps> = ({
  recommendations,
  onRefresh
}) => {
  const getPriorityColor = (priority: number) => {
    switch (priority) {
      case 1:
        return 'bg-red-100 text-red-800 border-red-200';
      case 2:
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 3:
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 4:
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 5:
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getPriorityLabel = (priority: number) => {
    switch (priority) {
      case 1:
        return 'High Priority';
      case 2:
        return 'Medium-High';
      case 3:
        return 'Medium';
      case 4:
        return 'Low-Medium';
      case 5:
        return 'Low Priority';
      default:
        return 'Unknown';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'skill_focus':
        return '🎯';
      case 'practice_suggestion':
        return '💡';
      case 'difficulty_adjustment':
        return '⚖️';
      default:
        return '📝';
    }
  };

  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">Recommendations</h2>
          <button
            onClick={onRefresh}
            className="text-blue-600 hover:text-blue-800 text-sm font-medium"
          >
            Refresh
          </button>
        </div>
        <div className="text-center py-8">
          <div className="text-4xl mb-4">🎯</div>
          <p className="text-gray-600">No recommendations available yet.</p>
          <p className="text-sm text-gray-500 mt-2">
            Complete more learning activities to get personalized suggestions.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-gray-900">Recommendations</h2>
        <button
          onClick={onRefresh}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        {recommendations.map((recommendation, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center">
                <span className="text-xl mr-2">
                  {getTypeIcon(recommendation.type)}
                </span>
                <h3 className="font-medium text-gray-900">
                  {recommendation.title}
                </h3>
              </div>
              <span
                className={`px-2 py-1 rounded-full text-xs font-medium border ${getPriorityColor(
                  recommendation.priority
                )}`}
              >
                {getPriorityLabel(recommendation.priority)}
              </span>
            </div>

            {/* Description */}
            <p className="text-sm text-gray-600 mb-3">
              {recommendation.description}
            </p>

            {/* Details */}
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center space-x-4">
                {recommendation.estimated_time > 0 && (
                  <span className="flex items-center">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
                    </svg>
                    {recommendation.estimated_time} min
                  </span>
                )}
                {recommendation.skills_targeted.length > 0 && (
                  <span className="flex items-center">
                    <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {recommendation.skills_targeted.length} skill{recommendation.skills_targeted.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <span>
                {new Date(recommendation.created_at).toLocaleDateString()}
              </span>
            </div>

            {/* Skills Targeted */}
            {recommendation.skills_targeted.length > 0 && (
              <div className="mt-3">
                <div className="flex flex-wrap gap-1">
                  {recommendation.skills_targeted.slice(0, 3).map((skill, skillIndex) => (
                    <span
                      key={skillIndex}
                      className="px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full"
                    >
                      {skill}
                    </span>
                  ))}
                  {recommendation.skills_targeted.length > 3 && (
                    <span className="px-2 py-1 bg-gray-50 text-gray-600 text-xs rounded-full">
                      +{recommendation.skills_targeted.length - 3} more
                    </span>
                  )}
                </div>
              </div>
            )}

            {/* Action Button */}
            <div className="mt-4">
              <button className="w-full bg-blue-50 hover:bg-blue-100 text-blue-700 py-2 px-4 rounded-md text-sm font-medium transition-colors">
                Start Practice Session
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">
            {recommendations.length} recommendation{recommendations.length !== 1 ? 's' : ''} available
          </span>
          <span className="text-gray-500">
            Updated {new Date().toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
};