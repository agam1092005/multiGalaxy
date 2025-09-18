"""
Knowledge Base Management System for Multi-Galaxy-Note.
Handles subject-specific content organization and curriculum alignment.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from .rag_system import RAGSystem

logger = logging.getLogger(__name__)

class SubjectArea(Enum):
    """Enumeration of supported subject areas."""
    MATHEMATICS = "mathematics"
    SCIENCE = "science"
    LANGUAGE_ARTS = "language_arts"
    HISTORY = "history"
    GENERAL = "general"

class GradeLevel(Enum):
    """Enumeration of grade levels."""
    ELEMENTARY = "elementary"  # K-5
    MIDDLE = "middle"         # 6-8
    HIGH = "high"            # 9-12
    COLLEGE = "college"      # College level

@dataclass
class KnowledgeItem:
    """Represents a single knowledge item in the knowledge base."""
    id: str
    title: str
    content: str
    subject: SubjectArea
    grade_level: GradeLevel
    topics: List[str]
    difficulty_level: int  # 1-10 scale
    prerequisites: List[str]
    learning_objectives: List[str]
    created_at: datetime
    updated_at: datetime
    source: str
    metadata: Dict[str, Any]

@dataclass
class CurriculumStandard:
    """Represents a curriculum standard."""
    id: str
    name: str
    description: str
    subject: SubjectArea
    grade_level: GradeLevel
    standard_code: str  # e.g., "CCSS.MATH.5.NBT.1"
    learning_objectives: List[str]

class KnowledgeBaseManager:
    """
    Manages the knowledge base with subject-specific organization and curriculum alignment.
    """
    
    def __init__(self, rag_system: RAGSystem):
        self.rag_system = rag_system
        self.knowledge_base_path = Path("knowledge_base")
        self.knowledge_base_path.mkdir(exist_ok=True)
        
        # Initialize subject-specific knowledge structures
        self.subject_taxonomies = self._load_subject_taxonomies()
        self.curriculum_standards = self._load_curriculum_standards()
        self.knowledge_items: Dict[str, KnowledgeItem] = {}
        
        # Load existing knowledge items
        self._load_knowledge_items()
    
    def _load_subject_taxonomies(self) -> Dict[SubjectArea, Dict[str, Any]]:
        """Load subject-specific taxonomies and topic hierarchies."""
        taxonomies = {
            SubjectArea.MATHEMATICS: {
                "elementary": {
                    "number_operations": ["counting", "addition", "subtraction", "multiplication", "division"],
                    "geometry": ["shapes", "measurement", "spatial_reasoning"],
                    "data_analysis": ["graphs", "charts", "basic_statistics"]
                },
                "middle": {
                    "algebra": ["variables", "equations", "inequalities", "functions"],
                    "geometry": ["area", "volume", "angles", "coordinate_plane"],
                    "statistics": ["probability", "data_collection", "analysis"]
                },
                "high": {
                    "algebra": ["polynomials", "rational_functions", "exponential_functions"],
                    "geometry": ["trigonometry", "proofs", "transformations"],
                    "calculus": ["limits", "derivatives", "integrals"],
                    "statistics": ["hypothesis_testing", "regression", "distributions"]
                }
            },
            SubjectArea.SCIENCE: {
                "elementary": {
                    "physical_science": ["matter", "energy", "forces", "motion"],
                    "life_science": ["plants", "animals", "habitats", "life_cycles"],
                    "earth_science": ["weather", "rocks", "water_cycle", "solar_system"]
                },
                "middle": {
                    "physical_science": ["atoms", "molecules", "chemical_reactions", "waves"],
                    "life_science": ["cells", "genetics", "evolution", "ecosystems"],
                    "earth_science": ["plate_tectonics", "climate", "natural_resources"]
                },
                "high": {
                    "physics": ["mechanics", "thermodynamics", "electromagnetism", "quantum"],
                    "chemistry": ["atomic_structure", "bonding", "stoichiometry", "kinetics"],
                    "biology": ["molecular_biology", "genetics", "ecology", "evolution"]
                }
            },
            SubjectArea.LANGUAGE_ARTS: {
                "elementary": {
                    "reading": ["phonics", "fluency", "comprehension", "vocabulary"],
                    "writing": ["sentence_structure", "paragraphs", "narrative", "descriptive"],
                    "speaking": ["presentation", "discussion", "listening"]
                },
                "middle": {
                    "reading": ["literary_analysis", "informational_text", "critical_thinking"],
                    "writing": ["essay_structure", "research", "persuasive", "expository"],
                    "language": ["grammar", "syntax", "word_choice"]
                },
                "high": {
                    "literature": ["analysis", "interpretation", "literary_devices", "themes"],
                    "composition": ["argumentative", "analytical", "research_papers"],
                    "rhetoric": ["persuasion", "audience", "purpose", "style"]
                }
            }
        }
        return taxonomies
    
    def _load_curriculum_standards(self) -> Dict[str, CurriculumStandard]:
        """Load curriculum standards from configuration files."""
        standards = {}
        
        # Sample Common Core Math Standards
        math_standards = [
            CurriculumStandard(
                id="ccss_math_5_nbt_1",
                name="Place Value Understanding",
                description="Recognize that in a multi-digit number, a digit in one place represents 10 times as much as it represents in the place to its right",
                subject=SubjectArea.MATHEMATICS,
                grade_level=GradeLevel.ELEMENTARY,
                standard_code="CCSS.MATH.5.NBT.1",
                learning_objectives=[
                    "Understand place value relationships",
                    "Compare multi-digit numbers",
                    "Round numbers to any place"
                ]
            ),
            CurriculumStandard(
                id="ccss_math_8_ee_1",
                name="Exponents and Scientific Notation",
                description="Know and apply the properties of integer exponents to generate equivalent numerical expressions",
                subject=SubjectArea.MATHEMATICS,
                grade_level=GradeLevel.MIDDLE,
                standard_code="CCSS.MATH.8.EE.1",
                learning_objectives=[
                    "Apply properties of exponents",
                    "Use scientific notation",
                    "Perform operations with scientific notation"
                ]
            )
        ]
        
        for standard in math_standards:
            standards[standard.id] = standard
        
        return standards
    
    def _load_knowledge_items(self):
        """Load existing knowledge items from storage."""
        knowledge_file = self.knowledge_base_path / "knowledge_items.json"
        if knowledge_file.exists():
            try:
                with open(knowledge_file, 'r') as f:
                    data = json.load(f)
                    for item_data in data:
                        item = KnowledgeItem(
                            id=item_data['id'],
                            title=item_data['title'],
                            content=item_data['content'],
                            subject=SubjectArea(item_data['subject']),
                            grade_level=GradeLevel(item_data['grade_level']),
                            topics=item_data['topics'],
                            difficulty_level=item_data['difficulty_level'],
                            prerequisites=item_data['prerequisites'],
                            learning_objectives=item_data['learning_objectives'],
                            created_at=datetime.fromisoformat(item_data['created_at']),
                            updated_at=datetime.fromisoformat(item_data['updated_at']),
                            source=item_data['source'],
                            metadata=item_data['metadata']
                        )
                        self.knowledge_items[item.id] = item
            except Exception as e:
                logger.error(f"Error loading knowledge items: {str(e)}")
    
    def _save_knowledge_items(self):
        """Save knowledge items to storage."""
        knowledge_file = self.knowledge_base_path / "knowledge_items.json"
        try:
            data = []
            for item in self.knowledge_items.values():
                item_dict = asdict(item)
                item_dict['subject'] = item.subject.value
                item_dict['grade_level'] = item.grade_level.value
                item_dict['created_at'] = item.created_at.isoformat()
                item_dict['updated_at'] = item.updated_at.isoformat()
                data.append(item_dict)
            
            with open(knowledge_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving knowledge items: {str(e)}")
    
    async def add_knowledge_item(
        self,
        title: str,
        content: str,
        subject: SubjectArea,
        grade_level: GradeLevel,
        topics: List[str],
        difficulty_level: int = 5,
        prerequisites: Optional[List[str]] = None,
        learning_objectives: Optional[List[str]] = None,
        source: str = "manual",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new knowledge item to the knowledge base.
        
        Returns:
            The ID of the created knowledge item
        """
        try:
            item_id = f"kb_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.knowledge_items)}"
            
            knowledge_item = KnowledgeItem(
                id=item_id,
                title=title,
                content=content,
                subject=subject,
                grade_level=grade_level,
                topics=topics or [],
                difficulty_level=max(1, min(10, difficulty_level)),
                prerequisites=prerequisites or [],
                learning_objectives=learning_objectives or [],
                created_at=datetime.now(),
                updated_at=datetime.now(),
                source=source,
                metadata=metadata or {}
            )
            
            # Store in local knowledge base
            self.knowledge_items[item_id] = knowledge_item
            
            # Add to RAG system
            rag_metadata = {
                'knowledge_item_id': item_id,
                'title': title,
                'subject': subject.value,
                'grade_level': grade_level.value,
                'topics': topics,
                'difficulty_level': difficulty_level,
                'source': source,
                'content_type': 'knowledge_base'
            }
            
            await self.rag_system.add_document(
                document_id=item_id,
                content=f"Title: {title}\n\nContent: {content}",
                metadata=rag_metadata,
                subject=self._map_subject_to_collection(subject)
            )
            
            # Save to persistent storage
            self._save_knowledge_items()
            
            logger.info(f"Added knowledge item: {title} ({item_id})")
            return item_id
            
        except Exception as e:
            logger.error(f"Error adding knowledge item: {str(e)}")
            raise ValueError(f"Failed to add knowledge item: {str(e)}")
    
    def _map_subject_to_collection(self, subject: SubjectArea) -> str:
        """Map SubjectArea enum to RAG collection name."""
        mapping = {
            SubjectArea.MATHEMATICS: 'math',
            SubjectArea.SCIENCE: 'science',
            SubjectArea.LANGUAGE_ARTS: 'language',
            SubjectArea.HISTORY: 'history',
            SubjectArea.GENERAL: 'general'
        }
        return mapping.get(subject, 'general')
    
    async def search_knowledge_base(
        self,
        query: str,
        subject: Optional[SubjectArea] = None,
        grade_level: Optional[GradeLevel] = None,
        topics: Optional[List[str]] = None,
        difficulty_range: Optional[tuple] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base with subject-specific filters.
        
        Args:
            query: Search query
            subject: Optional subject filter
            grade_level: Optional grade level filter
            topics: Optional topics filter
            difficulty_range: Optional difficulty level range (min, max)
            limit: Maximum number of results
            
        Returns:
            List of matching knowledge items with relevance scores
        """
        try:
            # Search in RAG system
            rag_subject = self._map_subject_to_collection(subject) if subject else None
            
            search_results = await self.rag_system.search(
                query=query,
                subject=rag_subject,
                limit=limit * 2,  # Get more results for filtering
                similarity_threshold=0.6
            )
            
            # Filter results based on criteria
            filtered_results = []
            
            for result in search_results:
                metadata = result.get('metadata', {})
                
                # Apply filters
                if subject and metadata.get('subject') != subject.value:
                    continue
                
                if grade_level and metadata.get('grade_level') != grade_level.value:
                    continue
                
                if topics:
                    item_topics = metadata.get('topics', [])
                    if not any(topic in item_topics for topic in topics):
                        continue
                
                if difficulty_range:
                    item_difficulty = metadata.get('difficulty_level', 5)
                    if not (difficulty_range[0] <= item_difficulty <= difficulty_range[1]):
                        continue
                
                # Add knowledge base specific information
                knowledge_item_id = metadata.get('knowledge_item_id')
                if knowledge_item_id and knowledge_item_id in self.knowledge_items:
                    kb_item = self.knowledge_items[knowledge_item_id]
                    result['knowledge_item'] = {
                        'id': kb_item.id,
                        'title': kb_item.title,
                        'subject': kb_item.subject.value,
                        'grade_level': kb_item.grade_level.value,
                        'topics': kb_item.topics,
                        'difficulty_level': kb_item.difficulty_level,
                        'learning_objectives': kb_item.learning_objectives,
                        'prerequisites': kb_item.prerequisites
                    }
                
                filtered_results.append(result)
                
                if len(filtered_results) >= limit:
                    break
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return []
    
    async def get_curriculum_aligned_content(
        self,
        standard_id: str,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get content aligned with specific curriculum standards.
        
        Args:
            standard_id: Curriculum standard identifier
            query: Optional additional search query
            
        Returns:
            List of aligned content items
        """
        try:
            if standard_id not in self.curriculum_standards:
                raise ValueError(f"Unknown curriculum standard: {standard_id}")
            
            standard = self.curriculum_standards[standard_id]
            
            # Build search query from learning objectives
            search_terms = []
            if query:
                search_terms.append(query)
            
            search_terms.extend(standard.learning_objectives)
            combined_query = " ".join(search_terms)
            
            # Search for aligned content
            results = await self.search_knowledge_base(
                query=combined_query,
                subject=standard.subject,
                grade_level=standard.grade_level,
                limit=15
            )
            
            # Add curriculum alignment information
            for result in results:
                result['curriculum_alignment'] = {
                    'standard_id': standard.id,
                    'standard_name': standard.name,
                    'standard_code': standard.standard_code,
                    'alignment_score': result['similarity_score']
                }
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting curriculum aligned content: {str(e)}")
            return []
    
    def get_subject_taxonomy(self, subject: SubjectArea, grade_level: GradeLevel) -> Dict[str, List[str]]:
        """Get the topic taxonomy for a specific subject and grade level."""
        grade_key = grade_level.value
        if grade_level == GradeLevel.COLLEGE:
            grade_key = "high"  # Use high school taxonomy for college
        
        return self.subject_taxonomies.get(subject, {}).get(grade_key, {})
    
    def get_learning_path(
        self,
        subject: SubjectArea,
        grade_level: GradeLevel,
        current_topic: str,
        target_topic: str
    ) -> List[str]:
        """
        Generate a learning path from current topic to target topic.
        
        Returns:
            List of topics in recommended learning order
        """
        try:
            taxonomy = self.get_subject_taxonomy(subject, grade_level)
            
            # Simple implementation - in practice, this would use more sophisticated
            # dependency analysis and prerequisite mapping
            all_topics = []
            for category, topics in taxonomy.items():
                all_topics.extend(topics)
            
            if current_topic not in all_topics or target_topic not in all_topics:
                return [target_topic]  # Fallback to direct target
            
            current_index = all_topics.index(current_topic)
            target_index = all_topics.index(target_topic)
            
            if current_index < target_index:
                return all_topics[current_index:target_index + 1]
            else:
                return [target_topic]  # Already past the target
            
        except Exception as e:
            logger.error(f"Error generating learning path: {str(e)}")
            return [target_topic]
    
    async def get_knowledge_base_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        try:
            stats = {
                'total_items': len(self.knowledge_items),
                'by_subject': {},
                'by_grade_level': {},
                'by_difficulty': {},
                'rag_stats': await self.rag_system.get_collection_stats()
            }
            
            # Count by subject
            for item in self.knowledge_items.values():
                subject = item.subject.value
                stats['by_subject'][subject] = stats['by_subject'].get(subject, 0) + 1
            
            # Count by grade level
            for item in self.knowledge_items.values():
                grade = item.grade_level.value
                stats['by_grade_level'][grade] = stats['by_grade_level'].get(grade, 0) + 1
            
            # Count by difficulty
            for item in self.knowledge_items.values():
                difficulty = item.difficulty_level
                stats['by_difficulty'][difficulty] = stats['by_difficulty'].get(difficulty, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting knowledge base stats: {str(e)}")
            return {'error': str(e)}
    
    async def update_knowledge_item(
        self,
        item_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update an existing knowledge item."""
        try:
            if item_id not in self.knowledge_items:
                return False
            
            item = self.knowledge_items[item_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(item, field):
                    setattr(item, field, value)
            
            item.updated_at = datetime.now()
            
            # Update in RAG system
            rag_metadata = {
                'knowledge_item_id': item_id,
                'title': item.title,
                'subject': item.subject.value,
                'grade_level': item.grade_level.value,
                'topics': item.topics,
                'difficulty_level': item.difficulty_level,
                'source': item.source,
                'content_type': 'knowledge_base'
            }
            
            await self.rag_system.update_document_metadata(
                document_id=item_id,
                metadata_updates=rag_metadata
            )
            
            # Save to storage
            self._save_knowledge_items()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating knowledge item {item_id}: {str(e)}")
            return False
    
    async def delete_knowledge_item(self, item_id: str) -> bool:
        """Delete a knowledge item from the knowledge base."""
        try:
            if item_id not in self.knowledge_items:
                return False
            
            # Remove from local storage
            del self.knowledge_items[item_id]
            
            # Remove from RAG system
            await self.rag_system.delete_document(document_id=item_id)
            
            # Save to storage
            self._save_knowledge_items()
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting knowledge item {item_id}: {str(e)}")
            return False