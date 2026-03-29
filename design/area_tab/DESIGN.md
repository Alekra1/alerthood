# AREA Tab — Neighbourhood Summary

## 1. What This Is

A **new bottom-nav tab** for AlertHood. A single scrollable screen that answers "how safe is this area right now?" at a glance. It acts as a neighbourhood intelligence brief — the user's first stop before going out.

On open, it auto-detects the user's location and displays the nearest area's summary. In MVP the user does not manually pick an area — it is resolved from their GPS coordinates.

**Creative North Star**: "Opening a classified briefing folder." Authoritative, data-rich, instantly scannable. The user assesses their neighbourhood's safety in under 3 seconds. The safety score hero is the "headline" — everything else supports it.

---

## 2. Navigation & Access

### Bottom Nav
- Add a **4th tab**: AREA (between FEED and PROFILE, or after PROFILE)
- **Icon**: Material Symbol — `shield`, `location_city`, `apartment`, or `insights`
- Active state: same treatment as other tabs — icon filled, label colored `#FF5545`, top border accent

### Default Behaviour (MVP)
1. User taps AREA tab
2. Browser Geolocation API requests user's position
3. `GET /api/areas/detect?lat=&lng=` resolves to an area
4. Area summary loads and renders

### Fallback (location unavailable)
- Show a prompt: "Enable location to see your area summary"
- Below it: list of the user's subscribed areas to pick from manually

### Future (TODO — do NOT design now, just note)
- Area selector/changer within the tab header
- Tapping a neighbourhood on the main map opens this tab with that area pre-selected
- Neighbourhood tappable/choosable from the tab itself

---

## 3. Design System

**MUST follow the AlertHood Editorial Neo-Brutalism system.** Reference files:
- `design/alerthood_neo_noir/DESIGN.md` — full design system
- `design/alerthood_map_view/code.html` — Map tab mockup
- `design/alerthood_threat_feed/code.html` — Feed tab mockup
- `design/alerthood_profile_tab/code.html` — Profile tab mockup (has circular progress gauge)

### Non-Negotiables

| Rule | Token |
|---|---|
| Background | `#131313` (`surface`) |
| Component surface | `#201F1F` (`surface_container`) + `3px solid black border` |
| Elevated surface | `#2A2A2A` (`surface_container_high`) + `4px 4px 0px #000000` hard shadow |
| Borders | 2-3px `solid #000000` — never 1px, never grey |
| Shadows | Hard only: `4px 4px 0px #000000` — never blurred |
| Button press | `active:translate-x-[2px] active:translate-y-[2px] active:shadow-none` |
| Transitions | `0.1s` or `0s` — no smooth/slow animations |
| Fonts | Space Grotesk (headlines, uppercase), Inter (body, labels) |
| Section dividers | Never 1px grey lines. Use background shifts or 2-3px black strokes. |

### Category Colors

| Category | Fill (container) | Text/border (on-container) |
|---|---|---|
| CRIME | `#FF5545` | `#5C0002` |
| UTILITY / INFRA | `#FE9400` | `#633700` |
| NATURAL | Yellow tones | — |
| DISTURBANCE | `#C567F4` | `#460066` |

### Risk Colors (for safety score & badges)

| Range | Label | Color |
|---|---|---|
| `>= 70` | LOW RISK | Neon green / `#4ade80` |
| `40–69` | MEDIUM RISK | Amber / `#FE9400` / `secondary-container` |
| `< 40` | HIGH RISK | Red / `#FF5545` / `primary-container` |

### Typography

| Role | Font | Size | Weight | Case |
|---|---|---|---|---|
| Display (hero numbers) | Space Grotesk | 3.5rem | Black | — |
| Headline (section headers) | Space Grotesk | 2rem | Bold | Uppercase |
| Title (card titles) | Inter | 1.125rem | Semi-Bold | — |
| Body (descriptions) | Inter | 0.875rem | Regular | — |
| Label (metadata, timestamps) | Inter | 0.75rem | Bold | Uppercase |

---

## 4. Layout Constraints

- **Mobile-first**: 390px width (iPhone 14). Desktop later.
- **Scrollable**: Single column, vertical scroll. All sections stack.
- **TopBar**: Fixed at top — AlertHood logo (`security` icon + "ALERTHOOD" in `#FF5545` italic) + notification bell. 64px height. `border-b-2 border-black shadow-[4px_4px_0px_#000000]`.
- **BottomNav**: Fixed at bottom — now **4 tabs**: MAP, FEED, AREA, PROFILE. AREA tab in active state for this mockup. 80px height. `border-t-2 border-black`.
- **Content area**: `mt-20` (offset for TopBar), `pb-24` (offset for BottomNav), `px-4` (16px horizontal padding).
- **Spacing between sections**: `space-y-8` (32px).

---

## 5. Page Sections (top to bottom)

### 5.1 Area Header

Compact header at the top of the scrollable content:

- **Neighbourhood name** — Space Grotesk, bold, uppercase, large (e.g. "WEST LOOP")
- **City** — Inter, smaller, muted `on-surface-variant` color (e.g. "Chicago, IL")
- **Risk level badge** — small pill/chip showing `LOW RISK` / `MEDIUM RISK` / `HIGH RISK`
  - Filled background matching risk color (green/amber/red)
  - Small filled circle dot before the text
  - Text in `on-container` color for that risk level (dark text on colored background)
  - Positioned inline to the right of the area name, or below on narrow screens

**Sample data**: "WEST LOOP" · "Chicago, IL" · `MEDIUM RISK` (amber badge)

---

### 5.2 Safety Score Hero

**The dominant visual element. First thing the eye lands on.**

Contained in a `surface_container` card (`bg-[#201F1F]`) with 3px black border and hard shadow.

**Circular gauge** (center of card):
- Use **conic-gradient** technique (same as Profile tab's trust score, but larger):
  - Outer ring: conic-gradient filled to the score percentage in risk color, remainder in `#2A2A2A`
  - Inner circle: `bg-[#201F1F]` overlay
  - Inside: score number in **Space Grotesk 3.5rem Black** + `/100` in smaller muted Inter
- **Ring color** follows risk logic:
  - Score 65 → amber ring (`#FE9400` or `#BA7517`)
  - Score 80 → green ring (`#4ade80`)
  - Score 25 → red ring (`#FF5545`)

**Below the gauge** (same card):
- **Subtitle**: "Safety score · updated X min ago" — Inter label, small, muted
- **One-line description**: Contextual text, Inter body:
  - Score >= 70: "Low incident activity. Generally safe."
  - Score 40-69: "Elevated activity near [location]. Exercise caution after dark."
  - Score < 40: "High incident volume reported. Stay alert."

**Sample data**: Score `65` / 100, amber ring, "Safety score · updated 4 min ago", "Elevated activity near Union Station. Exercise caution after dark."

---

### 5.3 Active Alert Card ("WATCH OUT")

**Conditional** — only renders when there are HIGH/CRITICAL severity events in last 24h. In the mockup, **include it** (assume there is an active alert).

- **Card**: `surface_container` background
- **Left impact bar**: 6px thick vertical stripe on the left edge, **amber** (`secondary-container` `#FE9400`) or **red** (`primary-container` `#FF5545`) depending on severity
- **3px black border**, hard shadow
- **Header row**: Warning triangle icon (`warning` Material Symbol) + "ACTIVE ALERT" in bold uppercase label text, colored amber/red
- **Body text**: Event description — title, location, time ago. 2-3 lines max. Inter body text.
- Should feel urgent but not panic-inducing — "pop" against the dark background without clashing with the hero gauge above

**Sample data**: "ACTIVE ALERT" · amber impact bar · "Pickpocket reports spiking near Union Station food court (Sat–Sun lunch). Keep bags front-facing and avoid phone use in crowded areas."

---

### 5.4 Mini Heatmap

A small, read-only map preview of the neighbourhood:

- **Container**: Rounded card (`rounded-xl`), 3px black border, hard shadow
- **Height**: ~160-180px
- **Content**:
  - Dark basemap (CartoDB Dark Matter tiles or dark SVG grid approximation)
  - Heatmap cells colored green/yellow/orange/red showing incident density
  - A few colored pin dots for recent events (red=crime, orange=utility, purple=disturbance, yellow=natural)
- **No drag/zoom** — static snapshot. Minimal or no interactivity.
- **Overlay** (bottom-left): Small label — "12 events · last 48h" in muted Inter label text
- **Button** (below or overlaid bottom-right): "VIEW ON MAP →" — small hard-shadow button, navigates to main map centered on this area. Primary button style: `bg-primary-container`, 3px black border, hard shadow, `on-primary-container` text.

**For the HTML mockup**: A static SVG or placeholder image is acceptable if live tiles are too complex. Use a dark grid with colored dots to approximate the heatmap look.

---

### 5.5 Recent Incidents (3-5 items)

Compact list of the most recent events in this area (last 48h):

- **Section header**: "RECENT ACTIVITY" — Space Grotesk, bold, uppercase, with a short colored accent bar (small horizontal line in `primary` or `secondary` color before the text, matching Profile tab section header pattern)

- **Each item** — lightweight card/row (no hard shadows, minimal treatment):
  - `surface_container` or `surface_container_low` background
  - Thin outline or `surface` background shift to separate items
  - **Layout per item**:
    - Top row: **Category badge** (small colored pill — CRIME=red, UTILITY=orange, NATURAL=yellow, DISTURBANCE=purple) + **time ago** in muted label text (e.g. "2h ago")
    - Below: **Title** — event title text, Inter body, truncated to 2 lines
    - Below or inline right: **Upvote count** — small `▲ 14` in muted text (display only, no interactive buttons)
  - Keep these visually lightweight — they are previews, not full feed cards

- **Footer**: "See all in Feed →" link/button — `primary` color text, navigates to `/feed`

**Sample data** (4 items):
1. `CRIME` badge (red) · "2h ago" · "Bag snatched near Market Street tram stop. Victim described two individuals on bicycles." · `▲ 14`
2. `DISTURBANCE` badge (purple) · "5h ago" · "Loud altercation outside venue. Security intervened. Area calm by 02:15." · `▲ 8`
3. `CRIME` badge (red) · "9h ago" · "Phone theft reported at food court. Suspect left via north entrance." · `▲ 22`
4. `UTILITY` badge (orange) · "14h ago" · "Street lighting out on Dale Street. Council notified." · `▲ 5`

---

### 5.6 AI Area Brief (Placeholder)

A stub section for a future AI-generated safety briefing:

- **Card**: `surface_container` background, 3px black border
- **Accent color**: Use `tertiary` (`#E8B3FF`) / purple-violet tint to visually signal "AI" — small icon, header text, or subtle border highlight
- **Header row**: AI sparkle icon (`auto_awesome` or `psychology` Material Symbol) in purple + "AI AREA BRIEF · COMING SOON" in small uppercase label, purple-tinted text
- **Body text**: Placeholder copy — "AI-powered safety recommendations based on current conditions, time of day, and your travel patterns — coming soon."
- **Visual treatment**: Muted/dimmed to clearly communicate inactive state:
  - `opacity-50` on the entire card, OR
  - Dashed border instead of solid, OR
  - Diagonal stripe/slash overlay
  - Choose whichever feels most readable while clearly saying "not yet active"

**Data source**: None (static placeholder). Future: `GET /api/briefing?lat=&lng=`

---

## 6. What NOT to Include

These features were in the reference example (`summary_tab_example.html`) but are **explicitly excluded**:

| Feature | Decision | Reason |
|---|---|---|
| Trust Score / Contributor Rank card | **Skip** | User-level metric, already on Profile tab |
| Full filterable incident feed | **Skip** | Feed tab handles this; summary shows top 3-5 only |
| Bottom stats bar (incidents count, uptime, etc.) | **Skip** | Keeps tab focused |
| Time-of-day risk breakdown | **Skip (post-MVP)** | Backend supports it but adds complexity |
| "Generate speech" / action buttons | **Skip** | Not relevant to AlertHood |
| Per-event AI summary | **Skip** | Subset of AI Area Brief; revisit later |
| Upvote/downvote buttons on incidents | **Skip** | Feed tab responsibility; summary only displays counts |

---

## 7. Deliverables

- **Single HTML file**: `design/area_tab/code.html`
- Inline Tailwind via CDN, same format as existing mockups (`design/alerthood_*/code.html`)
- Must include:
  - Fixed **TopBar** (AlertHood logo + notification bell)
  - Updated fixed **BottomNav** with **4 tabs** (MAP, FEED, AREA active, PROFILE)
  - All 6 sections rendered with hardcoded sample data
  - Safety score hero at **65/100 MEDIUM RISK** (amber)
  - Active alert card present (assume there's an active high-severity event)
  - AI brief placeholder in muted/inactive state
- Copy the exact Tailwind `config` block from `design/alerthood_profile_tab/code.html` for color tokens
- Use **Material Symbols Outlined** for all icons
- Fonts via Google Fonts: Space Grotesk (700, 900) + Inter (400, 600, 700)

---

## 8. Technical Reference (for implementation, not design)

### Data Flow
```
User taps AREA tab
  → AreaSummaryPage mounts
  → Browser Geolocation API → lat, lng
  → GET /api/areas/detect?lat=&lng= → area_id
  → Parallel fetches:
      1. GET /api/scores → safety_score, crime_count, score_updated_at
      2. GET /api/events/heatmap?area_id={id}&time_bucket=all → heatmap cells
      3. supabase: events_in_area → recent 5 events (last 48h)
      4. supabase: events in area, severity high/critical, last 24h → active alert
  → Render all sections
```

### New Components Needed

| Component | Purpose |
|---|---|
| `AreaSummaryPage.tsx` | Page wrapper — geolocation, area resolution, data loading |
| `SafetyScoreGauge.tsx` | SVG/conic-gradient circular gauge for safety score |
| `ActiveAlertCard.tsx` | Warning card for high-severity recent events |
| `MiniHeatmap.tsx` | Small read-only Leaflet heatmap of the area |
| `RecentIncidentsList.tsx` | Top 3-5 recent events compact list |
| `AIBriefPlaceholder.tsx` | Static placeholder card for AI brief |

### API Endpoints Used (all existing)

| Endpoint | What it returns |
|---|---|
| `GET /api/areas/detect?lat=&lng=` | Nearest area to user's coordinates |
| `GET /api/scores` | All neighbourhood safety scores |
| `GET /api/events/heatmap?area_id=` | Heatmap grid cells for the area |
| `supabase.rpc('events_in_area')` | Events within area radius |

---

## 9. Post-MVP TODO

- [ ] Area selector/changer within the summary tab
- [ ] Tapping a neighbourhood on the main map opens this tab pre-selected
- [ ] Time-of-day risk breakdown (morning/afternoon/evening/night)
- [ ] Wire up `GET /api/briefing` when backend endpoint is built
- [ ] Replace AI brief placeholder with real AI-generated summary
- [ ] Safe route suggestions ("Safest route to your destination")
- [ ] Business suggestions along safe routes (monetization)
- [ ] Trend indicator (safety improving vs worsening week-over-week)
