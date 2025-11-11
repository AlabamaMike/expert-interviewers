"""
Advanced NLU (Natural Language Understanding) Module
Provides enhanced entity extraction, emotion detection, and topic modeling
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
from .llm_provider import LLMProvider

logger = logging.getLogger(__name__)


class EmotionType(str, Enum):
    """Detailed emotion types beyond basic sentiment"""
    JOY = "joy"
    TRUST = "trust"
    FEAR = "fear"
    SURPRISE = "surprise"
    SADNESS = "sadness"
    DISGUST = "disgust"
    ANGER = "anger"
    ANTICIPATION = "anticipation"
    ENTHUSIASM = "enthusiasm"
    FRUSTRATION = "frustration"
    CONFUSION = "confusion"
    SATISFACTION = "satisfaction"
    DISAPPOINTMENT = "disappointment"


class EntityType(str, Enum):
    """Entity types for extraction"""
    PRODUCT = "product"
    FEATURE = "feature"
    COMPETITOR = "competitor"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    TIME = "time"
    MONETARY = "monetary"
    PAIN_POINT = "pain_point"
    BENEFIT = "benefit"
    USE_CASE = "use_case"


@dataclass
class Entity:
    """Extracted entity from text"""
    text: str
    type: EntityType
    confidence: float
    context: str
    start_position: int
    end_position: int
    normalized_value: Optional[str] = None
    related_entities: List[str] = None

    def __post_init__(self):
        if self.related_entities is None:
            self.related_entities = []


@dataclass
class EmotionDetection:
    """Detected emotion in text"""
    primary_emotion: EmotionType
    secondary_emotions: List[EmotionType]
    intensity: float  # 0.0 to 1.0
    confidence: float
    triggers: List[str]  # What triggered this emotion
    text_evidence: List[str]  # Phrases that indicate this emotion


@dataclass
class Topic:
    """Identified topic in text"""
    name: str
    keywords: List[str]
    relevance_score: float
    sentiment: str  # positive, negative, neutral
    related_topics: List[str]


@dataclass
class IntentClassification:
    """Classified intent of respondent's answer"""
    primary_intent: str
    confidence: float
    sub_intents: List[str]
    is_complete_answer: bool
    requires_elaboration: bool


@dataclass
class NLUAnalysis:
    """Comprehensive NLU analysis result"""
    entities: List[Entity]
    emotions: EmotionDetection
    topics: List[Topic]
    intent: IntentClassification
    key_concepts: List[str]
    semantic_complexity: float  # 0.0 to 1.0
    information_structure: str  # narrative, factual, comparative, etc.
    discourse_markers: List[str]  # however, therefore, additionally, etc.


class AdvancedNLU:
    """Advanced NLU capabilities for interview analysis"""

    def __init__(self, llm_provider: LLMProvider):
        """
        Initialize Advanced NLU

        Args:
            llm_provider: LLM provider for analysis
        """
        self.llm = llm_provider
        logger.info("Initialized AdvancedNLU")

    async def analyze(
        self,
        text: str,
        question_context: Optional[str] = None,
        research_domain: Optional[str] = None
    ) -> NLUAnalysis:
        """
        Perform comprehensive NLU analysis

        Args:
            text: Text to analyze (typically a response)
            question_context: The question that prompted this response
            research_domain: Domain context (product, healthcare, finance, etc.)

        Returns:
            NLUAnalysis with all extracted information
        """
        try:
            # Perform all NLU tasks in parallel for efficiency
            entities_task = self.extract_entities(text, research_domain)
            emotions_task = self.detect_emotions(text)
            topics_task = self.extract_topics(text, question_context)
            intent_task = self.classify_intent(text, question_context)

            # Wait for all tasks
            entities = await entities_task
            emotions = await emotions_task
            topics = await topics_task
            intent = await intent_task

            # Extract additional features
            key_concepts = await self._extract_key_concepts(text)
            complexity = self._calculate_semantic_complexity(text)
            structure = await self._identify_information_structure(text)
            discourse = self._extract_discourse_markers(text)

            return NLUAnalysis(
                entities=entities,
                emotions=emotions,
                topics=topics,
                intent=intent,
                key_concepts=key_concepts,
                semantic_complexity=complexity,
                information_structure=structure,
                discourse_markers=discourse
            )

        except Exception as e:
            logger.error(f"Error in NLU analysis: {e}")
            # Return minimal analysis on error
            return NLUAnalysis(
                entities=[],
                emotions=EmotionDetection(
                    primary_emotion=EmotionType.TRUST,
                    secondary_emotions=[],
                    intensity=0.0,
                    confidence=0.0,
                    triggers=[],
                    text_evidence=[]
                ),
                topics=[],
                intent=IntentClassification(
                    primary_intent="unknown",
                    confidence=0.0,
                    sub_intents=[],
                    is_complete_answer=False,
                    requires_elaboration=True
                ),
                key_concepts=[],
                semantic_complexity=0.5,
                information_structure="unknown",
                discourse_markers=[]
            )

    async def extract_entities(
        self,
        text: str,
        domain: Optional[str] = None
    ) -> List[Entity]:
        """
        Extract named entities and domain-specific entities

        Args:
            text: Text to analyze
            domain: Research domain for context

        Returns:
            List of extracted entities
        """
        try:
            prompt = f"""Extract all relevant entities from this text:

Text: "{text}"
"""
            if domain:
                prompt += f"\nDomain Context: {domain}\n"

            prompt += """
Identify and extract:
1. Products and features mentioned
2. Competitors or alternatives
3. People, organizations, locations
4. Pain points explicitly stated
5. Benefits or advantages mentioned
6. Use cases described
7. Monetary values or time references

For each entity provide:
- The exact text span
- Entity type
- Confidence (0.0-1.0)
- Context (surrounding text)
- Position in text (approximate)
- Normalized value if applicable
"""

            schema = {
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["product", "feature", "competitor", "person",
                                           "organization", "location", "time", "monetary",
                                           "pain_point", "benefit", "use_case"]
                                },
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "context": {"type": "string"},
                                "normalized_value": {"type": "string"}
                            },
                            "required": ["text", "type", "confidence", "context"]
                        }
                    }
                },
                "required": ["entities"]
            }

            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert at extracting structured information from text."
            )

            entities = []
            for i, ent in enumerate(result.get("entities", [])):
                # Find position in text (approximate)
                start_pos = text.lower().find(ent["text"].lower())
                end_pos = start_pos + len(ent["text"]) if start_pos >= 0 else 0

                entities.append(Entity(
                    text=ent["text"],
                    type=EntityType(ent["type"]),
                    confidence=ent["confidence"],
                    context=ent["context"],
                    start_position=start_pos,
                    end_position=end_pos,
                    normalized_value=ent.get("normalized_value")
                ))

            logger.info(f"Extracted {len(entities)} entities")
            return entities

        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []

    async def detect_emotions(self, text: str) -> EmotionDetection:
        """
        Detect detailed emotions in text

        Args:
            text: Text to analyze

        Returns:
            EmotionDetection with detailed emotion analysis
        """
        try:
            prompt = f"""Analyze the emotions expressed in this text:

Text: "{text}"

Identify:
1. Primary emotion (strongest emotion expressed)
2. Secondary emotions (other emotions present)
3. Intensity of primary emotion (0.0-1.0)
4. What triggered these emotions
5. Specific phrases that indicate emotions

Emotion types to consider: joy, trust, fear, surprise, sadness, disgust, anger,
anticipation, enthusiasm, frustration, confusion, satisfaction, disappointment
"""

            schema = {
                "type": "object",
                "properties": {
                    "primary_emotion": {
                        "type": "string",
                        "enum": ["joy", "trust", "fear", "surprise", "sadness", "disgust",
                               "anger", "anticipation", "enthusiasm", "frustration",
                               "confusion", "satisfaction", "disappointment"]
                    },
                    "secondary_emotions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["joy", "trust", "fear", "surprise", "sadness", "disgust",
                                   "anger", "anticipation", "enthusiasm", "frustration",
                                   "confusion", "satisfaction", "disappointment"]
                        }
                    },
                    "intensity": {"type": "number", "minimum": 0, "maximum": 1},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "triggers": {"type": "array", "items": {"type": "string"}},
                    "text_evidence": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["primary_emotion", "intensity", "confidence"]
            }

            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert at detecting emotions in text."
            )

            return EmotionDetection(
                primary_emotion=EmotionType(result["primary_emotion"]),
                secondary_emotions=[EmotionType(e) for e in result.get("secondary_emotions", [])],
                intensity=result["intensity"],
                confidence=result["confidence"],
                triggers=result.get("triggers", []),
                text_evidence=result.get("text_evidence", [])
            )

        except Exception as e:
            logger.error(f"Error detecting emotions: {e}")
            return EmotionDetection(
                primary_emotion=EmotionType.TRUST,
                secondary_emotions=[],
                intensity=0.0,
                confidence=0.0,
                triggers=[],
                text_evidence=[]
            )

    async def extract_topics(
        self,
        text: str,
        question_context: Optional[str] = None
    ) -> List[Topic]:
        """
        Extract topics from text

        Args:
            text: Text to analyze
            question_context: Question that prompted this response

        Returns:
            List of identified topics
        """
        try:
            prompt = f"""Identify the main topics discussed in this text:

Text: "{text}"
"""
            if question_context:
                prompt += f"\nQuestion Context: {question_context}\n"

            prompt += """
For each topic provide:
- Topic name
- Keywords associated with it
- Relevance score (0.0-1.0)
- Sentiment about this topic (positive/negative/neutral)
- Related topics
"""

            schema = {
                "type": "object",
                "properties": {
                    "topics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "keywords": {"type": "array", "items": {"type": "string"}},
                                "relevance_score": {"type": "number", "minimum": 0, "maximum": 1},
                                "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                                "related_topics": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["name", "relevance_score", "sentiment"]
                        }
                    }
                },
                "required": ["topics"]
            }

            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert at identifying topics in text."
            )

            return [
                Topic(
                    name=t["name"],
                    keywords=t.get("keywords", []),
                    relevance_score=t["relevance_score"],
                    sentiment=t["sentiment"],
                    related_topics=t.get("related_topics", [])
                )
                for t in result.get("topics", [])
            ]

        except Exception as e:
            logger.error(f"Error extracting topics: {e}")
            return []

    async def classify_intent(
        self,
        text: str,
        question_context: Optional[str] = None
    ) -> IntentClassification:
        """
        Classify the intent of the response

        Args:
            text: Text to analyze
            question_context: Question that prompted this response

        Returns:
            IntentClassification with intent analysis
        """
        try:
            prompt = f"""Classify the intent of this response:

Response: "{text}"
"""
            if question_context:
                prompt += f"\nQuestion: {question_context}\n"

            prompt += """
Determine:
1. Primary intent (e.g., answer, deflect, elaborate, complain, praise, compare, etc.)
2. Confidence in classification (0.0-1.0)
3. Sub-intents (supporting intents)
4. Is this a complete answer to the question?
5. Does this require elaboration or follow-up?
"""

            schema = {
                "type": "object",
                "properties": {
                    "primary_intent": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "sub_intents": {"type": "array", "items": {"type": "string"}},
                    "is_complete_answer": {"type": "boolean"},
                    "requires_elaboration": {"type": "boolean"}
                },
                "required": ["primary_intent", "confidence", "is_complete_answer", "requires_elaboration"]
            }

            result = await self.llm.generate_structured(
                prompt=prompt,
                output_schema=schema,
                system_prompt="You are an expert at understanding user intent in conversations."
            )

            return IntentClassification(
                primary_intent=result["primary_intent"],
                confidence=result["confidence"],
                sub_intents=result.get("sub_intents", []),
                is_complete_answer=result["is_complete_answer"],
                requires_elaboration=result["requires_elaboration"]
            )

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return IntentClassification(
                primary_intent="unknown",
                confidence=0.0,
                sub_intents=[],
                is_complete_answer=False,
                requires_elaboration=True
            )

    async def _extract_key_concepts(self, text: str) -> List[str]:
        """Extract key concepts from text"""
        try:
            prompt = f"""Extract the key concepts from this text:

Text: "{text}"

List the most important concepts, ideas, or themes (as single words or short phrases).
"""

            result = await self.llm.generate(
                prompt=prompt,
                system_prompt="Extract key concepts concisely.",
                max_tokens=200
            )

            # Parse concepts from response
            concepts = [c.strip() for c in result.content.strip().split('\n') if c.strip()]
            # Remove bullet points and numbers
            concepts = [c.lstrip('•-*0123456789. ') for c in concepts]
            return concepts[:10]  # Limit to top 10

        except Exception as e:
            logger.error(f"Error extracting key concepts: {e}")
            return []

    def _calculate_semantic_complexity(self, text: str) -> float:
        """
        Calculate semantic complexity of text

        Simple heuristic based on:
        - Sentence length variety
        - Vocabulary richness
        - Clause complexity
        """
        if not text:
            return 0.0

        # Simple heuristics
        words = text.split()
        sentences = [s for s in text.split('.') if s.strip()]

        if not sentences:
            return 0.3

        avg_sentence_length = len(words) / len(sentences)
        unique_word_ratio = len(set(words)) / len(words) if words else 0

        # Normalize to 0-1 scale
        complexity = min(1.0, (avg_sentence_length / 20.0 + unique_word_ratio) / 2)

        return complexity

    async def _identify_information_structure(self, text: str) -> str:
        """Identify the structure of information presentation"""
        try:
            prompt = f"""Identify how this text is structured:

Text: "{text}"

Choose the best structure type:
- narrative (telling a story)
- factual (stating facts)
- comparative (comparing options)
- argumentative (making an argument)
- descriptive (describing something)
- procedural (explaining a process)
"""

            result = await self.llm.generate(
                prompt=prompt,
                system_prompt="Identify structure type in one word.",
                max_tokens=10
            )

            structure = result.content.strip().lower()
            valid_structures = ["narrative", "factual", "comparative", "argumentative", "descriptive", "procedural"]

            for vs in valid_structures:
                if vs in structure:
                    return vs

            return "mixed"

        except Exception as e:
            logger.error(f"Error identifying structure: {e}")
            return "unknown"

    def _extract_discourse_markers(self, text: str) -> List[str]:
        """Extract discourse markers from text"""
        markers = [
            "however", "therefore", "moreover", "furthermore", "additionally",
            "in contrast", "on the other hand", "for example", "for instance",
            "consequently", "as a result", "in fact", "actually", "basically",
            "essentially", "specifically", "particularly", "especially"
        ]

        text_lower = text.lower()
        found_markers = [m for m in markers if m in text_lower]
        return found_markers
