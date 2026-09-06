# GameGem Frontend — Final Carousel + Chat UX

Static frontend files for GameGem.

## Structure

```text
frontend/
├── index.html
├── css/
│   └── styles.css
├── js/
│   ├── data.js
│   └── app.js
└── assets/
    └── gamegem-logo.jpg
```

## Featured-game carousel

- Exactly one stable active game is kept in the carousel after each transition.
- During navigation, one temporary incoming slide is created so the old game can exit while the next game enters smoothly.
- Left/right keyboard arrows navigate the carousel unless the user is typing in a form field.
- Hovering the left or right edge reveals a subtle translucent white navigation affordance.
- Mouse/touch horizontal swipe is supported.
- Automatic advancement is retained at 7.5 seconds.
- Hover/focus pauses the automatic timer.
- The hero height adapts to the browser viewport so game information remains visible without unnecessary scrolling.

## GameGem AI

The top-right GameGem logo toggles the assistant open and closed.

The redesigned composer includes:
- visible multiline message field
- auto-grow up to a sensible maximum height
- polished send button
- Enter to send
- Shift+Enter for a new line
- streamed FastAPI responses via `/api/chat/stream`

## Asset policy

Only one local image asset is required:

```text
assets/gamegem-logo.jpg
```

Game cover/hero images are referenced remotely from `js/data.js`. If a remote image fails, a generated browser-side SVG placeholder is used; no extra asset files are needed.
