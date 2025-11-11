# Expert Interviewers

**Autonomous Voice Agents for Structured Primary Research Interviews**

Expert Interviewers is an advanced system that conducts high-quality research interviews autonomously, using voice AI to engage with respondents, adapt to their answers, and extract maximum insight value—all without human interviewer costs.

## 🎯 Core Value Proposition

- **Scalable primary research** without proportional human interviewer costs
- **Consistent methodology** with adaptive intelligence
- **Real-time insight capture** with automated synthesis
- **24/7 availability** across time zones and languages

## 🏗️ System Architecture

The system consists of four main layers:

### 1. Orchestration Layer
- Session management and agent dispatch
- Quality control and monitoring
- Interview workflow orchestration

### 2. Voice Agent Core Engine
- **Speech-to-Text (STT)**: Deepgram integration for real-time transcription
- **Text-to-Speech (TTS)**: ElevenLabs for natural voice synthesis
- **Natural Language Understanding**: Claude API for response analysis
- **Conversation State Management**: Tracks interview progress and context

### 3. Intelligence & Adaptation Layer
- **Call Guide Interpreter**: Executes structured interview scripts
- **Dynamic Follow-up Generator**: Creates contextual probing questions
- **Response Analysis Engine**: Analyzes sentiment, themes, and insight value
- **Insight Extraction Module**: Synthesizes findings from interviews

### 4. Data & Analytics Layer
- Response database with full transcripts
- Real-time analytics and dashboards
- Cross-interview pattern recognition
- Automated report generation

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 13+ (optional, for production)
- Redis 6+ (optional, for production)

### Installation

```bash
# Clone the repository
git clone https://github.com/AlabamaMike/expert-interviewers.git
cd expert-interviewers

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Configuration

Edit `.env` file with your credentials:

```bash
# Deepgram for STT
DEEPGRAM_API_KEY=your_key_here

# ElevenLabs for TTS
ELEVENLABS_API_KEY=your_key_here
ELEVENLABS_VOICE_ID=your_voice_id

# Anthropic Claude for intelligence
ANTHROPIC_API_KEY=your_key_here

# Database (optional)
DATABASE_URL=postgresql://user:password@localhost:5432/expert_interviewers

# Redis (optional)
REDIS_URL=redis://localhost:6379/0
```

### Running the API

```bash
# Start the FastAPI server
python -m src.api.main

# Or with uvicorn directly
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 📖 Usage

### 1. Create a Call Guide

A call guide defines the structure and flow of your interview:

```python
import json
from src.models.call_guide import CallGuide

# Load example call guide
with open('examples/product_feedback_guide.json') as f:
    guide_data = json.load(f)

call_guide = CallGuide(**guide_data)
```

Or via API:

```bash
curl -X POST http://localhost:8000/api/call-guides/ \
  -H "Content-Type: application/json" \
  -d @examples/product_feedback_guide.json
```

### 2. Schedule an Interview

```bash
curl -X POST http://localhost:8000/api/interviews/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "call_guide_id": "guide-uuid-here",
    "respondent_phone": "+1234567890",
    "respondent_name": "John Doe",
    "respondent_email": "john@example.com"
  }'
```

### 3. Conduct Interview Programmatically

```python
from src.orchestration.interview_orchestrator import InterviewOrchestrator
from src.voice_engine.stt import create_stt_provider
from src.voice_engine.tts import create_tts_provider
from src.intelligence.llm_provider import create_llm_provider
from src.config import settings

# Initialize components
stt = create_stt_provider("deepgram", api_key=settings.deepgram_api_key)
tts = create_tts_provider("elevenlabs", api_key=settings.elevenlabs_api_key,
                         voice_id=settings.elevenlabs_voice_id)
llm = create_llm_provider("claude", api_key=settings.anthropic_api_key)

# Create orchestrator
orchestrator = InterviewOrchestrator(stt, tts, llm)

# Conduct interview
completed_interview = await orchestrator.conduct_interview(
    call_guide=call_guide,
    interview=interview,
    audio_stream_handler=audio_handler
)
```

### 4. Extract Insights

```python
from src.intelligence.insight_extractor import InsightExtractor

extractor = InsightExtractor(llm)

# Extract insights from single interview
insights = await extractor.extract_interview_insights(
    interview=completed_interview,
    research_objective=call_guide.research_objective
)

# Cross-interview synthesis
multi_insights = await extractor.synthesize_cross_interview_insights(
    interviews=[interview1, interview2, interview3],
    research_objective="Overall research goal"
)
```

## 📋 Example Call Guides

The `examples/` directory contains ready-to-use call guides:

- **product_feedback_guide.json**: Understand user pain points and satisfaction
- **customer_discovery_guide.json**: Validate problem-solution fit for new products

## 🔑 Key Features

### Adaptive Conversation

The system dynamically adapts to respondent answers:

- **Vague Response** → "Can you give me a specific example?"
- **Emotional Signal** → "That sounds challenging, tell me more..."
- **Contradiction** → "Earlier you mentioned X, how does that relate?"
- **High-Value Topic** → "This is interesting, what led to that?"

### Intelligent Follow-ups

Automatically generates contextual follow-up questions:

1. Detects incomplete or surface-level responses
2. Identifies contradictions requiring clarification
3. Recognizes emotional cues suggesting deeper insights
4. Generates contextual probes based on response analysis

### Quality Control

- Completion rate tracking
- Engagement score calculation
- Response quality metrics
- Automatic escalation for human review when needed

### Compliance Built-in

- Automated consent collection
- GDPR/CCPA compliance
- Call recording with permission
- Data retention policies

## 🛠️ Development

### Project Structure

```
expert-interviewers/
├── src/
│   ├── api/                    # FastAPI application
│   │   ├── main.py
│   │   └── routers/
│   ├── models/                 # Pydantic data models
│   │   ├── call_guide.py
│   │   ├── interview.py
│   │   └── analytics.py
│   ├── voice_engine/           # STT/TTS integration
│   │   ├── stt.py
│   │   └── tts.py
│   ├── intelligence/           # LLM-powered analysis
│   │   ├── llm_provider.py
│   │   ├── response_analyzer.py
│   │   ├── follow_up_generator.py
│   │   └── insight_extractor.py
│   ├── orchestration/          # Interview management
│   │   ├── interview_orchestrator.py
│   │   └── conversation_state.py
│   └── config.py               # Configuration management
├── examples/                   # Example call guides
├── tests/                      # Test suite
├── docs/                       # Documentation
├── requirements.txt
└── README.md
```

### Running Tests

```bash
pytest tests/ -v --cov=src
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
flake8 src/ tests/

# Type checking
mypy src/
```

## 📊 Performance Targets

### Technical KPIs
- Call setup latency: <2 seconds
- STT accuracy: >95%
- Response latency: <500ms
- System uptime: 99.9%

### Research Quality KPIs
- Interview completion: >80%
- Insight density: >5 key findings per 30-min call
- Respondent satisfaction: >4.0/5.0
- Follow-up effectiveness: >60% yielding deeper insights

## 🗺️ Roadmap

### Phase 1: MVP ✅
- [x] Basic call guide execution
- [x] Simple follow-up rules
- [x] Core voice infrastructure
- [x] Basic reporting

### Phase 2: Intelligence Layer (In Progress)
- [ ] Dynamic follow-up generation
- [ ] Advanced NLU integration
- [ ] Cross-interview analysis
- [ ] Quality monitoring dashboard

### Phase 3: Scale & Optimize
- [ ] Multi-language support
- [ ] Self-improvement features
- [ ] Advanced analytics
- [ ] Enterprise integrations

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License

## 🙏 Acknowledgments

Built with:
- [Anthropic Claude](https://www.anthropic.com/) - LLM for intelligence
- [Deepgram](https://deepgram.com/) - Speech-to-Text
- [ElevenLabs](https://elevenlabs.io/) - Text-to-Speech
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/AlabamaMike/expert-interviewers/issues)

---

**Built to scale qualitative research with AI** 🚀
