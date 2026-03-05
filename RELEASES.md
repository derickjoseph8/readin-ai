# ReadIn AI Release Notes

## v1.6.0 (March 5, 2026)

### Major Release - 12 New Features

This is a major release introducing AI personas, collaboration features, comprehensive integrations, and much more.

#### AI & Intelligence
- **AI Personas**: 10 customizable response styles (Professional, Casual, Technical, Concise, Executive, Sales, Legal, Creative, Supportive, Analytical)
- **Semantic Search**: Find meetings by meaning, not just keywords - powered by embeddings
- **AI-Powered Recommendations**: Predictive meeting insights, next steps suggestions, effectiveness metrics
- **Real-time Translation**: Translate transcripts to 11 languages (EN, ES, FR, DE, PT, ZH, JA, KO, AR, HI, SW)
- **Transcript Editing**: Edit transcriptions with AI-powered correction suggestions

#### Collaboration
- **Shared Notes**: Create and share meeting notes with team members
- **@Mentions**: Tag colleagues in comments with automatic notifications
- **Meeting Handoffs**: Transfer meeting ownership between team members
- **Collaborative Comments**: Thread-based discussions on shared notes

#### Integrations
- **Slack Deep Integration**:
  - Slash commands: `/readin summary`, `/readin meetings`, `/readin action-items`
  - Interactive buttons for completing action items
  - Modal support for adding notes
- **Project Management**:
  - Asana: Sync action items as tasks
  - Notion: Create pages from meetings
  - Jira: Create issues with full ADF support
  - Linear: GraphQL-based issue sync

#### Desktop App
- **Voice Commands**: Wake word detection ("Hey ReadIn") with 7 commands
  - Summarize, repeat, action items, what did they say, stop/start listening, clear
  - Text-to-speech feedback option
- **Privacy Mode**:
  - Excluded apps list management
  - Auto-pause for sensitive apps (banking, medical, password managers)
  - Pause history tracking
- **Offline Mode**:
  - SQLite local storage for meetings, conversations, action items
  - Sync queue with automatic retry when online
  - Conflict resolution strategies

#### Mobile
- **Mobile API Endpoints**: Optimized for React Native
  - `/mobile/dashboard` - Lightweight stats
  - `/mobile/meetings` - Paginated list with filters
  - `/mobile/action-items/{id}/complete` - One-tap complete
  - `/mobile/device/register` - Push notification registration

#### Compliance
- **SOC 2 Reports**: Access controls, audit logging summary
- **HIPAA Checks**: BAA status, compliance checklist
- **CCPA**: Data access requests, deletion requests, opt-out handling
- **Consent Management**: User consent preferences for GDPR/CCPA

### Files Changed
- 41 files modified/created
- 12,181+ lines of code added

### Build Status
- ✅ Windows (x64)
- ✅ macOS (Universal - Intel + Apple Silicon)
- ✅ Linux (x64, AppImage)

---

## v1.5.4 (March 3, 2026)

### Improvements
- **Speaker Diarization**: Now optional with one-click installer
  - Reduces base build size significantly
  - Install via Settings > Features > "Install Speaker Diarization"
  - One-click batch file for Windows
- **Swahili Language Support**: Added Swahili (sw) to supported languages
- **Overlay Feature Tips**: New tooltip in main interface directing to settings
- **Security**: Fixed CI security scan (upgraded sentence-transformers)

### Bug Fixes
- Fixed process kill patterns for proper cleanup
- Fixed email sender domain configuration

---

## v1.5.3 (February 2026)

### Features
- Full system audit and optimization
- Enhanced meeting detection (29 apps supported)
- Improved memory management
- Browser extension updates

### Infrastructure
- GZip compression middleware
- Slow query logging (>500ms)
- Redis caching layer
- Kubernetes health probes

---

## v1.5.0 - v1.5.2 (January-February 2026)

### Core Features
- Real-time transcription with Whisper
- AI-powered meeting summaries
- Action item extraction
- Pre-meeting briefings
- Multi-platform support (Windows, macOS, Linux)

### Integrations
- Google Calendar
- Microsoft Outlook
- Apple Calendar
- HubSpot CRM
- Salesforce CRM
- Slack notifications
- Microsoft Teams notifications

### Security
- JWT authentication
- Two-factor authentication (TOTP)
- WebAuthn/Passkey support
- SSO (Google, Microsoft, Apple, SAML, OIDC)
- Role-based access control

---

## Download Links

### v1.6.0 (Latest)
- [Windows Installer](https://github.com/derickjoseph8/readin-ai/releases/download/v1.6.0/ReadIn-AI-Setup-1.6.0.exe)
- [macOS DMG](https://github.com/derickjoseph8/readin-ai/releases/download/v1.6.0/ReadIn-AI-1.6.0.dmg)
- [Linux AppImage](https://github.com/derickjoseph8/readin-ai/releases/download/v1.6.0/ReadIn-AI-1.6.0.AppImage)

### Previous Versions
See [GitHub Releases](https://github.com/derickjoseph8/readin-ai/releases) for all versions.

---

*ReadIn AI - Your Intelligent Meeting Assistant*
