/**
 * Skill assessment chart component for visualizing skill proficiency levels
 */
import React from 'react';
import { SkillAssessment, analyticsService } from '../../services/analyticsService';

interface SkillAssessmentChartProps {
  skillAssessments: SkillAssessment[];
}

export const SkillAssessmentChart: React.FC<SkillAssessmentChartProps> = ({
  skillAssessments
}) => {
  if (!skillAssessments || skillAssessments.length === 0) {
    return (
      <div className="text-center py-8">
        <div className="text-4xl mb-4">📈</div>
        <p className="text-gray-600">No skill assessments available yet.</p>
        <p className="text-sm text-gray-500 mt-2">
          Complete some learning activities to see your skill progress here.
        </p>
      </div>
    );
  }

  // Sort skills by proficiency level
  const sortedSkills = [...skillAssessments].sort((a, b) => b.proficiency - a.proficiency);

  return (
    <div className="space-y-4">
      {sortedSkills.map((skill, index) => (
        <div key={skill.skill_name} className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <h3 className="font-medium text-gray-900">{skill.skill_name}</h3>
              <span className="ml-2 text-sm">
                {analyticsService.getTrendIcon(skill.trend)}
              </span>
            </div>
            <div className="flex items-center space-x-3">
              <span 
                className="px-2 py-1 rounded-full text-xs font-medium text-white"
                style={{ backgroundColor: analyticsService.getSkillLevelColor(skill.level) }}
              >
                {skill.level}
              </span>
              <span className="text-sm text-gray-600">
                {Math.round(skill.proficiency * 100)}%
              </span>
            </div>
          </div>

          {/* Proficiency Bar */}
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
              <span>Proficiency</span>
              <span>{Math.round(skill.confidence * 100)}% confidence</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${skill.proficiency * 100}%`,
                  backgroundColor: analyticsService.getSkillLevelColor(skill.level)
                }}
              />
            </div>
          </div>

          {/* Skill Details */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              Based on {skill.evidence_count} interaction{skill.evidence_count !== 1 ? 's' : ''}
            </span>
            <span>
              Last assessed: {new Date(skill.last_assessed).toLocaleDateString()}
            </span>
          </div>

          {/* Trend Indicator */}
          <div className="mt-2">
            <div className="flex items-center text-xs">
              <span className="text-gray-600 mr-2">Trend:</span>
              <span 
                className={`font-medium ${
                  skill.trend === 'improving' ? 'text-green-600' :
                  skill.trend === 'declining' ? 'text-red-600' :
                  skill.trend === 'stable' ? 'text-blue-600' :
                  'text-gray-600'
                }`}
              >
                {skill.trend.replace('_', ' ')}
              </span>
            </div>
          </div>
        </div>
      ))}

      {/* Summary Stats */}
      <div className="mt-6 bg-gray-50 rounded-lg p-4">
        <h4 className="font-medium text-gray-900 mb-3">Skill Summary</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-purple-600">
              {skillAssessments.filter(s => s.level === 'mastery').length}
            </div>
            <div className="text-xs text-gray-600">Mastery</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-green-600">
              {skillAssessments.filter(s => s.level === 'advanced').length}
            </div>
            <div className="text-xs text-gray-600">Advanced</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-yellow-600">
              {skillAssessments.filter(s => s.level === 'proficient').length}
            </div>
            <div className="text-xs text-gray-600">Proficient</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-orange-600">
              {skillAssessments.filter(s => ['developing', 'beginner'].includes(s.level)).length}
            </div>
            <div className="text-xs text-gray-600">Developing</div>
          </div>
        </div>
      </div>
    </div>
  );
};