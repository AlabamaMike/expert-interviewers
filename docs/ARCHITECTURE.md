# System Architecture

## Overview

Expert Interviewers is a sophisticated autonomous voice interview system built on a four-layer architecture designed for scalability, reliability, and adaptability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer                              │
│  • Web Dashboard                                             │
│  • Mobile Apps                                               │
│  • API Clients                                               │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│                  API Gateway (FastAPI)                       │
│  • REST Endpoints                                            │
│  • WebSocket Connections                                     │
│  • Authentication & Authorization                            │
└────────────────────┬────────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────────┐
│             Orchestration Layer                              │
│  • Session Management                                        │
│  • Interview Orchestrator                                    │
│  • Conversation State Manager                                │
│  • Agent Dispatch                                            │
│  • Quality Control Monitor                                   │
└─────────────────────┬───────────────────────────────────────┘
                     │
        ┌────────────┴───────────────┐
        │                            │
┌───────┴─────────┐        ┌────────┴──────────┐
│  Voice Engine   │        │  Intelligence &   │
│                 │        │  Adaptation Layer │
│  • STT Provider │        │                   │
│  • TTS Provider │        │  • LLM Provider   │
│  • Audio Proc.  │        │  • Response       │
│  • Call Manager │        │    Analyzer       │
└───────┬─────────┘        │  • Follow-up      │
        │                  │    Generator      │
        │                  │  • Insight        │
        │                  │    Extractor      │
        │                  └────────┬──────────┘
        │                           │
        └────────────┬──────────────┘
                     │
┌─────────────────────────────────────────────────────────────┐
│              Data & Analytics Layer                          │
│  • PostgreSQL (Interviews, Responses, Transcripts)          │
│  • Redis (Session Cache, Task Queue)                        │
│  • Vector DB (Embeddings, Semantic Search)                  │
│  • Analytics Engine                                          │
│  • Report Generator                                          │
└─────────────────────────────────────────────────────────────┘
                     │
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│  • Deepgram (STT)                                           │
│  • ElevenLabs (TTS)                                         │
│  • Anthropic Claude (LLM)                                   │
│  • Twilio (Voice Infrastructure)                            │
└─────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### 1. Orchestration Layer

**Purpose**: Manages the overall interview lifecycle and coordinates between components.

**Key Components**:

- **SessionManager**: Creates, tracks, and terminates interview sessions
- **InterviewOrchestrator**: Main controller for conducting interviews
  - Implements interview flow logic
  - Coordinates STT, TTS, and LLM components
  - Handles error recovery and escalation
  - Manages time budgets and section transitions

- **ConversationStateManager**: Maintains state for active interviews
  - Tracks current position in call guide
  - Manages follow-up question stack
  - Monitors time budgets
  - Maintains conversation history

**Design Patterns**:
- State Machine for interview phases
- Observer pattern for quality monitoring
- Strategy pattern for adaptive behavior

### 2. Voice Agent Core Engine

**Purpose**: Handles all voice interaction with respondents.

**Key Components**:

- **STT Provider (Speech-to-Text)**:
  - Deepgram integration for real-time transcription
  - Streaming support for low latency
  - 95%+ accuracy target
  - Confidence scoring

- **TTS Provider (Text-to-Speech)**:
  - ElevenLabs for natural voice synthesis
  - Configurable voice profiles
  - Emotional tone adaptation
  - Multi-language support (future)

- **AudioProcessor**:
  - Audio format conversion
  - Noise reduction
  - Volume normalization

- **CallManager**:
  - Twilio integration for telephony
  - WebRTC for browser-based calls
  - Call recording management
  - DTMF handling

**Performance Requirements**:
- STT latency: <500ms
- TTS latency: <1s
- End-to-end response time: <2s

### 3. Intelligence & Adaptation Layer

**Purpose**: Provides AI-powered analysis and adaptive conversation capabilities.

**Key Components**:

- **LLMProvider**:
  - Abstraction over multiple LLM providers (Claude, GPT-4)
  - Structured output generation
  - Token usage tracking
  - Rate limiting and retries

- **ResponseAnalyzer**:
  - Real-time sentiment analysis
  - Theme extraction
  - Information density scoring
  - Signal detection (enthusiasm, hesitation, confusion)
  - Contradiction identification

- **FollowUpGenerator**:
  - Dynamic follow-up question generation
  - Context-aware probing
  - Template-based and LLM-generated follow-ups
  - Priority ranking
  - Trigger rule evaluation

- **InsightExtractor**:
  - Post-interview insight synthesis
  - Cross-interview pattern recognition
  - Quote extraction
  - Theme clustering
  - Executive summary generation

**LLM Usage Strategy**:
- Real-time: Response analysis, follow-up generation (fast, low-token)
- Batch: Deep insight extraction, cross-interview synthesis (high-quality, higher-token)
- Caching: Common analyses, follow-up templates

### 4. Data & Analytics Layer

**Purpose**: Stores, processes, and analyzes interview data.

**Data Stores**:

- **PostgreSQL**:
  - Interviews and metadata
  - Responses and transcripts
  - Call guides
  - Quality metrics
  - User accounts

- **Redis**:
  - Session state cache
  - Celery task queue
  - Rate limiting
  - Real-time analytics cache

- **Vector Database** (Future):
  - Response embeddings
  - Semantic search
  - Similar interview matching

**Analytics Components**:
- Real-time dashboard
- Aggregate metrics calculator
- Trend analyzer
- Report generator
- Export functionality

## Data Flow

### Interview Execution Flow

```
1. Interview Scheduled
   └─> Create Interview record in DB

2. Interview Started
   └─> Initialize ConversationState
   └─> Load CallGuide
   └─> Begin Consent Phase

3. For each Question:
   └─> TTS: Synthesize question → Play audio
   └─> STT: Listen for response → Transcribe
   └─> Store response in DB
   └─> LLM: Analyze response
   └─> If follow-up needed:
       └─> LLM: Generate follow-up
       └─> Ask follow-up (recurse)
   └─> Update ConversationState
   └─> Check time budget

4. Interview Completed
   └─> Calculate metrics
   └─> Store final state
   └─> Trigger insight extraction (async)

5. Post-Processing (Async)
   └─> LLM: Extract insights
   └─> Generate report
   └─> Notify stakeholders
```

### Response Analysis Flow

```
Response Received
  │
  ├─> Sentiment Analysis
  │   └─> Score: -1.0 to 1.0
  │
  ├─> Theme Extraction
  │   └─> Keywords, Topics
  │
  ├─> Information Density
  │   └─> Score: 0.0 to 1.0
  │   └─> Triggers: Vague, Detailed, Surface-level
  │
  ├─> Signal Detection
  │   └─> Enthusiasm, Hesitation, Confusion, Emotional
  │
  └─> Contradiction Check
      └─> Compare with previous responses
      └─> Flag inconsistencies
```

## Scalability Considerations

### Horizontal Scaling

- **API Layer**: Multiple FastAPI instances behind load balancer
- **Orchestrators**: Multiple worker processes via Celery
- **Voice Processing**: Distributed via message queue

### Vertical Scaling

- **Database**: Read replicas for analytics queries
- **Redis**: Cluster mode for high availability
- **LLM**: Request batching and caching

### Performance Optimizations

1. **Caching Strategy**:
   - Call guides cached in Redis
   - Common LLM responses cached
   - Transcription results cached

2. **Async Processing**:
   - Non-blocking voice synthesis
   - Background insight extraction
   - Parallel response analysis

3. **Rate Limiting**:
   - Per-user API rate limits
   - LLM token budget management
   - Concurrent interview limits

## Security & Compliance

### Data Protection

- **Encryption**: TLS 1.3 for all communications
- **At Rest**: Database encryption, encrypted backups
- **PII Handling**: Separate tables, access controls

### Compliance Features

- **GDPR**:
  - Consent tracking
  - Right to deletion
  - Data export
  - Purpose limitation

- **CCPA**:
  - Opt-out mechanisms
  - Data disclosure
  - Deletion rights

### Authentication & Authorization

- JWT-based authentication
- Role-based access control (RBAC)
- API key management
- Audit logging

## Monitoring & Observability

### Metrics

- **Application**: Request rates, latency, error rates
- **Business**: Interview completion rate, quality scores
- **Infrastructure**: CPU, memory, disk, network

### Logging

- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Sensitive data masking

### Alerting

- High error rates
- Interview failures
- Quality degradation
- System resource issues

## Disaster Recovery

### Backup Strategy

- **Database**: Daily full backups, hourly incrementals
- **Audio**: Offsite storage, 90-day retention
- **Configuration**: Version controlled, backed up

### Failover

- Multi-region deployment (future)
- Database replication
- Graceful degradation

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| API | FastAPI | High-performance async API |
| Voice | Deepgram | Speech-to-Text |
| Voice | ElevenLabs | Text-to-Speech |
| Voice | Twilio | Telephony infrastructure |
| Intelligence | Anthropic Claude | LLM for analysis |
| Database | PostgreSQL | Relational data storage |
| Cache | Redis | Session state, queuing |
| Queue | Celery | Async task processing |
| Monitoring | Prometheus | Metrics collection |

## Future Enhancements

### Phase 2
- Multi-language support
- Video interview capability
- Advanced emotion detection
- Self-learning from feedback

### Phase 3
- Real-time translation
- Multi-modal interviews (voice + screen share)
- Predictive analytics
- Auto-generated call guides

---

*Last Updated: 2024*
