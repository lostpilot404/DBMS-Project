# Frontend direction and compliance record

## Product context

This is an educational hospital-administration and operations interface backed by the project's nine-table Oracle schema and Flask API. It supports record management, operational queues, and database-generated reports. It is not a patient portal, clinical decision-support tool, or live hospital service. The browser consumes same-origin Flask endpoints; it never connects directly to Oracle.

## Direction and hierarchy

**Design thesis:** a calm, dependable operations console that makes current work queues easier to scan without making the data feel more certain or more live than it is.

The dashboard first emphasizes four actionable measures supplied by the API: today's active appointment queue, active admissions, available rooms, and pending bills. Supporting register counts and payment-status totals follow. Upcoming appointments, outstanding bills, low-stock medicines, and recent records remain available as operational panels. KPI values are never synthesized in the client; database failure remains an explicit unavailable state. Payment totals are described as bills *marked* paid or pending, not gateway settlements. The dated queue uses status then booked time, and its copy explicitly states that arrival order and triage priority are not recorded.

The other modules remain record-first: task controls and filters lead into semantic, sortable/paginated tables. No trend chart, fabricated activity, patient avatar, testimonial, or unsupported clinical claim is added. Navigation is represented by in-app links with a consistent inline SVG icon set.

## Visual system

- **Typography:** system UI font stack, avoiding an unloaded external font; shared `--type-caption` (12px), `--type-ui` (13px), and `--type-body` (14px) roles, with larger headings for hierarchy.
- **Color:** the existing navy identity remains the structural/navigation color; teal is reserved for primary actions, active navigation, and positive emphasis. Named values distinguish text, warning/error, borders, focus, and surfaces.
- **Spacing and shape:** the bounded `--space-*` scale and role-based control/compact/surface/overlay/pill radii replace scattered values for shared components.
- **Elevation:** surface, toast, and dialog shadows have separate tokens. Surfaces use borders/spacing first; shadows remain restrained.
- **Interaction/motion:** buttons expose hover, focus, pressed, disabled, and loading feedback where applicable; brief motion uses named duration/easing tokens and the reduced-motion media rule.
- **Iconography:** navigation icons are inline SVG with a shared stroke treatment. Decorative icons are hidden from assistive technology; actions keep visible text or a programmatic name. No icon-only navigation is used.

## Responsive and interaction rules

- Desktop keeps a labeled navigation rail. At 820px and below it becomes a drawer with backdrop, synchronized expanded state, Escape/backdrop close, focus containment/return, and an inert closed drawer. A resize back to desktop restores navigation availability.
- A first-focus skip link bypasses repeated navigation. In-app navigation uses links; route changes retain focus in navigation or move it to the new page title as appropriate.
- Dashboard measures and snapshots reduce columns at narrower widths; headings and supporting figures stack where needed.
- Tables preserve their columns inside explicitly named, keyboard-focusable horizontal scroll regions; they do not silently hide data. A narrow-screen hint identifies horizontal scrolling. The appointment agenda reflows event details and actions at 700px and below.
- Dialogs move focus into the open content, contain keyboard traversal, support Escape, and return focus to the trigger when closed. Form hints are associated with their controls; labels, native constraints, and inline error feedback remain in place.
- Focus indicators use teal on light surfaces and pale teal on the dark navigation rail. Input borders and destructive-action boundaries remain identifiable.

## FrontEnd.md compliance matrix

The full supplied acceptance playbook is retained unchanged as [`FrontEnd.md`](FrontEnd.md). This summary separates source-level or mocked evidence from checks that require a real browser or live database.

| Playbook requirement area | Status | Evidence / boundary |
|---|---|---|
| Operating constraints, preserve behavior, and evidence discipline (0) | **Met for this audit** | The Oracle + Flask architecture and nine core entities are retained. Appointment queue/status lifecycle, patient timeline, and CSV export are additive API/UI workflows; no new schema entity was introduced. The unavailable Oracle state is shown honestly; findings below distinguish tests, mocks, and blocked live verification. |
| Product context, user needs, and truthfulness (1, 3, 6) | **Met in source review** | Dashboard and modules use Oracle-backed API values, an operations-first hierarchy, and qualified billing labels. The chart and queue state their limits; no demo values, invented clinical claims, arrival-order claims, or unsupported data are presented. |
| Anti-pattern diagnosis and product-specific design direction (2, 4, 5) | **Reviewed; rendered judgment not evaluated** | Existing operations-console composition was refined rather than replaced. Font, palette, spacing, surfaces, icons, motion, and responsive behavior are documented above. Real-browser visual critique was unavailable. |
| Semantic design tokens and coherent components (5.3) | **Verified in source** | Named color/type/spacing/radius/shadow/motion tokens are declared and referenced; CSS parsed and an undefined-token check passed. Shared controls keep consistent states. |
| Content hierarchy, labels, navigation, and dashboard context (5.4–5.6, 6) | **Verified in source and mocked DOM** | Visible actions, current-route state, metric context, units, loading/empty/error copy, SVG navigation, and database-unavailable messaging are present. Source values remain API-derived. |
| Motion, controls, forms, dialogs, and operational journeys (5.7, 7) | **Partially verified** | 79 mocked API calls exercised the dashboard (including refresh and an unavailable response), all nine module views, all twelve reports, related options, search/sort/pagination/filter queries, one create payload, appointment table/agenda/queue modes and forward lifecycle actions, patient timeline/print interaction, filtered CSV download, and dialog/drawer focus. This is jsdom event/DOM evidence; it does not cover every mutation/error against a real API, Oracle, or rendered browser. |
| Accessibility baseline and WCAG language (8) | **Partial; no conformance claim** | Skip link, semantic navigation, labels, associated hints, keyboard focus management, dialog handling, table regions, and selected contrast pairs were checked. No axe/Lighthouse scan, browser accessibility tree, screen reader, or full manual AT audit was available. |
| Performance, stability, and implementation quality (9) | **Partial** | Existing Flask architecture and dependency set were preserved; no external UI/font dependency was added. JavaScript/CSS parsing and unit tests passed. No performance trace, field metrics, or Core Web Vitals assessment was run. |
| Responsive behavior and content stress (10) | **Partial; rendered layout not evaluated** | Responsive CSS includes 820/700/620/1150px rules, scrollable data tables, stacked forms, and a wrapping agenda. jsdom checked 390px and 1024px drawer state only; it cannot measure layout, zoom, clipping, or device behavior. |
| Browser screenshot, console/network, and real-journey QA (11–14) | **Blocked / not evaluated** | No browser engine was installed. HTTP requests confirmed static assets, but browser console, actual screenshots, rendered visual states, and real-browser journeys were not inspected. The supplied playbook is preserved for follow-up. |
| Playbook prompt templates and meta-instructions (15–18) | **Not applicable as product features** | These are instructions for an agent, not UI acceptance criteria. Applicable design, implementation, verification, and reporting requirements are recorded in this audit. |
| Honest acceptance reporting and task-specific constraints (19–21) | **Documented** | Actual commands/results and limitations are in the README and this matrix; no skipped test or unavailable tool is represented as a pass. |

## Measured evidence and limitations

Selected color pairs were calculated from CSS source colors: muted text on white 5.65:1 and on the light canvas 5.30:1; teal links on white 4.96:1; the focus teal on white 6.17:1 and on the canvas 5.78:1; navigation secondary text on navy 4.65:1; warning, error, and positive status text on their surfaces 6.12:1, 4.99:1, and 4.92:1; input-border contrast against white 3.52:1; and the pale sidebar focus color against the two navy endpoints 7.64:1 and 9.17:1. These are selected source-color calculations, not a complete contrast audit.

Automated and mocked evidence is recorded in the [README verification section](../README.md#verification-and-tests). A Flask test-client check returned `/`, CSS, JavaScript, and favicon with HTTP 200; without Oracle configuration, `/api/health` and `/api/dashboard` returned structured HTTP 503 `database_unavailable` responses. No live Oracle instance or real-browser engine was used. Real rendered composition, a full viewport/zoom matrix, browser console/network inspection, screen-reader behavior, and complete WCAG 2.2 AA conformance remain unverified.
