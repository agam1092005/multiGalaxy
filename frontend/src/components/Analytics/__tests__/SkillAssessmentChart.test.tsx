/**
 * Tests for SkillAssessmentChart component
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { SkillAssessmentChart } from '../SkillAssessmentChart';
import { analyticsService } from '../../../services/analyticsService';

// Mock the analytics service
jest.mock('../../../services/analyticsService', () => ({
  analyticsService: {
    getSkillLevelColor: jest.fn((level) => {
      const colors = {
        beginner: '#ef4444',
        developing: '#f97316',
        proficient: '#eab308',
        advanced: '#22c55e',
        mastery: '#8b5cf6',
      };
      return colors[level as keyof typeof colors] || '#6b7280';
    }),
    getTrendIcon: jest.fn((trend) => {
      const icons = {
        improving: '📈',
        stable: '➡️',
        declining: '📉',
        insufficient_data: '❓',
      };
      return icons[trend as keyof typeof icons] || '❓';
    }),
  },
}));

const mockSkillAssessments = [
  {
    skill_name: 'algebra',
    proficiency: 0.85,
    confidence: 0.9,
    level: 'advanced' as const,
    trend: 'improving' as const,
    evidence_count: 15,
    last_assessed: '2023-01-01T00:00:00Z',
  },
  {
    skill_name: 'geometry',
    proficiency: 0.65,
    confidence: 0.7,
    level: 'proficient' as const,
    trend: 'stable' as const,
    evidence_count: 8,
    last_assessed: '2023-01-02T00:00:00Z',
  },
  {
    skill_name: 'calculus',
    proficiency: 0.35,
    confidence: 0.5,
    level: 'developing' as const,
    trend: 'declining' as const,
    evidence_count: 5,
    last_assessed: '2023-01-03T00:00:00Z',
  },
];

describe('SkillAssessmentChart', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders empty state when no skill assessments provided', () => {
    render(<SkillAssessmentChart skillAssessments={[]} />);

    expect(screen.getByText('No skill assessments available yet.')).toBeInTheDocument();
    expect(screen.getByText(/Complete some learning activities/)).toBeInTheDocument();
  });

  it('renders skill assessments correctly', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    // Check that all skills are displayed
    expect(screen.getByText('algebra')).toBeInTheDocument();
    expect(screen.getByText('geometry')).toBeInTheDocument();
    expect(screen.getByText('calculus')).toBeInTheDocument();

    // Check proficiency percentages
    expect(screen.getByText('85%')).toBeInTheDocument(); // algebra
    expect(screen.getByText('65%')).toBeInTheDocument(); // geometry
    expect(screen.getByText('35%')).toBeInTheDocument(); // calculus

    // Check skill levels
    expect(screen.getByText('advanced')).toBeInTheDocument();
    expect(screen.getByText('proficient')).toBeInTheDocument();
    expect(screen.getByText('developing')).toBeInTheDocument();
  });

  it('displays evidence count and last assessed date', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    // Check evidence counts
    expect(screen.getByText('Based on 15 interactions')).toBeInTheDocument();
    expect(screen.getByText('Based on 8 interactions')).toBeInTheDocument();
    expect(screen.getByText('Based on 5 interactions')).toBeInTheDocument();

    // Check last assessed dates
    expect(screen.getByText(/Last assessed: 1\/1\/2023/)).toBeInTheDocument();
    expect(screen.getByText(/Last assessed: 1\/2\/2023/)).toBeInTheDocument();
    expect(screen.getByText(/Last assessed: 1\/3\/2023/)).toBeInTheDocument();
  });

  it('displays trend information correctly', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    // Check trend labels
    expect(screen.getByText('improving')).toBeInTheDocument();
    expect(screen.getByText('stable')).toBeInTheDocument();
    expect(screen.getByText('declining')).toBeInTheDocument();

    // Verify trend icons are called
    expect(analyticsService.getTrendIcon).toHaveBeenCalledWith('improving');
    expect(analyticsService.getTrendIcon).toHaveBeenCalledWith('stable');
    expect(analyticsService.getTrendIcon).toHaveBeenCalledWith('declining');
  });

  it('displays confidence percentages correctly', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    expect(screen.getByText('90% confidence')).toBeInTheDocument(); // algebra
    expect(screen.getByText('70% confidence')).toBeInTheDocument(); // geometry
    expect(screen.getByText('50% confidence')).toBeInTheDocument(); // calculus
  });

  it('sorts skills by proficiency level (highest first)', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    const skillElements = screen.getAllByText(/algebra|geometry|calculus/);
    
    // First skill should be algebra (highest proficiency: 0.85)
    expect(skillElements[0]).toHaveTextContent('algebra');
    
    // Second should be geometry (0.65)
    expect(skillElements[1]).toHaveTextContent('geometry');
    
    // Third should be calculus (lowest proficiency: 0.35)
    expect(skillElements[2]).toHaveTextContent('calculus');
  });

  it('displays skill summary statistics', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    expect(screen.getByText('Skill Summary')).toBeInTheDocument();

    // Check summary counts - use more specific queries to avoid conflicts
    const summarySection = screen.getByText('Skill Summary').closest('div');
    expect(summarySection).toBeInTheDocument();
    
    // Check that we have the right number of skills in each category
    const masteryCount = summarySection?.querySelector('.text-purple-600');
    const advancedCount = summarySection?.querySelector('.text-green-600');
    const proficientCount = summarySection?.querySelector('.text-yellow-600');
    const developingCount = summarySection?.querySelector('.text-orange-600');
    
    expect(masteryCount).toHaveTextContent('0');
    expect(advancedCount).toHaveTextContent('1');
    expect(proficientCount).toHaveTextContent('1');
    expect(developingCount).toHaveTextContent('1');

    // Check summary labels
    expect(screen.getByText('Mastery')).toBeInTheDocument();
    expect(screen.getByText('Advanced')).toBeInTheDocument();
    expect(screen.getByText('Proficient')).toBeInTheDocument();
    expect(screen.getByText('Developing')).toBeInTheDocument();
  });

  it('uses correct colors for skill levels', () => {
    render(<SkillAssessmentChart skillAssessments={mockSkillAssessments} />);

    // Verify color function is called for each skill level
    expect(analyticsService.getSkillLevelColor).toHaveBeenCalledWith('advanced');
    expect(analyticsService.getSkillLevelColor).toHaveBeenCalledWith('proficient');
    expect(analyticsService.getSkillLevelColor).toHaveBeenCalledWith('developing');
  });

  it('handles single skill assessment', () => {
    const singleSkill = [mockSkillAssessments[0]];
    render(<SkillAssessmentChart skillAssessments={singleSkill} />);

    expect(screen.getByText('algebra')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
    expect(screen.getByText('Based on 15 interactions')).toBeInTheDocument();
  });

  it('handles skill with insufficient data trend', () => {
    const skillWithInsufficientData = [
      {
        ...mockSkillAssessments[0],
        trend: 'insufficient_data' as const,
      },
    ];

    render(<SkillAssessmentChart skillAssessments={skillWithInsufficientData} />);

    expect(screen.getByText('insufficient data')).toBeInTheDocument();
    expect(analyticsService.getTrendIcon).toHaveBeenCalledWith('insufficient_data');
  });

  it('handles mastery level skills in summary', () => {
    const skillsWithMastery = [
      {
        ...mockSkillAssessments[0],
        level: 'mastery' as const,
        proficiency: 0.95,
      },
      ...mockSkillAssessments.slice(1),
    ];

    render(<SkillAssessmentChart skillAssessments={skillsWithMastery} />);

    // Should show 1 mastery skill in summary
    const summarySection = screen.getByText('Skill Summary').closest('div');
    expect(summarySection).toBeInTheDocument();
  });

  it('handles beginner level skills', () => {
    const skillsWithBeginner = [
      {
        skill_name: 'trigonometry',
        proficiency: 0.2,
        confidence: 0.3,
        level: 'beginner' as const,
        trend: 'improving' as const,
        evidence_count: 3,
        last_assessed: '2023-01-04T00:00:00Z',
      },
    ];

    render(<SkillAssessmentChart skillAssessments={skillsWithBeginner} />);

    expect(screen.getByText('trigonometry')).toBeInTheDocument();
    expect(screen.getByText('beginner')).toBeInTheDocument();
    expect(screen.getByText('20%')).toBeInTheDocument();
    expect(analyticsService.getSkillLevelColor).toHaveBeenCalledWith('beginner');
  });
});