# Research: Phase 9 — Mobile-First Chat Interface

## Responsive Design Patterns

### Mobile-First Approach
```css
/* Base styles (mobile) */
.container { padding: 1rem; }

/* Tablet */
@media (min-width: 768px) {
  .container { padding: 2rem; }
}

/* Desktop */
@media (min-width: 1024px) {
  .container { padding: 3rem; }
}
```

### Touch-Friendly Interfaces
- **Tap targets**: Minimum 44x44px
- **Spacing**: 8px minimum between interactive elements
- **Gestures**: Swipe, pinch-to-zoom for knowledge graph

### PWA Patterns
- **Service Worker**: Cache static assets
- **Manifest**: Add to home screen
- **IndexedDB**: Store recent queries offline

## Chat Interface Patterns

### Message Bubbles
- **User messages**: Right-aligned, primary color
- **Assistant messages**: Left-aligned, neutral color
- **System messages**: Centered, muted color

### Source Citation Display
- **Inline citations**: [1], [2] in text
- **Hover preview**: Show source excerpt on hover
- **Click to open**: Navigate to source document

### Confidence Badges
- **High confidence**: Green badge (4-5)
- **Medium confidence**: Yellow badge (3)
- **Low confidence**: Red badge (1-2)

## Voice Input

### Web Speech API
```javascript
const recognition = new webkitSpeechRecognition();
recognition.continuous = false;
recognition.interimResults = false;
recognition.lang = 'en-US';
```

### Whisper API
- Better accuracy than Web Speech API
- Costs money
- Requires network connection

### Push-to-Talk
- Button to start/stop recording
- Visual feedback (recording indicator)
- Cancel option

## Performance Optimization

### Lazy Loading
- **React.lazy**: Component-level code splitting
- **Intersection Observer**: Load on scroll
- **Virtual scrolling**: For large lists

### Caching Strategies
- **React Query**: Cache API responses
- **Service Worker**: Cache static assets
- **localStorage**: Cache user preferences

### Accessibility (WCAG)
- **Keyboard navigation**: Tab through all elements
- **Screen reader**: Proper ARIA labels
- **Color contrast**: Minimum 4.5:1 ratio
- **Focus visible**: Clear focus indicators

## Common Pitfalls

1. **Mobile performance**: Test on real devices, not just simulators
2. **Offline limitations**: Service workers are complex
3. **Accessibility oversights**: Test with screen readers
4. **Voice input accuracy**: Background noise affects recognition
5. **Touch target size**: Too small targets frustrate users
