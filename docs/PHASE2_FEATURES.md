# Phase 2 Features - Intelligence Layer Enhancements

## Overview

Phase 2 introduces advanced intelligence capabilities to the Expert Interviewers system, focusing on dynamic follow-up generation, advanced NLU integration, cross-interview analysis, and quality monitoring.

## New Features

### 1. Advanced NLU (Natural Language Understanding)

**Module:** `src/intelligence/advanced_nlu.py`

Enhanced natural language understanding capabilities beyond basic sentiment analysis:

#### Features

- **Entity Extraction**: Identifies and extracts key entities from responses
  - Products, features, competitors
  - People, organizations, locations
  - Pain points and benefits
  - Use cases and monetary values

- **Emotion Detection**: Detailed emotion analysis beyond basic sentiment
  - 13 emotion types: joy, trust, fear, surprise, sadness, disgust, anger, anticipation, enthusiasm, frustration, confusion, satisfaction, disappointment
  - Intensity scoring (0.0-1.0)
  - Emotion trigger identification
  - Text evidence extraction

- **Topic Modeling**: Automatic topic identification
  - Keywords and relevance scoring
  - Topic-specific sentiment
  - Related topic mapping

- **Intent Classification**: Understanding respondent intent
  - Primary and sub-intents
  - Completeness assessment
  - Elaboration requirements

- **Semantic Analysis**:
  - Key concept extraction
  - Semantic complexity scoring
  - Information structure identification (narrative, factual, comparative, etc.)
  - Discourse marker extraction

#### Usage Example

```python
from src.intelligence.advanced_nlu import AdvancedNLU
from src.intelligence.llm_provider import create_llm_provider

llm = create_llm_provider("claude", api_key="your_key")
nlu = AdvancedNLU(llm)

# Analyze a response
analysis = await nlu.analyze(
    text="I really love the new feature, but the pricing is too high...",
    question_context="What do you think about our product?",
    research_domain="product_feedback"
)

# Access results
print(f"Primary emotion: {analysis.emotions.primary_emotion}")
print(f"Entities found: {len(analysis.entities)}")
print(f"Topics: {[t.name for t in analysis.topics]}")
```

### 2. Enhanced Cross-Interview Analysis

**Module:** `src/intelligence/cross_interview_analyzer.py`

Sophisticated analysis across multiple interviews with statistical pattern detection:

#### Features

- **Pattern Detection**:
  - Universal patterns (appearing across most interviews)
  - Segment-specific patterns
  - Outlier detection
  - Temporal trends

- **Segment Analysis**:
  - Compare different respondent segments
  - Statistical significance testing
  - Metric comparisons with confidence intervals

- **Trend Analysis**:
  - Time-series analysis for metrics
  - Trend direction and rate of change
  - Confidence scoring

- **Executive Summaries**:
  - AI-generated comprehensive summaries
  - Key findings synthesis
  - Actionable recommendations

#### Usage Example

```python
from src.intelligence.cross_interview_analyzer import CrossInterviewAnalyzer

analyzer = CrossInterviewAnalyzer(llm)

# Detect patterns across interviews
patterns = await analyzer.analyze_patterns(
    interviews=interview_list,
    research_objective="Understand user pain points",
    min_pattern_frequency=0.3
)

# Compare segments
comparison = await analyzer.compare_segments(
    segment_a_interviews=power_users,
    segment_b_interviews=casual_users,
    segment_a_name="Power Users",
    segment_b_name="Casual Users"
)

# Analyze trends
trend = await analyzer.analyze_trends(
    interviews=interview_list,
    metric_name="engagement",
    time_window="weekly"
)

# Generate executive summary
summary = await analyzer.generate_executive_summary(
    interviews=interview_list,
    research_objective="Product-market fit validation"
)
```

### 3. Quality Monitoring System

**Module:** `src/monitoring/quality_monitor.py`

Real-time quality monitoring with alerting and metrics tracking:

#### Features

- **Real-time Metrics Tracking**:
  - Engagement score
  - Completion rate
  - Response quality
  - STT accuracy
  - Response latency
  - Error rates

- **Configurable Thresholds**:
  - Warning, error, and critical levels
  - Metric-specific thresholds
  - Window-based evaluation

- **Alert System**:
  - Severity levels (info, warning, error, critical)
  - Alert acknowledgment and resolution
  - Alert history tracking
  - Custom alert callbacks

- **Quality Reports**:
  - Overall health status
  - Health score calculation
  - Trend identification
  - Issue detection
  - Automated recommendations

#### Usage Example

```python
from src.monitoring.quality_monitor import QualityMonitor, QualityThreshold

# Create monitor with custom thresholds
thresholds = [
    QualityThreshold(
        metric_name="engagement_score",
        warning_threshold=0.5,
        error_threshold=0.3,
        critical_threshold=0.2,
        comparison="less_than"
    )
]

monitor = QualityMonitor(
    thresholds=thresholds,
    alert_callback=handle_alert
)

# Track interview progress
await monitor.track_interview_start(interview)
await monitor.track_response(interview_id, response, metrics)
await monitor.track_interview_completion(interview)

# Generate report
report = await monitor.generate_report(time_window=timedelta(hours=24))
print(f"Health Score: {report.health_score}")
print(f"Active Alerts: {len(report.active_alerts)}")
```

### 4. Quality Monitoring Dashboard API

**Module:** `src/api/routers/quality_dashboard.py`

RESTful API endpoints for accessing quality metrics:

#### Endpoints

- `GET /api/quality/dashboard` - Get quality dashboard overview
- `GET /api/quality/metrics/{metric_name}` - Get metric history
- `GET /api/quality/metrics` - List available metrics
- `GET /api/quality/alerts` - Get active alerts
- `POST /api/quality/alerts/{alert_id}/acknowledge` - Acknowledge alert
- `POST /api/quality/alerts/{alert_id}/resolve` - Resolve alert
- `GET /api/quality/thresholds` - Get configured thresholds
- `PUT /api/quality/thresholds/{metric_name}` - Update threshold
- `GET /api/quality/health` - Quick health check
- `GET /api/quality/statistics` - Detailed statistics

#### Example API Usage

```bash
# Get dashboard
curl http://localhost:8000/api/quality/dashboard?hours=24

# Get metric history
curl http://localhost:8000/api/quality/metrics/engagement_score?limit=100

# Get active alerts
curl http://localhost:8000/api/quality/alerts?severity=error

# Acknowledge alert
curl -X POST http://localhost:8000/api/quality/alerts/alert-123/acknowledge \
  -H "Content-Type: application/json" \
  -d '{"acknowledged_by": "admin"}'
```

### 5. Follow-up Learning System

**Module:** `src/intelligence/follow_up_learning.py`

Machine learning system that improves follow-up question generation over time:

#### Features

- **Outcome Tracking**:
  - Track follow-up question effectiveness
  - Measure response quality improvement
  - Identify successful patterns

- **Pattern Learning**:
  - Automatically identify successful follow-up patterns
  - Learn trigger conditions for different follow-up types
  - Calculate success rates and confidence scores

- **Smart Suggestions**:
  - Suggest follow-ups based on learned patterns
  - Confidence scoring for suggestions
  - Context-aware generation

- **Continuous Improvement**:
  - Learn from every completed interview
  - Update patterns as more data is collected
  - Export/import learned patterns

- **Effectiveness Reporting**:
  - Track action effectiveness over time
  - Identify top-performing patterns
  - Improvement statistics

#### Usage Example

```python
from src.intelligence.follow_up_learning import FollowUpLearningSystem

learning_system = FollowUpLearningSystem(
    llm_provider=llm,
    min_pattern_samples=5,
    min_success_rate=0.6
)

# Learn from completed interviews
await learning_system.learn_from_interview(completed_interview)

# Get suggestions for follow-ups
suggestion = await learning_system.suggest_follow_up(
    original_response="It's okay, I guess.",
    response_quality=0.3,
    context={"section": "satisfaction", "topic": "product"}
)

if suggestion:
    print(f"Suggested: {suggestion['question']}")
    print(f"Confidence: {suggestion['confidence']:.1%}")

# Get effectiveness report
report = learning_system.get_effectiveness_report()
print(f"Total patterns learned: {report['total_patterns_learned']}")

# Export learned patterns
patterns_json = learning_system.export_patterns()
```

## Integration Guide

### Setting Up Phase 2 Features

1. **Install Dependencies** (if any new dependencies were added):
```bash
pip install -r requirements.txt
```

2. **Initialize Quality Monitoring**:
```python
from src.monitoring.quality_monitor import QualityMonitor

# In your application startup
quality_monitor = QualityMonitor()
app.state.quality_monitor = quality_monitor
```

3. **Enable Advanced NLU**:
```python
from src.intelligence.advanced_nlu import AdvancedNLU
from src.intelligence.llm_provider import create_llm_provider

llm = create_llm_provider("claude", api_key=settings.anthropic_api_key)
nlu = AdvancedNLU(llm)
```

4. **Set Up Follow-up Learning**:
```python
from src.intelligence.follow_up_learning import FollowUpLearningSystem

learning_system = FollowUpLearningSystem(llm)

# Learn from completed interviews automatically
@app.on_event("interview_completed")
async def on_interview_complete(interview):
    await learning_system.learn_from_interview(interview)
```

### Using Phase 2 in Interview Orchestration

Update your `InterviewOrchestrator` to use new capabilities:

```python
class EnhancedInterviewOrchestrator(InterviewOrchestrator):
    def __init__(self, stt, tts, llm, quality_monitor, nlu, learning_system):
        super().__init__(stt, tts, llm)
        self.quality_monitor = quality_monitor
        self.nlu = nlu
        self.learning_system = learning_system

    async def conduct_interview(self, call_guide, interview, audio_handler):
        # Track interview start
        await self.quality_monitor.track_interview_start(interview)

        # ... existing interview logic ...

        # Use advanced NLU for response analysis
        nlu_analysis = await self.nlu.analyze(
            text=response.response_text,
            question_context=question.text
        )

        # Get learned follow-up suggestions
        suggestion = await self.learning_system.suggest_follow_up(
            original_response=response.response_text,
            response_quality=response_quality,
            context=context
        )

        # Track response quality
        await self.quality_monitor.track_response(
            interview_id=interview.interview_id,
            response=response,
            metrics={"response_quality": response_quality}
        )

        # ... rest of interview logic ...

        # Track completion
        await self.quality_monitor.track_interview_completion(interview)
        await self.learning_system.learn_from_interview(interview)
```

## Performance Considerations

### Advanced NLU
- **Token Usage**: NLU analysis uses LLM tokens. Consider caching for frequently analyzed patterns.
- **Latency**: Add ~200-500ms per response analysis. Use async operations for parallel processing.

### Cross-Interview Analysis
- **Memory**: Large interview datasets may require pagination or batch processing.
- **Processing Time**: Pattern detection on 100+ interviews may take 10-30 seconds.

### Quality Monitoring
- **Storage**: Metric history is kept in memory (deque with max length). Consider persistent storage for long-term tracking.
- **Alert Frequency**: Configure alert callbacks to avoid flooding. Alerts are de-duplicated within 5-minute windows.

### Follow-up Learning
- **Learning Curve**: Requires minimum 5 samples per pattern before suggesting.
- **Pattern Storage**: Export patterns periodically to persist learnings.

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Quality Monitoring
QUALITY_MONITOR_ENABLED=true
QUALITY_ALERT_WEBHOOK=https://your-webhook-url.com/alerts
QUALITY_REPORT_INTERVAL=3600  # seconds

# NLU
NLU_CACHE_ENABLED=true
NLU_CACHE_TTL=86400  # seconds

# Learning System
LEARNING_MIN_SAMPLES=5
LEARNING_MIN_SUCCESS_RATE=0.6
LEARNING_AUTO_EXPORT=true
LEARNING_EXPORT_PATH=./data/learned_patterns.json
```

## Monitoring and Observability

### Key Metrics to Track

1. **NLU Performance**:
   - Entity extraction accuracy
   - Emotion detection confidence
   - Processing time per response

2. **Cross-Interview Analysis**:
   - Pattern detection rate
   - Analysis completion time
   - Pattern confidence scores

3. **Quality Monitoring**:
   - Health score trends
   - Alert frequency by severity
   - Metric threshold violations

4. **Learning System**:
   - Pattern learning rate
   - Follow-up success rate
   - Improvement scores

### Logging

All Phase 2 modules use Python's standard logging:

```python
import logging

# Configure logging level
logging.basicConfig(level=logging.INFO)

# Module-specific loggers
logging.getLogger('src.intelligence.advanced_nlu').setLevel(logging.DEBUG)
logging.getLogger('src.monitoring.quality_monitor').setLevel(logging.WARNING)
```

## Testing Phase 2 Features

### Unit Tests

```bash
# Run tests for new modules
pytest tests/intelligence/test_advanced_nlu.py -v
pytest tests/intelligence/test_cross_interview_analyzer.py -v
pytest tests/monitoring/test_quality_monitor.py -v
pytest tests/intelligence/test_follow_up_learning.py -v
```

### Integration Tests

```python
# Example integration test
async def test_phase2_integration():
    # Set up components
    llm = create_llm_provider("claude", api_key=test_api_key)
    nlu = AdvancedNLU(llm)
    monitor = QualityMonitor()
    learning = FollowUpLearningSystem(llm)

    # Conduct test interview
    interview = await conduct_test_interview()

    # Verify NLU analysis
    nlu_result = await nlu.analyze(interview.responses[0].response_text)
    assert len(nlu_result.entities) > 0

    # Verify quality tracking
    report = await monitor.generate_report()
    assert report.health_score > 0

    # Verify learning
    await learning.learn_from_interview(interview)
    effectiveness = learning.get_effectiveness_report()
    assert effectiveness['total_outcomes_analyzed'] > 0
```

## Migration from Phase 1

Phase 2 is backward compatible with Phase 1. Existing code will continue to work. To adopt Phase 2 features:

1. **Optional Integration**: Phase 2 features are opt-in. You can use them incrementally.
2. **Existing APIs**: All Phase 1 API endpoints remain unchanged.
3. **New Endpoints**: Phase 2 adds new endpoints under `/api/quality/`.

## Best Practices

1. **NLU Analysis**:
   - Use domain context for better entity extraction
   - Cache results for similar responses
   - Monitor token usage

2. **Quality Monitoring**:
   - Start with default thresholds, adjust based on your data
   - Set up alert callbacks for critical issues
   - Review quality reports daily

3. **Cross-Interview Analysis**:
   - Run pattern detection on batches of 20-50 interviews
   - Update patterns weekly
   - Export and backup learned patterns

4. **Follow-up Learning**:
   - Let the system collect data for 2-3 weeks before relying on suggestions
   - Review top patterns monthly
   - Export patterns before system updates

## Troubleshooting

### NLU Analysis is Slow
- Check LLM provider latency
- Enable caching
- Reduce analysis depth for real-time use cases

### Quality Alerts Too Frequent
- Adjust thresholds based on your baseline
- Increase alert de-duplication window
- Review metric calculation logic

### Learning System Not Suggesting Follow-ups
- Ensure minimum sample count is reached (default: 5)
- Check success rate threshold (default: 0.6)
- Review outcome quality calculations

### Cross-Interview Patterns Not Detected
- Increase min_pattern_frequency (try 0.2 instead of 0.3)
- Ensure sufficient interview volume (20+ recommended)
- Check theme extraction consistency

## Support and Feedback

For issues or questions about Phase 2 features:
- GitHub Issues: [Create an issue](https://github.com/AlabamaMike/expert-interviewers/issues)
- Tag with `phase-2` label

## Roadmap

### Phase 2.1 (Planned)
- Web dashboard UI for quality monitoring
- Real-time WebSocket updates for metrics
- Advanced visualization of cross-interview patterns
- ML-based anomaly detection

### Phase 3 (Future)
- Multi-language NLU support
- Video interview analysis
- Predictive quality modeling
- Auto-generated call guides based on learnings
