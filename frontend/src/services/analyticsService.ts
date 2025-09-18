/**
 * Analytics service for learning progress tracking and reporting
 */

export interface SkillAssessment {
  skill_name: string;
  proficiency: number;
  confidence: number;
  level: 'beginner' | 'developing' | 'proficient' | 'advanced' | 'mastery';
  trend: 'improving' | 'stable' | 'declining' | 'insufficient_data';
  evidence_count: number;
  last_assessed: string;
}

export interface ProgressMetrics {
  total_time_spent: number;
  sessions_completed: number;
  problems_solved: number;
  success_rate: number;
  average_session_duration: number;
  streak_days: number;
  subjects_studied: string[];
  improvement_rate: number;
}

export interface LearningPatterns {
  preferred_learning_times: number[];
  session_frequency: number;
  attention_span: number;
  difficulty_preference: number;
  interaction_preferences: Record<string, number>;
  common_mistake_patterns: string[];
}

export interface LearningAnalytics {
  user_id: string;
  subject: string;
  skill_assessments: SkillAssessment[];
  progress_metrics: ProgressMetrics;
  learning_patterns: LearningPatterns;
  last_updated: string;
}

export interface Recommendation {
  type: string;
  title: string;
  description: string;
  priority: number;
  estimated_time: number;
  skills_targeted: string[];
  created_at: string;
}

export interface ProgressReport {
  id: string;
  report_type: string;
  period_start: string;
  period_end: string;
  summary_data: Record<string, any>;
  recommendations: Recommendation[];
  generated_at: string;
}

export interface ParentDashboardChild {
  user_id: string;
  name: string;
  weekly_progress: ProgressMetrics;
  current_streak: number;
  subjects_studied: string[];
  recent_activity: Array<{
    date: string;
    subject: string;
    type: string;
    success_rate?: number;
    time_spent: number;
  }>;
  alerts: Array<{
    type: string;
    message: string;
    severity: string;
    created_at: string;
  }>;
  skill_summary?: {
    total_skills: number;
    mastered_skills: number;
    developing_skills: number;
    needs_attention: number;
  };
}

export interface ParentDashboard {
  children: ParentDashboardChild[];
  summary: {
    total_study_time: number;
    total_sessions: number;
    average_success_rate: number;
    active_children: number;
  };
}

export interface LearningInsights {
  learning_style: string;
  optimal_session_length: number;
  best_study_times: number[];
  consistency_score: number;
  challenge_readiness: boolean;
  areas_of_strength: string[];
  growth_opportunities: string[];
}

class AnalyticsService {
  private baseUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = localStorage.getItem('token');
    
    const response = await fetch(`${this.baseUrl}/api/analytics${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * Get comprehensive analytics for a user
   */
  async getUserAnalytics(userId: string, subject?: string): Promise<LearningAnalytics> {
    const params = new URLSearchParams();
    if (subject) params.append('subject', subject);
    
    return this.makeRequest<LearningAnalytics>(
      `/user/${userId}?${params.toString()}`
    );
  }

  /**
   * Get personalized learning recommendations
   */
  async getUserRecommendations(
    userId: string,
    subject?: string,
    limit: number = 5
  ): Promise<Recommendation[]> {
    const params = new URLSearchParams();
    if (subject) params.append('subject', subject);
    params.append('limit', limit.toString());
    
    return this.makeRequest<Recommendation[]>(
      `/user/${userId}/recommendations?${params.toString()}`
    );
  }

  /**
   * Record a user interaction for analytics
   */
  async recordInteraction(
    userId: string,
    sessionId: string,
    interactionType: string,
    subject: string,
    skillTags: string[],
    options: {
      successRate?: number;
      timeSpent?: number;
      difficultyLevel?: number;
      interactionData?: Record<string, any>;
      aiFeedbackQuality?: number;
    } = {}
  ): Promise<{ message: string; interaction_id: string }> {
    return this.makeRequest<{ message: string; interaction_id: string }>(
      `/user/${userId}/interaction`,
      {
        method: 'POST',
        body: JSON.stringify({
          session_id: sessionId,
          interaction_type: interactionType,
          subject,
          skill_tags: skillTags,
          success_rate: options.successRate,
          time_spent: options.timeSpent || 0,
          difficulty_level: options.difficultyLevel || 0.5,
          interaction_data: options.interactionData,
          ai_feedback_quality: options.aiFeedbackQuality,
        }),
      }
    );
  }

  /**
   * Generate a progress report
   */
  async generateProgressReport(
    userId: string,
    reportType: 'weekly' | 'monthly' | 'custom' = 'weekly',
    subject?: string
  ): Promise<ProgressReport> {
    const params = new URLSearchParams();
    params.append('report_type', reportType);
    if (subject) params.append('subject', subject);
    
    return this.makeRequest<ProgressReport>(
      `/user/${userId}/progress-report?${params.toString()}`
    );
  }

  /**
   * Get parent dashboard data
   */
  async getParentDashboard(childUserIds: string[]): Promise<ParentDashboard> {
    const params = new URLSearchParams();
    childUserIds.forEach(id => params.append('child_user_ids', id));
    
    return this.makeRequest<ParentDashboard>(
      `/parent-dashboard?${params.toString()}`
    );
  }

  /**
   * Get learning insights for a user
   */
  async getLearningInsights(userId: string): Promise<LearningInsights> {
    return this.makeRequest<LearningInsights>(`/user/${userId}/learning-insights`);
  }

  /**
   * Get skill trends over time
   */
  async getSkillTrends(
    userId: string,
    subject: string,
    skillName: string,
    days: number = 30
  ): Promise<any> {
    const params = new URLSearchParams();
    params.append('subject', subject);
    params.append('skill_name', skillName);
    params.append('days', days.toString());
    
    return this.makeRequest<any>(
      `/user/${userId}/skill-trends?${params.toString()}`
    );
  }

  /**
   * Helper method to format time duration
   */
  formatDuration(seconds: number): string {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }

  /**
   * Helper method to format success rate as percentage
   */
  formatSuccessRate(rate: number): string {
    return `${Math.round(rate * 100)}%`;
  }

  /**
   * Helper method to get skill level color
   */
  getSkillLevelColor(level: string): string {
    const colors = {
      beginner: '#ef4444',     // red
      developing: '#f97316',   // orange
      proficient: '#eab308',   // yellow
      advanced: '#22c55e',     // green
      mastery: '#8b5cf6',      // purple
    };
    return colors[level as keyof typeof colors] || '#6b7280';
  }

  /**
   * Helper method to get trend icon
   */
  getTrendIcon(trend: string): string {
    const icons = {
      improving: '📈',
      stable: '➡️',
      declining: '📉',
      insufficient_data: '❓',
    };
    return icons[trend as keyof typeof icons] || '❓';
  }
}

export const analyticsService = new AnalyticsService();