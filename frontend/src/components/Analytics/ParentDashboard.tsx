/**
 * Parent dashboard component for monitoring children's learning progress
 */
import React, { useState, useEffect } from 'react';
import { 
  analyticsService, 
  ParentDashboard as ParentDashboardData,
  ParentDashboardChild 
} from '../../services/analyticsService';

interface ParentDashboardProps {
  childUserIds: string[];
}

export const ParentDashboard: React.FC<ParentDashboardProps> = ({
  childUserIds
}) => {
  const [dashboardData, setDashboardData] = useState<ParentDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChild, setSelectedChild] = useState<string | null>(null);

  useEffect(() => {
    loadDashboardData();
  }, [childUserIds]);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await analyticsService.getParentDashboard(childUserIds);
      setDashboardData(data);
      if (data.children.length > 0 && !selectedChild) {
        setSelectedChild(data.children[0].user_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getAlertSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'positive':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'performance_concern':
        return '⚠️';
      case 'inactivity':
        return '😴';
      case 'achievement':
        return '🎉';
      default:
        return 'ℹ️';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-500"></div>
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
              <h3 className="text-sm font-medium text-red-800">Error Loading Dashboard</h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
          <div className="mt-4">
            <button
              onClick={loadDashboardData}
              className="bg-red-100 hover:bg-red-200 text-red-800 px-4 py-2 rounded-md text-sm font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!dashboardData) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">👨‍👩‍👧‍👦</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Dashboard Data</h2>
          <p className="text-gray-600">No children's learning data available.</p>
        </div>
      </div>
    );
  }

  const selectedChildData = dashboardData.children.find(
    child => child.user_id === selectedChild
  );

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Parent Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor your children's learning progress and achievements
          </p>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="text-2xl mr-3">⏱️</div>
              <div>
                <p className="text-sm font-medium text-gray-600">Total Study Time</p>
                <p className="text-2xl font-bold text-gray-900">
                  {analyticsService.formatDuration(dashboardData.summary.total_study_time)}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="text-2xl mr-3">📚</div>
              <div>
                <p className="text-sm font-medium text-gray-600">Total Sessions</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardData.summary.total_sessions}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="text-2xl mr-3">🎯</div>
              <div>
                <p className="text-sm font-medium text-gray-600">Average Success</p>
                <p className="text-2xl font-bold text-gray-900">
                  {analyticsService.formatSuccessRate(dashboardData.summary.average_success_rate)}
                </p>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex items-center">
              <div className="text-2xl mr-3">👥</div>
              <div>
                <p className="text-sm font-medium text-gray-600">Active Children</p>
                <p className="text-2xl font-bold text-gray-900">
                  {dashboardData.summary.active_children}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Child Selection and Details */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Child List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Children</h2>
              <div className="space-y-3">
                {dashboardData.children.map((child) => (
                  <button
                    key={child.user_id}
                    onClick={() => setSelectedChild(child.user_id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selectedChild === child.user_id
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900">{child.name}</p>
                        <p className="text-sm text-gray-600">
                          {child.current_streak} day streak
                        </p>
                      </div>
                      {child.alerts.length > 0 && (
                        <div className="flex items-center">
                          <span className="bg-red-100 text-red-600 text-xs px-2 py-1 rounded-full">
                            {child.alerts.length}
                          </span>
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Selected Child Details */}
          <div className="lg:col-span-3">
            {selectedChildData ? (
              <div className="space-y-6">
                {/* Child Header */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900">
                        {selectedChildData.name}
                      </h2>
                      <p className="text-gray-600">
                        {selectedChildData.subjects_studied.length} subject{selectedChildData.subjects_studied.length !== 1 ? 's' : ''} studied this week
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-blue-600">
                        🔥 {selectedChildData.current_streak}
                      </div>
                      <div className="text-sm text-gray-600">day streak</div>
                    </div>
                  </div>
                </div>

                {/* Alerts */}
                {selectedChildData.alerts.length > 0 && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Alerts</h3>
                    <div className="space-y-3">
                      {selectedChildData.alerts.map((alert, index) => (
                        <div
                          key={index}
                          className={`border rounded-lg p-3 ${getAlertSeverityColor(alert.severity)}`}
                        >
                          <div className="flex items-center">
                            <span className="text-lg mr-2">
                              {getAlertIcon(alert.type)}
                            </span>
                            <div className="flex-1">
                              <p className="font-medium">{alert.message}</p>
                              <p className="text-xs mt-1">
                                {new Date(alert.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Weekly Progress */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">This Week's Progress</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">
                        {analyticsService.formatDuration(selectedChildData.weekly_progress.total_time_spent)}
                      </div>
                      <div className="text-sm text-gray-600">Study Time</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {selectedChildData.weekly_progress.sessions_completed}
                      </div>
                      <div className="text-sm text-gray-600">Sessions</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">
                        {analyticsService.formatSuccessRate(selectedChildData.weekly_progress.success_rate)}
                      </div>
                      <div className="text-sm text-gray-600">Success Rate</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">
                        {selectedChildData.weekly_progress.problems_solved}
                      </div>
                      <div className="text-sm text-gray-600">Problems Solved</div>
                    </div>
                  </div>
                </div>

                {/* Skill Summary */}
                {selectedChildData.skill_summary && (
                  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Skill Development</h3>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="text-center p-4 bg-purple-50 rounded-lg">
                        <div className="text-2xl font-bold text-purple-600">
                          {selectedChildData.skill_summary.mastered_skills}
                        </div>
                        <div className="text-sm text-purple-700">Mastered</div>
                      </div>
                      <div className="text-center p-4 bg-green-50 rounded-lg">
                        <div className="text-2xl font-bold text-green-600">
                          {selectedChildData.skill_summary.developing_skills}
                        </div>
                        <div className="text-sm text-green-700">Developing</div>
                      </div>
                      <div className="text-center p-4 bg-yellow-50 rounded-lg">
                        <div className="text-2xl font-bold text-yellow-600">
                          {selectedChildData.skill_summary.needs_attention}
                        </div>
                        <div className="text-sm text-yellow-700">Needs Attention</div>
                      </div>
                      <div className="text-center p-4 bg-blue-50 rounded-lg">
                        <div className="text-2xl font-bold text-blue-600">
                          {selectedChildData.skill_summary.total_skills}
                        </div>
                        <div className="text-sm text-blue-700">Total Skills</div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Recent Activity */}
                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
                  {selectedChildData.recent_activity.length > 0 ? (
                    <div className="space-y-3">
                      {selectedChildData.recent_activity.slice(0, 5).map((activity, index) => (
                        <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                          <div className="flex items-center">
                            <div className="text-sm">
                              <p className="font-medium text-gray-900">{activity.subject}</p>
                              <p className="text-gray-600">{activity.type.replace('_', ' ')}</p>
                            </div>
                          </div>
                          <div className="text-right text-sm">
                            <p className="text-gray-900">
                              {analyticsService.formatDuration(activity.time_spent)}
                            </p>
                            <p className="text-gray-600">
                              {new Date(activity.date).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500 text-center py-4">No recent activity</p>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 text-center">
                <p className="text-gray-600">Select a child to view their details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};