/**
 * Main analytics dashboard component for learning progress tracking
 */
import React, { useState, useEffect } from 'react';
import { 
  analyticsService, 
  LearningAnalytics, 
  Recommendation,
  LearningInsights 
} from '../../services/analyticsService';
import { SkillAssessmentChart } from './SkillAssessmentChart';
import { ProgressMetricsCard } from './ProgressMetricsCard';
import { RecommendationsPanel } from './RecommendationsPanel';
import { LearningPatternsChart } from './LearningPatternsChart';

interface AnalyticsDashboardProps {
  userId: string;
  subject?: string;
}

export const AnalyticsDashboard: React.FC<AnalyticsDashboardProps> = ({
  userId,
  subject
}) => {
  const [analytics, setAnalytics] = useState<LearningAnalytics | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [insights, setInsights] = useState<LearningInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>(subject || '');

  useEffect(() => {
    loadAnalyticsData();
  }, [userId, selectedSubject]);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [analyticsData, recommendationsData, insightsData] = await Promise.all([
        analyticsService.getUserAnalytics(userId, selectedSubject || undefined),
        analyticsService.getUserRecommendations(userId, selectedSubject || undefined),
        analyticsService.getLearningInsights(userId)
      ]);

      setAnalytics(analyticsData);
      setRecommendations(recommendationsData);
      setInsights(insightsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubjectChange = (newSubject: string) => {
    setSelectedSubject(newSubject);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500" role="status" aria-label="Loading analytics data"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error Loading Analytics</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={loadAnalyticsData}
              className="bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!analytics) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">📊</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Analytics Data</h2>
          <p className="text-gray-600 mb-4">
            Start learning to see your progress and insights here!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Learning Analytics</h1>
              <p className="mt-1 text-sm text-gray-600">
                Track your progress and discover insights about your learning journey
              </p>
            </div>
            
            {/* Subject Filter */}
            <div className="flex items-center space-x-4">
              <label htmlFor="subject-select" className="text-sm font-medium text-gray-700">
                Subject:
              </label>
              <select
                id="subject-select"
                value={selectedSubject}
                onChange={(e) => handleSubjectChange(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">All Subjects</option>
                {analytics.progress_metrics.subjects_studied.map((subj) => (
                  <option key={subj} value={subj}>
                    {subj}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Progress Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <ProgressMetricsCard
            title="Study Time"
            value={analyticsService.formatDuration(analytics.progress_metrics.total_time_spent)}
            icon="⏱️"
            trend={analytics.progress_metrics.improvement_rate > 0 ? 'up' : 'down'}
            trendValue={`${Math.abs(analytics.progress_metrics.improvement_rate).toFixed(1)}%`}
          />
          <ProgressMetricsCard
            title="Success Rate"
            value={analyticsService.formatSuccessRate(analytics.progress_metrics.success_rate)}
            icon="🎯"
            trend={analytics.progress_metrics.success_rate > 0.7 ? 'up' : 'down'}
          />
          <ProgressMetricsCard
            title="Learning Streak"
            value={`${analytics.progress_metrics.streak_days} days`}
            icon="🔥"
            trend={analytics.progress_metrics.streak_days > 0 ? 'up' : 'down'}
          />
          <ProgressMetricsCard
            title="Sessions"
            value={analytics.progress_metrics.sessions_completed.toString()}
            icon="📚"
            trend="neutral"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Skills and Progress */}
          <div className="lg:col-span-2 space-y-8">
            {/* Skill Assessments */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Skill Assessment</h2>
              <SkillAssessmentChart skillAssessments={analytics.skill_assessments} />
            </div>

            {/* Learning Patterns */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Learning Patterns</h2>
              <LearningPatternsChart 
                patterns={analytics.learning_patterns}
                insights={insights}
              />
            </div>

            {/* Learning Insights */}
            {insights && (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">Learning Insights</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h3 className="font-medium text-blue-900 mb-2">Learning Style</h3>
                    <p className="text-blue-700 capitalize">{insights.learning_style}</p>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <h3 className="font-medium text-green-900 mb-2">Optimal Session</h3>
                    <p className="text-green-700">
                      {analyticsService.formatDuration(insights.optimal_session_length)}
                    </p>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4">
                    <h3 className="font-medium text-purple-900 mb-2">Best Study Times</h3>
                    <p className="text-purple-700">
                      {insights.best_study_times.map(hour => `${hour}:00`).join(', ')}
                    </p>
                  </div>
                  <div className="bg-yellow-50 rounded-lg p-4">
                    <h3 className="font-medium text-yellow-900 mb-2">Consistency Score</h3>
                    <p className="text-yellow-700">
                      {Math.round(insights.consistency_score * 100)}%
                    </p>
                  </div>
                </div>

                {/* Strengths and Growth Areas */}
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h3 className="font-medium text-gray-900 mb-3">Areas of Strength</h3>
                    <div className="space-y-2">
                      {insights.areas_of_strength.slice(0, 3).map((skill, index) => (
                        <div key={index} className="flex items-center text-sm">
                          <span className="text-green-500 mr-2">✓</span>
                          <span className="text-gray-700">{skill}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 mb-3">Growth Opportunities</h3>
                    <div className="space-y-2">
                      {insights.growth_opportunities.slice(0, 3).map((skill, index) => (
                        <div key={index} className="flex items-center text-sm">
                          <span className="text-blue-500 mr-2">→</span>
                          <span className="text-gray-700">{skill}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Column - Recommendations */}
          <div className="space-y-8">
            <RecommendationsPanel 
              recommendations={recommendations}
              onRefresh={loadAnalyticsData}
            />
          </div>
        </div>
      </div>
    </div>
  );
};