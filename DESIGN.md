# DESIGN.md — AI-PPTX

> Visual language guide for the AI-PPTX application.
> Drop this file into any Claude project to maintain consistent UI aesthetics.

---

## 1. Brand Identity

**Product:** AI-PPTX — AI-powered PowerPoint generation tool  
**Tagline:** From data to deck, instantly  
**Aesthetic:** Dark developer-tool meets editorial precision. Feels like a premium IDE crossed with a design studio.  
**Mood:** Confident, technical, modern — not corporate, not playful. Think "the tool serious designers actually use."

---

## 2. Color Tokens

### Base Surfaces
| Token         | Value                    | Usage                        |
|---------------|--------------------------|------------------------------|
| `--bg`        | `#0b0e1a`               | App background (deepest)     |
| `--bg-panel`  | `#111627`               | Sidebars, top bar            |
| `--bg-card`   | `#161d30`               | Cards, inputs, dropdowns     |
| `--bg-hover`  | `#1c2540`               | Hover states, scrollbars     |

### Borders
| Token          | Value                        | Usage                      |
|----------------|------------------------------|----------------------------|
| `--border`     | `rgba(255,255,255,0.07)`    | Default borders            |
| `--border-hi`  | `rgba(99,180,255,0.3)`      | Focus, selected, highlight |

### Typography
| Token         | Value       | Usage                       |
|---------------|-------------|-----------------------------|
| `--txt`       | `#e2e8f0`  | Primary text                |
| `--txt-muted` | `#64748b`  | Secondary / labels          |
| `--txt-dim`   | `#334155`  | Placeholders, dividers      |

### Accent Palette (multi-accent system)
| Token       | Value      | Usage                               |
|-------------|------------|-------------------------------------|
| `--accent`  | `#4f9cf9` | Primary CTA, links, active states   |
| `--accent2` | `#f97316` | Generate button, warnings, charts   |
| `--accent3` | `#a78bfa` | Content blocks, secondary highlights|
| `--accent4` | `#34d399` | Success, table blocks, green states |
| `--accent5` | `#f472b6` | Insight blocks, pink accents        |

### Slide Block Colors (canvas UI only)
```
Title:   rgba(79,156,249,0.20)   border rgba(79,156,249,0.40)   text #4f9cf9
Table:   rgba(52,211,153,0.15)   border rgba(52,211,153,0.40)   text #34d399
Chart:   rgba(249,115,22,0.15)   border rgba(249,115,22,0.40)   text #f97316
Content: rgba(167,139,250,0.15)  border rgba(167,139,250,0.40)  text #a78bfa
Insight: rgba(244,114,182,0.15)  border rgba(244,114,182,0.40)  text #f472b6
Image:   rgba(234,179,8,0.15)    border rgba(234,179,8,0.40)    text #eab308
```

---

## 3. Typography

### Font Stack
| Role          | Font                          | Fallback         |
|---------------|-------------------------------|------------------|
| UI / Display  | **Syne**                      | sans-serif       |
| Monospace     | **JetBrains Mono**            | monospace        |
| Document text | **Georgia**                   | serif            |

### Type Scale
| Element          | Size  | Weight | Family         | Notes                              |
|------------------|-------|--------|----------------|------------------------------------|
| Logo / Brand     | 18px  | 800    | Syne           | letter-spacing: 2px                |
| Nav button       | 13px  | 700    | Syne           | letter-spacing: 0.5px              |
| Panel title      | 12px  | 700    | Syne           | UPPERCASE, letter-spacing: 1.5px   |
| Section label    | 11px  | 700    | Syne           | UPPERCASE, letter-spacing: 1.5px   |
| Body text        | 13px  | 400    | Syne           |                                    |
| Code / badges    | 10–13px | 600  | JetBrains Mono |                                    |
| Document editor  | 14px  | 400    | Georgia        | line-height: 1.7, white bg         |

### Typography Rules
- **NEVER** use Inter, Roboto, or system-ui for UI elements
- Syne for ALL interface text — its geometric weight conveys precision
- JetBrains Mono for technical labels, chips, badges, version numbers
- Georgia exclusively for the content editor pane (warm editorial contrast to the dark UI)
- Letter-spacing on uppercase labels: always 1.5px minimum

---

## 4. Layout & Spatial System

### Grid
- **Step 1:** 50% left panel | 50% right preview
- **Step 2:** 30% design panel | 20% slide list | 50% canvas
- Panels separated by `1px solid var(--border)` lines — never heavy borders

### Spacing
- Panel padding: `16px 20px`
- Card padding: `14px 16px`
- Top bar height: `52px` fixed
- Border radius: `10px` (cards) / `6px` (small elements) / `8px` (buttons)

### Composition Rules
- Use `flex` exclusively — no floats
- Panels scroll internally; app viewport never scrolls
- Content layers: bg → panel → card → element
- Scrollbars: thin (5px), thumb color `var(--bg-hover)`, transparent track

---

## 5. Components

### Buttons
```
Primary CTA:  bg var(--accent),  text #fff,  hover bg #3b82f6 + translateY(-1px)
Generate:     gradient(135deg, var(--accent2) → #ef4444),  hover opacity 0.9
Back/Ghost:   bg var(--bg-card), border var(--border), hover border-color var(--border-hi)
All buttons:  border-radius 8px, font Syne 700, transition 0.2s
```

### Cards
```
Background: var(--bg-card)
Border: 1px solid var(--border)
Border-radius: var(--radius) = 10px
Hover: border-color rgba(255,255,255,0.12)
Selected: border-color var(--accent)
```

### Inputs & Dropdowns
```
Background: var(--bg-card)
Border: 1px solid var(--border) → focus: var(--border-hi)
Font: Syne 13px
Border-radius: 6px
Padding: 9px 12px
```

### Chips / Badges
```
Active:   bg var(--accent), text #fff, border var(--accent)
Inactive: bg var(--bg-card), text var(--txt-muted), border var(--border)
Hover:    border var(--border-hi)
Font:     JetBrains Mono 11px 600
```

### Toggle Groups
```
Container: bg var(--bg), border-radius 8px, padding 3px
Option active:   bg var(--bg-card), text var(--txt), box-shadow 0 1px 4px rgba(0,0,0,0.3)
Option inactive: text var(--txt-muted)
```

### Toast Notifications
```
Position: fixed bottom-center
Default: bg var(--bg-card), border var(--border-hi)
Success: border + text var(--accent4)  = green
Error:   border + text #ef4444         = red
Animation: translateY spring (cubic-bezier 0.34,1.56,0.64,1)
```

### Progress Overlay
```
Background: rgba(11,14,26,0.85) with backdrop-filter blur(8px)
Progress bar: gradient var(--accent) → var(--accent3)
Bar height: 4px, border-radius 2px
```

---

## 6. Motion & Animation

- **Spring easing:** `cubic-bezier(0.34, 1.2, 0.64, 1)` — canvas block transitions
- **Toast spring:** `cubic-bezier(0.34, 1.56, 0.64, 1)` — bouncy entry
- **Standard:** `transition: all 0.2s` or `0.18s` for hover states
- **Spinner:** `border-top-color var(--accent)`, 0.8s linear
- **Canvas blocks:** `transition: all 0.25s` spring — layout shifts feel physical

### Principles
- Hover states always respond in ≤200ms
- Page transitions use opacity + translate, not jump cuts
- Only animate properties that matter: `transform`, `opacity`, `border-color`, `background`
- Never animate `width/height` directly — use `transform: scale()` instead

---

## 7. Canvas Preview System

The slide canvas is the product's hero element:

```
Container:    white bg, border-radius 8px, box-shadow 0 8px 40px rgba(0,0,0,0.4)
Aspect ratio: 16/9
Max width:    760px
Wrapper:      24px padding, centered, overflow auto
```

Block colors are semantic (each content type has a unique hue) to allow at-a-glance slide structure reading. This is intentional — the canvas is a **schematic view**, not a realistic preview.

---

## 8. PPTX Output Design Tokens

The generated PowerPoint files use a separate, light-mode design token system:

```json
{
  "bg_dark":    "#1a1a1a",
  "bg_light":   "#fafafa",
  "accent":     "#ff6b35",
  "heading":    "#1a1a1a",
  "body":       "#1a1a1a",
  "font_main":  "Arial",
  "font_heading": "Arial"
}
```

> **Note:** PPTX output intentionally uses Arial for maximum compatibility across Office installations. The UI uses Syne/JetBrains — do not cross-contaminate these systems.

---

## 9. Anti-Patterns (Never Do)

- ❌ Purple gradients on white or light backgrounds
- ❌ Inter, Roboto, Arial, or system-ui in the app UI
- ❌ Rounded corners > 12px on any element
- ❌ Bright full-saturation colors as backgrounds
- ❌ More than 3 font sizes in a single panel
- ❌ Solid white or solid black backgrounds in the app shell
- ❌ Generic card grids with equal gutters and equal sizing (boring)
- ❌ Emoji in UI chrome (OK in content/data only)
- ❌ Box shadows on everything — reserve for floating elements and canvas

---

## 10. Design Rationale

**Why dark?** — AI tools are used for hours. Dark reduces eye strain and makes the colorful slide canvas pop by contrast.

**Why Syne?** — Its wide, geometric letterforms read well at small sizes and carry authority without being corporate. Unique enough to be remembered.

**Why multi-accent?** — Slide content types (title, table, chart, insight) need instant visual disambiguation. A monochrome accent system would require text labels everywhere. Color does it in milliseconds.

**Why JetBrains Mono for chips?** — Technical metadata (slide types, layout tokens, percentages) benefits from monospace alignment. It also signals "this is data, not prose."
