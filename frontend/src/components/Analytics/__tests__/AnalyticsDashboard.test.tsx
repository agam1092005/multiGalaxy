/**
 * Tests for AnalyticsDashboard component
 */
import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AnalyticsDashboard } from '../AnalyticsDashboard';
import { analyticsService } from '../../../services/analyticsService';

// Mock the analytics service
jest.mock('../../../services/analyticsService', () => ({
  analyticsService: {
    getUserAnalytics: jest.fn(),
    getUserRecommendations: jest.fn(),
    getLearningInsights: jest.fn(),
    formatDuration: jest.fn((seconds) => `${Math.floor(seconds / 60)}m`),
    formatSuccessRate: jest.fn((rate) => `${Math.round(rate * 100)}%`),
  },
}));

// Mock child components
jest.mock('../SkillAssessmentChart', () => ({
  SkillAssessmentChart: ({ skillAssessments }: any) => (
    <div data-testid="skill-assessment-chart">
      Skills: {skillAssessments.length}
    </div>
  ),
}));

jest.mock('../ProgressMetricsCard', () => ({
  ProgressMetricsCard: ({ title, value }: any) => (
    <div data-testid="progress-metrics-card">
      {title}: {value}
    </div>
  ),
}));

jest.mock('../RecommendationsPanel', () => ({
  RecommendationsPanel: ({ recommendations }: any) => (
    <div data-testid="recommendations-panel">
      Recommendations: {recommendations.length}
    </div>
  ),
}));

jest.mock('../LearningPatternsChart', () => ({
  LearningPatternsChart: () => (
    <div data-testid="learning-patterns-chart">Learning Patterns</div>
  ),
}));

const mockAnalyticsData = {
  user_id: 'test-user-id',
  subject: 'Mathematics',
  skill_assessments: [
    {
      skill_name: 'algebra',
      proficiency: 0.75,
      confidence: 0.8,
      level: 'proficient' as const,
      trend: 'improving' as const,
      evidence_count: 10,
      last_assessed: '2023-01-01T00:00:00Z',
    },
  ],
  progress_metrics: {
    total_time_spent: 3600,
    sessions_completed: 5,
    problems_solved: 15,
    success_rate: 0.8,
    average_session_duration: 720,
    streak_days: 3,
    subjects_studied: ['Mathematics', 'Science'],
    improvement_rate: 15.0,
  },
  learning_patterns: {
    preferred_learning_times: [14, 16, 20],
    session_frequency: 4.2,
    attention_span: 1800,
    difficulty_preference: 0.6,
    interaction_preferences: {},
    common_mistake_patterns: [],
  },
  last_updated: '2023-01-01T00:00:00Z',
};

const mockRecommendations = [
  {
    type: 'skill_focus',
    title: 'Practice Algebra',
    description: 'Focus on algebraic equations',
    priority: 1,
    estimated_time: 20,
    skills_targeted: ['algebra'],
    created_at: '2023-01-01T00:00:00Z',
  },
];

const mockInsights = {
  learning_style: 'visual',
  optimal_session_length: 1800,
  best_study_times: [14, 16],
  consistency_score: 0.8,
  challenge_readiness: true,
  areas_of_strength: ['algebra', 'geometry'],
  growth_opportunities: ['calculus'],
};

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders loading state initially', () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<AnalyticsDashboard userId="test-user-id" />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('renders analytics dashboard with data', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('Learning Analytics')).toBeInTheDocument();
    });

    // Check if main sections are rendered
    expect(screen.getByTestId('skill-assessment-chart')).toBeInTheDocument();
    expect(screen.getAllByTestId('progress-metrics-card')).toHaveLength(4);
    expect(screen.getByTestId('recommendations-panel')).toBeInTheDocument();
    expect(screen.getByTestId('learning-patterns-chart')).toBeInTheDocument();
  });

  it('renders error state when data loading fails', async () => {
    const errorMessage = 'Failed to load analytics data';
    (analyticsService.getUserAnalytics as jest.Mock).mockRejectedValue(new Error(errorMessage));

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('Error Loading Analytics')).toBeInTheDocument();
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });

    // Check for retry button
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('renders no data state when analytics is null', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(null);

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('No Analytics Data')).toBeInTheDocument();
      expect(screen.getByText(/Start learning to see your progress/)).toBeInTheDocument();
    });
  });

  it('handles subject filter changes', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('Learning Analytics')).toBeInTheDocument();
    });

    // Find and change subject filter
    const subjectSelect = screen.getByLabelText('Subject:');
    fireEvent.change(subjectSelect, { target: { value: 'Mathematics' } });

    await waitFor(() => {
      expect(analyticsService.getUserAnalytics).toHaveBeenCalledWith('test-user-id', 'Mathematics');
    });
  });

  it('displays learning insights when available', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('Learning Insights')).toBeInTheDocument();
    });

    // Check for specific insights
    expect(screen.getByText('Learning Style')).toBeInTheDocument();
    expect(screen.getByText('visual')).toBeInTheDocument();
    expect(screen.getByText('Optimal Session')).toBeInTheDocument();
    expect(screen.getByText('Best Study Times')).toBeInTheDocument();
    expect(screen.getByText('Consistency Score')).toBeInTheDocument();
  });

  it('handles retry functionality', async () => {
    const errorMessage = 'Network error';
    (analyticsService.getUserAnalytics as jest.Mock)
      .mockRejectedValueOnce(new Error(errorMessage))
      .mockResolvedValueOnce(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" />);

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText('Error Loading Analytics')).toBeInTheDocument();
    });

    // Click retry button
    const retryButton = screen.getByText('Try Again');
    fireEvent.click(retryButton);

    // Wait for successful load
    await waitFor(() => {
      expect(screen.getByText('Learning Analytics')).toBeInTheDocument();
    });

    expect(analyticsService.getUserAnalytics).toHaveBeenCalledTimes(2);
  });

  it('passes correct props to child components', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('Learning Analytics')).toBeInTheDocument();
    });

    // Check that skill assessment chart receives correct data
    expect(screen.getByText('Skills: 1')).toBeInTheDocument();

    // Check that recommendations panel receives correct data
    expect(screen.getByText('Recommendations: 1')).toBeInTheDocument();
  });

  it('displays progress metrics correctly', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" />);

    await waitFor(() => {
      expect(screen.getByText('Learning Analytics')).toBeInTheDocument();
    });

    // Check that progress metrics are displayed
    expect(screen.getByText(/Study Time:/)).toBeInTheDocument();
    expect(screen.getByText(/Success Rate:/)).toBeInTheDocument();
    expect(screen.getByText(/Learning Streak:/)).toBeInTheDocument();
    expect(screen.getByText(/Sessions:/)).toBeInTheDocument();
  });

  it('handles subject prop correctly', async () => {
    (analyticsService.getUserAnalytics as jest.Mock).mockResolvedValue(mockAnalyticsData);
    (analyticsService.getUserRecommendations as jest.Mock).mockResolvedValue(mockRecommendations);
    (analyticsService.getLearningInsights as jest.Mock).mockResolvedValue(mockInsights);

    render(<AnalyticsDashboard userId="test-user-id" subject="Science" />);

    await waitFor(() => {
      expect(analyticsService.getUserAnalytics).toHaveBeenCalledWith('test-user-id', 'Science');
    });
  });
});