# ReadIn AI - Comprehensive Application Audit Report

## EXECUTIVE SUMMARY

| Component | Critical | High | Medium | Low | Total |
|-----------|----------|------|--------|-----|-------|
| Desktop App (Core) | 3 | 5 | 6 | 3 | 17 |
| Desktop App (UI) | 2 | 6 | 12 | 2 | 22 |
| Backend API | 2 | 8 | 15 | 5 | 30 |
| Web Application | 3 | 8 | 12 | 4 | 27 |
| Config & Deployment | 5 | 10 | 17 | 4 | 36 |
| **TOTAL** | **15** | **37** | **62** | **18** | **132** |

---

## CRITICAL ISSUES BY COMPONENT

### Desktop Application - Critical Issues

| Issue | File:Line | Impact |
|-------|-----------|--------|
| API key imported from config without protection | `main.py:20` | Key visible in process memory |
| Auth tokens stored in plaintext JSON | `src/api_client.py:36-42` | Token theft via filesystem |
| Race condition in audio buffer | `audio_capture.py:270-275` | Audio corruption, crashes |
| Direct UI updates from background threads | `audio_setup_dialog.py:512-648` | Race conditions, crashes |

### Backend API - Critical Issues

| Issue | File:Line | Impact |
|-------|-----------|--------|
| Admin authorization logic inverted | `main.py:1124-1140` | Users bypass admin checks |
| 30-day JWT tokens, no refresh | `config.py:52` | Compromised tokens valid too long |
| No rate limit on email verification | `main.py:628-651` | Brute force token guessing |
| TOTP backup codes stored plaintext | `models.py:150` | 2FA bypass if DB compromised |

### Web Application - Critical Issues

| Issue | File:Line | Impact |
|-------|-----------|--------|
| XSS in chat message rendering | `dashboard/page.tsx:289` | Script injection |
| Auth tokens in localStorage | `lib/api/client.ts:19` | XSS can steal tokens |
| Missing error boundaries | `dashboard/layout.tsx` | Crashes propagate |
| Hardcoded API URLs | `login/page.tsx:32` | Deployment inflexibility |

---

## DETAILED FINDINGS

### 1. Desktop Application - Security

#### Insecure Credential Storage
- **Location:** `src/api_client.py:15, 36-42`
- **Issue:** Tokens stored as plaintext JSON at `~/.readin/auth.json`
- **Fix:** Use OS credential storage (Windows DPAPI, macOS Keychain)

#### Missing Error Handling in Audio Pipeline
- **Location:** `transcriber.py:117-180`, `audio_capture.py:238-290`
- **Issue:** Errors rate-limited or silently swallowed
- **Fix:** Implement proper error propagation to UI

#### WebSocket Message Validation Missing
- **Location:** `browser_bridge.py:181-256`
- **Issue:** No size limits on audio data, potential memory exhaustion
- **Fix:** Add message size validation, max 10MB

#### Incomplete Resource Cleanup
- **Location:** `audio_capture.py:594-615`
- **Issue:** Thread join with 1 second timeout may leave threads orphaned
- **Fix:** Implement proper shutdown sequence with queue clearing

### 2. Desktop Application - UI/UX

#### Thread Safety Violations
- **Location:** `audio_setup_dialog.py:521`
- **Issue:** `self._testing` flag modified from background thread
- **Fix:** Use Qt signals for all cross-thread state changes

#### Missing Multi-Monitor Support
- **Location:** `overlay.py:373-380`
- **Issue:** Only uses `primaryScreen()`, overlay appears wrong on multi-monitor
- **Fix:** Check screen geometry, validate saved positions

#### Settings Not Persisted Correctly
- **Location:** `settings_window.py:617-629`
- **Issue:** Theme and shortcut changes don't take effect until restart
- **Fix:** Emit settings changed signal, update all windows

#### Accessibility Issues
- **Location:** `overlay.py:96-206`
- **Issue:** 24x24px buttons too small, color-only status indication
- **Fix:** Increase button size to 44x44px, add text labels

### 3. Backend API - Security

#### Authorization Bypass
```python
# CURRENT (WRONG):
if not user.is_staff and user.staff_role not in ["super_admin", "admin"]:

# CORRECT:
if not (user.is_staff and user.staff_role in ["super_admin", "admin"]):
```

#### Missing Rate Limits
| Endpoint | Current | Recommended |
|----------|---------|-------------|
| GET /user/me | None | 30/minute |
| POST /usage/increment | None | 60/minute |
| DELETE /api-keys/{id} | None | 5/minute |
| GET /organizations/my | None | 30/minute |

#### N+1 Query Issues
- **Location:** `main.py:709-755` (get_me endpoint)
- **Fix:** Use SQLAlchemy `joinedload()`:
```python
user = db.query(User).options(
    joinedload(User.profession),
    joinedload(User.organization)
).filter(User.id == user.id).first()
```

#### Missing Database Indexes
```python
# Add to models.py:
Index("ix_user_email_verification_token", "email_verification_token"),
Index("ix_user_password_reset_token", "password_reset_token"),
Index("ix_meeting_user_status", "user_id", "status"),
```

### 4. Web Application - Security & Performance

#### XSS Vulnerability
- **Location:** `components/ChatWidget.tsx:277-289`
- **Issue:** User messages rendered without sanitization
- **Fix:** Use DOMPurify or React's built-in escaping

#### CSRF Protection Missing
- **Location:** `lib/api/client.ts:41-83`
- **Issue:** No CSRF tokens in mutating requests
- **Fix:** Implement CSRF token handling or use SameSite cookies

#### Missing Code Splitting
```typescript
// Current:
import OnboardingModal from '@/components/OnboardingModal';

// Fix:
const OnboardingModal = dynamic(() => import('@/components/OnboardingModal'), {
  loading: () => <OnboardingSkeleton />
});
```

#### Memory Leak in Chat Polling
- **Location:** `ChatWidget.tsx:62-63`
- **Issue:** `pollMessages()` called before interval setup, race condition
- **Fix:** Move initial call inside useEffect with proper cleanup

### 5. Configuration & Deployment

#### Docker Security Gaps
```yaml
# Add to docker-compose.yml fastapi service:
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

#### Default Password in Compose
- **Location:** `docker-compose.yml:13`
- **Current:** `POSTGRES_PASSWORD: ${DB_PASSWORD:-readin_secure_password}`
- **Fix:** Remove default, require explicit env var

#### Dependency Pinning Missing
```txt
# Current:
fastapi>=0.109.0

# Fix:
fastapi>=0.109.0,<0.114.0
```

#### CI/CD Security Checks Non-Blocking
- **Location:** `.github/workflows/ci.yml:87-92`
- **Issue:** `continue-on-error: true` allows vulnerable builds
- **Fix:** Remove `continue-on-error` for security jobs

---

## PRIORITIZED REMEDIATION PLAN

### Phase 1: Critical Security (This Week)

| Priority | Task | Files |
|----------|------|-------|
| 1 | Remove .env from build.spec | `build.spec:27-29` |
| 2 | Fix admin authorization logic | `main.py:1124-1140` |
| 3 | Implement OS credential storage | `src/api_client.py` |
| 4 | Add rate limiting to auth endpoints | `main.py`, `routes/` |
| 5 | Fix XSS in chat rendering | `ChatWidget.tsx:277` |

### Phase 2: High Priority (Week 2-3)

| Priority | Task | Files |
|----------|------|-------|
| 6 | Add threading locks to audio buffer | `audio_capture.py:270` |
| 7 | Implement JWT refresh tokens | `auth.py`, `config.py` |
| 8 | Add React error boundaries | `dashboard/layout.tsx` |
| 9 | Fix N+1 database queries | `main.py:709-755` |
| 10 | Add missing database indexes | `models.py` |
| 11 | Implement CSRF protection | `lib/api/client.ts` |

### Phase 3: Medium Priority (Week 4)

| Priority | Task | Files |
|----------|------|-------|
| 12 | Multi-monitor overlay support | `overlay.py:373-380` |
| 13 | Proper resource cleanup | `audio_capture.py:594` |
| 14 | Input validation on settings | `settings_manager.py` |
| 15 | Lazy load large components | `dashboard/page.tsx` |
| 16 | Pin dependency versions | `requirements.txt` |
| 17 | Add backup strategy for PostgreSQL | `docker-compose.yml` |

### Phase 4: Polish & Hardening (Ongoing)

- Replace all bare `except:` clauses with specific exceptions
- Add comprehensive audit logging
- Implement accessibility improvements (WCAG 2.1)
- Add E2E tests for critical paths
- Implement anomaly detection using existing models
- Add GPG signatures to releases

---

## QUICK WINS (Can Fix Immediately)

### 1. Fix admin authorization (`main.py`):
```python
# Line ~1130, change:
if not user.is_staff and user.staff_role not in ["super_admin", "admin"]:
# To:
if not (user.is_staff and user.staff_role in ["super_admin", "admin"]):
```

### 2. Remove .env bundling (`build.spec`):
```python
# Delete lines 27-29 entirely
```

### 3. Reduce JWT expiration (`backend/config.py`):
```python
# Line 52, change:
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))
# To:
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "1"))
```

### 4. Add audio buffer lock (`audio_capture.py`):
```python
# Add at class level:
self._buffer_lock = threading.Lock()

# In processing method:
with self._buffer_lock:
    self._audio_buffer = np.concatenate([self._audio_buffer, audio])
```

---

## SUMMARY

Your application has a solid architecture but needs security hardening before production. The most critical issues are:

1. **Secrets embedded in desktop builds** - Remove .env bundling
2. **Authorization bypass** - Fix admin logic
3. **XSS vulnerabilities** - Sanitize user content
4. **Race conditions in audio** - Add thread synchronization
5. **JWT token lifetime** - Reduce expiration, add refresh tokens

---

## FILES TO MODIFY

### Desktop Application
- `build.spec` - Remove .env bundling
- `src/api_client.py` - Secure credential storage
- `src/audio_capture.py` - Thread safety, resource cleanup
- `src/audio_capture_enhanced.py` - Thread safety
- `src/transcriber.py` - Error handling
- `src/browser_bridge.py` - Message validation, async safety
- `src/ai_assistant.py` - Thread synchronization
- `src/settings_manager.py` - Input validation
- `src/ui/overlay.py` - Multi-monitor, accessibility
- `src/ui/audio_setup_dialog.py` - Thread safety
- `src/ui/settings_window.py` - Settings persistence
- `src/ui/login_window.py` - Loading states
- `src/export_manager.py` - File permissions

### Backend
- `backend/main.py` - Auth logic, rate limiting, N+1 queries
- `backend/config.py` - JWT expiration
- `backend/auth.py` - Token refresh, logging
- `backend/models.py` - Database indexes, encryption
- `backend/routes/bulk.py` - Input validation
- `backend/routes/api_keys.py` - Rate limiting
- `backend/routes/organizations.py` - Authorization
- `backend/middleware/logging_middleware.py` - Sanitization
- `backend/docker-compose.yml` - Security options
- `backend/Dockerfile` - Health check

### Web Application
- `web/components/ChatWidget.tsx` - XSS, memory leaks
- `web/app/(static)/dashboard/page.tsx` - Error boundaries, lazy loading
- `web/app/(static)/dashboard/layout.tsx` - Error boundaries
- `web/app/(static)/login/page.tsx` - Error handling
- `web/lib/api/client.ts` - CSRF, error messages
- `web/lib/hooks/useAuth.tsx` - Error handling
- `web/lib/hooks/useMeetings.ts` - Error handling

### Configuration
- `requirements.txt` - Version pinning
- `backend/requirements.txt` - Version pinning
- `web/package.json` - Version pinning
- `.github/workflows/ci.yml` - Security checks blocking
- `.github/workflows/build.yml` - Checksums
