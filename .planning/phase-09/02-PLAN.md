# Plan: Phase 9 — Mobile-First Chat Interface

## Goal
Build responsive chat UI for field technicians with touch-friendly design, voice input, and offline capabilities.

## Requirement IDs
COP-04, UX-01, UX-02

## Success Criteria
1. Interface works on mobile devices for field technicians
2. Responsive web interface works on desktop and mobile devices
3. Search results appear within 5 seconds (time-to-answer improvement)
4. Touch-friendly input with 44x44px minimum targets
5. Voice input for hands-free operation
6. Offline capabilities via PWA

## Tasks

### Task 9.1: Project Setup
- [ ] Initialize React project with Vite
- [ ] Set up Tailwind CSS
- [ ] Configure React Router for navigation
- [ ] Set up React Query for state management

### Task 9.2: Chat Interface Component
- [ ] Create message bubble components (user/assistant)
- [ ] Implement input area with send button
- [ ] Add loading indicators
- [ ] Implement auto-scroll to latest message

### Task 9.3: Source Citation Display
- [ ] Create source card component
- [ ] Implement citation formatting
- [ ] Add click-to-open functionality
- [ ] Show source preview on hover

### Task 9.4: Confidence Badge System
- [ ] Create confidence badge component
- [ ] Implement color coding (green/yellow/red)
- [ ] Add tooltip with confidence explanation
- [ ] Show confidence in message header

### Task 9.5: Voice Input Integration
- [ ] Implement Web Speech API
- [ ] Add push-to-talk button
- [ ] Show recording indicator
- [ ] Handle speech recognition results

### Task 9.6: Touch-Friendly Design
- [ ] Ensure 44x44px minimum tap targets
- [ ] Add proper spacing between elements
- [ ] Implement swipe gestures for navigation
- [ ] Optimize for thumb reach zones

### Task 9.7: PWA Setup
- [ ] Create manifest.json
- [ ] Set up service worker
- [ ] Implement offline fallback
- [ ] Add install prompt

### Task 9.8: Performance Optimization
- [ ] Implement lazy loading for chat history
- [ ] Add infinite scroll for older messages
- [ ] Optimize for slow networks
- [ ] Cache recent queries

## Technical Design

### Project Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── SourceCard.jsx
│   │   │   └── ConfidenceBadge.jsx
│   │   └── Voice/
│   │       └── VoiceInput.jsx
│   ├── pages/
│   │   └── Copilot.jsx
│   ├── services/
│   │   └── api.js
│   └── App.jsx
├── public/
│   ├── manifest.json
│   └── sw.js
├── tailwind.config.js
└── vite.config.js
```

### Dependencies
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "react-router-dom": "^6.20.0",
  "@tanstack/react-query": "^5.8.0",
  "tailwindcss": "^3.3.5"
}
```

## Verification

### Unit Tests
- Test chat interface rendering
- Test message bubble display
- Test source citation display
- Test confidence badge display

### Integration Tests
- Test chat flow end-to-end
- Test voice input functionality
- Test PWA installation

### Manual Verification
- Test on mobile devices (iOS, Android)
- Test on desktop browsers
- Test on slow networks (3G)
- Test offline functionality

## Dependencies
- Phase 6: RAG Query Engine & CAG Caching

## Timeline
- Task 9.1: 1 hour
- Task 9.2: 2 hours
- Task 9.3: 1.5 hours
- Task 9.4: 1 hour
- Task 9.5: 1.5 hours
- Task 9.6: 1 hour
- Task 9.7: 1.5 hours
- Task 9.8: 0.5 hours
- **Total: 10 hours**

## Risks
1. **Mobile performance**: Older devices may struggle
   - Mitigation: Progressive enhancement, lazy loading
2. **Voice input accuracy**: Background noise affects recognition
   - Mitigation: Push-to-talk, visual feedback
3. **Offline limitations**: Service workers are complex
   - Mitigation: Start with online-only, add offline later
