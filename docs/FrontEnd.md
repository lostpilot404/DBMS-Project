---
title: "AI Website Design & Engineering: Iceberg Playbook + Agent Execution Specification"
version: "1.0"
status: "Reusable operating document"
research_date: "2026-10-27"
intended_audience:
  - AI coding agents
  - Frontend engineers
  - Product designers
  - Technical reviewers
primary_use: "Give this single Markdown file to an AI coding agent and instruct it to improve or build a website in the current repository."
---

# AI Website Design & Engineering
## Iceberg Playbook + Master Execution Prompt

> **Purpose:** Use this document as both (1) a design and engineering playbook and (2) an execution specification for an AI coding agent. The target is a website that is distinctive for its actual product, visually coherent, usable, accessible, responsive, functional, credible, and verified in a browser—not merely a page with different colors or less obvious AI clichés.

**Instructions to the receiving AI:** Read this document before making substantial changes. Follow the **Master Execution Prompt** near the end. Use the rest of this document as the reference standard. Inspect the actual project; do not assume its stack, structure, state, or requirements from this document alone.

---

# 0. Operating contract for the AI agent

## 0.1 What successful completion means

Do not stop at a critique, strategy, mockup, code snippet, or list of recommendations. In the current environment, make the relevant changes to the actual project, run the application where possible, inspect the rendered result, test important interactions, correct the defects found, and report verified outcomes and remaining limitations.

A result is complete only when the appropriate gates below have been evaluated:

1. **Product fit:** The interface reflects the actual audience, job, content, domain, and constraints.
2. **Design intent:** Color, type, layout, surfaces, imagery, and motion are deliberate rather than arbitrary defaults.
3. **Information quality:** Content is specific, truthful, well organized, and understandable.
4. **Functional completeness:** Controls perform the action their labels and appearance promise; major states are implemented.
5. **Responsive integrity:** Layouts remain understandable and usable at narrow, intermediate, and wide widths.
6. **Accessibility:** Applicable accessibility requirements have been checked using both automated and manual methods.
7. **Technical quality:** Existing architecture is respected; relevant tests, builds, browser checks, and performance investigations are run where feasible.
8. **Visual verification:** Actual screenshots/rendered views are inspected, defects are recorded specifically, and fixes are rechecked.
9. **Honest reporting:** The final report distinguishes verified facts, inferred findings, untested areas, and blockers.

## 0.2 Instruction priority

Resolve conflicts in this order:

1. Applicable safety, security, privacy, legal, and platform constraints.
2. Explicit user requirements and project acceptance criteria.
3. Existing product behavior, data contracts, architecture, and documented invariants that must be preserved.
4. Verified content and domain facts; never invent product features, results, endorsements, numbers, users, or evidence.
5. Applicable standards, especially accessibility and browser/platform requirements.
6. The product-specific design brief and existing brand system.
7. This playbook's design and engineering heuristics.
8. Personal taste or trend preferences.

If the repository contains a real design system or brand guide, inspect it and extend it rather than replacing it without cause. If the user's brief deliberately asks for a style that appears in the anti-pattern list, follow the brief and preserve accessibility and usability.

## 0.3 Normative language

- **MUST / MUST NOT:** A hard project constraint, verified factual safeguard, or applicable requirement that must be satisfied.
- **SHOULD / SHOULD NOT:** A high-value default; depart only with a reason tied to the product, audience, or evidence.
- **MAY:** An optional technique, style, or experiment.
- **HEURISTIC:** A clue that helps diagnose a problem; it is not automatically a defect.
- **SUBJECTIVE:** A matter of taste that should be resolved against a brief, reference, or review preference—not presented as objective fact.

Do not convert every heuristic in this document into a rigid rule. The goal is coherent judgment, not a new template made from anti-template rules.

## 0.4 Safe repository behavior

Before editing:

- Inspect the repository instructions, project documentation, framework/package manifests, routes, components, assets, test commands, and current implementation.
- Inspect the working tree and current changes when Git is available. Do not overwrite or discard user changes.
- Identify which pages and features are in scope. Preserve working behavior unless the requested change requires modifying it.
- Avoid unrelated rewrites, framework migrations, broad dependency changes, data migrations, destructive shell commands, or new paid services unless required and authorized.
- Use existing tools first. Do not claim browser verification if no browser actually ran. Do not silently install a large or risky dependency simply to perform an optional check.
- If something essential is missing, infer the safest reasonable default from the repository and explain it. Ask a concise clarifying question only when a material decision cannot be safely inferred and would change the solution.

## 0.5 Evidence discipline

For every significant finding, distinguish:

- **Observed:** Visible in code, a live page, a screenshot, a test result, or a source document.
- **Measured:** Confirmed with a tool or calculation—for example, a contrast ratio, viewport width, failing test, or response metric.
- **Inferred:** Strongly suggested by evidence but not directly confirmed.
- **Not evaluated:** The required source, tool, state, credential, device, or environment was unavailable.

A screenshot can suggest contrast trouble; it cannot reliably prove a WCAG contrast failure unless the relevant colors and conditions are measured. A successful build does not prove a feature works in a browser. A detector score does not prove that a design is beautiful.

---

# 1. The iceberg model: what an “AI-looking” website actually is

## 1.1 The surface problem

The visible symptoms commonly include predictable gradients, a centered hero, generic feature cards, the same rounded corners everywhere, vague marketing copy, decorative icons, repeated entrance animations, and fake-looking imagery. These are useful clues, but individually they are not proof of poor design or AI authorship.

## 1.2 The underlying problem

A generative model can produce plausible code and familiar layouts without possessing a complete brief, real user research, a reliable design memory, or direct feedback from the actual rendered page. When the brief leaves many choices unspecified, the agent often fills the gaps with familiar patterns. Common component libraries can accelerate this convergence if their defaults are left unexamined.

This is a **practitioner explanation of observed behavior**, not a claim that every model or every generic-looking website has one identical technical cause. The actionable conclusion is robust: give the agent enough product truth, bounded design freedom, real content, clear constraints, and a screenshot-based feedback loop.

## 1.3 The iceberg layers

| Layer | What goes wrong | What the agent must do |
|---|---|---|
| 1. Styling | Familiar fonts, colors, radii, shadows, gradients | Make a context-specific visual system instead of swapping one default palette for another |
| 2. Composition | The same hero, card grid, testimonials and CTA sequence | Organize the page around audience questions, tasks and content hierarchy |
| 3. Information architecture | Sections are present because templates expect them | Decide what belongs, what order it belongs in, and what should be removed |
| 4. Content | Copy fills space but says little; claims are fabricated | Use verified, specific content and truthful examples |
| 5. Interaction | Controls are decorative or states are missing | Complete the interaction contract, including errors, loading, empty and success states |
| 6. Product fit | The interface looks like a marketing page even when the work is an operational app | Use patterns appropriate to persuade, read, explore, operate, or transact |
| 7. Design-system integrity | Styles drift between components and pages | Create or reuse semantic tokens and enforce consistent component behavior |
| 8. Responsive behavior | Desktop composition collapses, content clips, action targets become inaccessible | Test real rendered layouts across widths and content variations |
| 9. Accessibility | Low contrast, missing labels, poor focus, motion problems | Apply WCAG requirements and manual keyboard/assistive-technology-oriented checks |
| 10. Technical quality | Layout shifts, slow assets, brittle code, console failures | Inspect performance, error states, semantics, build/tests and browser behavior |
| 11. Verification | The agent assumes its code looks right because it compiled | Render pages, inspect screenshots, measure where possible, fix and recheck |
| 12. Learning | Each new prompt forgets previous design decisions | Store durable product facts, design rules, exceptions and verified QA findings in project documentation when useful |

**Core rule:** Improve the causes, not merely the symptoms. Changing a purple gradient to a beige gradient is a cosmetic substitution, not a design strategy.

---

# 2. AI-look anti-pattern taxonomy

Use this section as a diagnostic inventory. A pattern should be reported as a defect only when its use is unjustified, repeated in a way that flattens hierarchy, conflicts with the brief, harms usability, or creates measurable quality problems.

## 2.1 Visual styling patterns

| Pattern / tell | Why it can feel generic | Better action | False-positive warning |
|---|---|---|---|
| Purple/blue/indigo gradient hero by reflex | It can signal a copied SaaS template rather than a product-specific choice | Use the palette derived from the brand and subject; use a gradient only if it adds meaning or composition | Gradients and purple are valid brand choices |
| Cream background + serif headline + terracotta accent by reflex | It is an alternative cliché, not inherently more original | Derive colors and typography from the product's intended character and content | Editorial and warm palettes can be exactly right |
| Near-black background + acid green, cyan or vermilion glow | “Technical” appearance substituted for a considered theme | Establish readable semantic colors and restrained surface/elevation rules | Dark mode is appropriate for many products, particularly when users prefer it or the brand requires it |
| Inter, Roboto, Arial, system fonts or Space Grotesk chosen without consideration | The typeface becomes a default rather than a designed decision | Pick one or two families appropriate to the product; make roles, scale, line length and weights intentional | A familiar sans-serif can be the best choice for dense UI and legibility |
| One word in a headline randomly italicized or recolored | Artificial emphasis that does not correspond to the message | Emphasize via sentence structure, scale, weight or a justified highlight | A carefully art-directed accent can be legitimate when it supports meaning |
| All-caps eyebrow labels above every heading | Decorative chrome is repeated independently of information needs | Use labels only when they convey category, status or helpful context | Editorial metadata and small caps are not inherently wrong |
| Monospace type on every tiny label to signal “technical” | Genre shorthand replaces actual hierarchy or readability | Reserve monospaced type for code, identifiers or tabular data where it helps | A technical brand may intentionally use monospace more broadly |
| Every element has the same 16–24px radius | Components lose role-based shape hierarchy | Define radii by role: e.g. controls, small surfaces, large surfaces, pills—only as needed | A soft, rounded brand system can be coherent when deliberate |
| The same soft shadow under every card | Elevation fails to communicate actual relationships | Use borders, surface contrast, spacing and elevation sparingly and consistently | A deliberate card system is valid for interactive objects or grouped content |
| Everything is a card, including headings and form fields | Container chrome competes with content; visual nesting becomes noisy | Remove unnecessary containers; use spacing, dividers and typography to group information | Independent records and panels often need clear boundaries |
| Colored icon tile above every section | Repeated icon decoration becomes a template signature | Use icons only when they aid recognition or scanning; use one consistent family | Icon tiles can support navigation or recognizable feature groups |
| Emoji used as the primary icon system | Style, rendering and meaning can vary by platform; icons often look informal | Use a coherent icon set or plain text labels | Emoji can be correct in playful products or user-generated content |
| Random blobs, glassmorphism, neon, gradient text and ambient particles | Effects add surface noise without improving meaning | Keep effects that communicate depth, state or brand; remove the rest | Visual effects may be central to art direction or a creative product |
| Decorative 01 / 02 / 03 labels | Numbering implies a sequence that may not exist | Number true steps, timelines or ranked structures only | Numbered indexes are useful in long structured content |
| Arrows appended to every button or link | Uniform decoration takes focus from action labels | Use arrows only when the direction or destination matters | A consistent arrow language can be useful for navigation |
| Every section has identical padding, height and alignment | The page has no rhythm or meaningful hierarchy | Use a common spacing scale but vary composition to fit content roles | Consistent alignment and spacing are good; arbitrary variation is not |

## 2.2 Structure and information architecture patterns

1. **The automatic SaaS landing page:** centered hero → logo strip → three feature cards → stats → testimonials → pricing → CTA, regardless of what the product does.
2. **The repeated three-column feature grid:** all features are forced into equal cards even when the content has different importance, complexity or media needs.
3. **The all-centered page:** body copy, forms, data, navigation and long text are centered because the model never selects an alignment system.
4. **The one-size-fits-all dashboard:** giant headline metrics, colored tiles and tiny decorative sparklines appear before the agent has identified the actual operational tasks.
5. **The card-in-card pattern:** the outer card, inner card and nested panel all have independent padding, radius and shadow without a meaningful hierarchy.
6. **The endless full-width scroll:** every concept becomes another oversized section with the same composition; important actions and information are buried.
7. **The bento grid for its own sake:** irregular tile sizes are used for visual fashion even when reading order, comparability or content does not justify them.
8. **The fake hierarchy:** labels, badges, accent borders, decorative rules and tiny metadata all compete with the true primary heading or action.
9. **The missing hierarchy:** all buttons look primary, or every metric has the same weight; users cannot distinguish what is important.
10. **The over-minimal task screen:** important context, filters, labels, undo, status, help or confirmation is deleted in the name of a clean look.
11. **The over-dense task screen:** data is compressed into small type and tight spacing without prioritizing frequently used actions, key comparisons or error prevention.
12. **The layout copied between incompatible page types:** a marketing card is reused for every settings panel, a form is represented as a table, or a long article is forced into dashboard-like tiles.

**Correction method:** Name the page's user task and content hierarchy first. Then choose the structure. Do not start from a preselected component pattern and force the content into it.

## 2.3 Copy and content patterns

Watch for:

- Vague slogans such as “unlock your potential,” “the future of work,” “revolutionize your workflow,” “seamless experience,” “all-in-one platform,” “cutting-edge,” or “best-in-class” when they are not grounded in specifics.
- A headline that a direct competitor could use unchanged.
- Feature descriptions that repeat the same promise with different nouns.
- Fake statistics, customer counts, reviews, partner logos, awards, security claims or testimonials.
- Fake product screenshots or charts whose data is impossible, inconsistent or disconnected from the application's functionality.
- Placeholder-looking personas, generic stock-team stories, invented names and fabricated case studies.
- Button labels such as “Submit” or “Continue” when the user needs a more specific action label, or hyper-clever labels that obscure what happens.
- System-centric wording where users need task language (for example, internal implementation terminology instead of the outcome users recognize).
- Empty success messages (“Success!”) or vague errors (“Something went wrong”) without useful next steps.
- Copy that changes tone across routes because each page was generated from a separate prompt.
- Accessibility text that says “image,” “screenshot” or “hero image” rather than describing the meaningful content—or unnecessary alt text on purely decorative images.

**Corrective rules:**

1. Treat provided product facts and source content as the source of truth.
2. Mark fabricated demonstration data as sample/demo data when the product genuinely needs it.
3. Never invent endorsements, security certifications, customer metrics or business results.
4. Replace generic copy with specific capabilities, scope, conditions and user outcomes.
5. Use errors that explain what happened, what field or operation is affected, and how the user can recover—without leaking secrets or internal stack traces.
6. If a necessary claim cannot be verified, omit it, qualify it, or mark it for owner confirmation instead of presenting it as fact.

## 2.4 Imagery and visual asset patterns

- Generic stock imagery whose only purpose is to fill empty space.
- Synthetic people, hands, devices, interfaces or lighting that look implausible in the context.
- Multiple illustration styles mixed on the same page because images came from different prompts or sources.
- Text baked into generated images, including misspelled or garbled pseudo-copy.
- Fake UI screenshots used to suggest working features that do not exist.
- Decorative diagrams and charts that do not explain actual content.
- Images without explicit dimensions or suitable aspect-ratio behavior, causing layout shifts or awkward crops.
- Heavy imagery loaded at full resolution when a smaller responsive asset is appropriate.

**Corrective rules:** Prefer genuine product screenshots, truthful photography, carefully art-directed illustrations, or meaningful data visualizations. Use generated art only if it fits the brief and can be checked for visual defects and rights/usage constraints. Optimize assets, preserve the intended crop, define dimensions/aspect ratios, and write meaningful alt text when the image conveys content.

## 2.5 Motion and interaction patterns

- Every section fades/slides into view on scroll.
- Every card lifts on hover, even when it is not interactive.
- Floating particles, parallax, cursor followers, fake terminal animations, count-up metrics or glow effects are used to imply sophistication without serving a real purpose.
- Controls lack hover/focus/pressed/disabled/loading/selected states where applicable.
- A button appears interactive but has no behavior.
- A link is implemented as a button or a button as a link without a reason.
- A disabled action gives no explanation when users need to know what prevents progress.
- A form silently fails, clears user input unexpectedly, or shows validation only after all information is lost.
- A loading screen or skeleton remains indefinitely; a spinner is used when meaningful progress can be shown; an operation has no success confirmation.
- A dialog has no visible close or cancel path, keyboard focus behavior, or sensible return-focus behavior.
- Interaction depends on hover and therefore fails on touch or keyboard-only input.

**Corrective rules:** Animation should express state change, provide feedback, or support a clear narrative. Nonessential motion should be reduced or removed when the user prefers reduced motion. Every actionable control needs a meaningful action and appropriate states. The user should retain context and recover safely from errors.

## 2.6 Signs that the issue is deeper than visual taste

Report these as concrete usability or engineering defects when verified:

- Broken routes, stale content, incorrect active navigation, dead links, or buttons that do nothing.
- Layout overflow, clipped or overlapping text, hidden controls, broken tables, unusable dialogs, or sticky headers obscuring focused elements.
- Inconsistent data labels, incorrect totals, fake records, charts contradicting tables, or different pages showing different values for the same fact.
- Missing loading/empty/error states and inaccessible feedback.
- Low measured contrast, missing accessible names, broken keyboard navigation, invalid heading/landmark structure, or form errors not programmatically associated.
- Unoptimized image delivery, visible layout shifts, slow blocking scripts, unbounded animation or large unused bundles.
- Inconsistent tokens, page-to-page drift, one-off CSS overrides, or component variants that cancel one another.
- Broken browser console, runtime errors, failed requests, or test failures introduced by the changes.

---

# 3. Do not overcorrect: false positives and contextual design judgment

Anti-pattern lists are diagnostic. They are not universal design laws. Anthropic's own frontend-design guidance warns that familiar anti-AI rules can themselves become a new template if agents automatically replace one style with another.

| Element | Weak rule | Better rule |
|---|---|---|
| Inter / system sans | “Never use Inter.” | Select a typeface based on brand, legibility, language support, data density and product context. The issue is unexamined defaulting and weak hierarchy. |
| Purple or blue | “Never use purple.” | Use colors because they belong to the product's visual logic. Avoid an unmotivated default gradient. |
| Cream + serif / acid green + black | “These are forbidden.” | They are potential new clichés; use them only when appropriate and art-directed. |
| Cards | “Never use cards.” | Use cards for independent objects, actionable content or meaningful grouping. Avoid unnecessary and nested card chrome. |
| Rounded corners | “Always use 4px radius.” | Choose radii by product character and component role. Consistency matters more than a universal number. |
| Symmetry / centered composition | “Everything must be asymmetric and left aligned.” | Choose alignment from content, hierarchy, reading direction and intended composition. |
| Dark mode | “Dark mode is AI slop.” | Dark mode may be required by brand or work context. Verify text, control, data-visualization and focus contrast. |
| Animations | “Remove all motion.” | Keep useful, performant, accessible motion; remove motion that distracts, delays or communicates nothing. |
| Minimalism | “Use fewer elements at all costs.” | Remove nonessential competition, but keep useful context, status, task aids and safety information. |
| Unconventional layouts | “Distinctive means unusual.” | Use novelty only when it improves meaning or brand character. Familiar, predictable structures are often better for task-critical UI. |
| Component libraries | “Never use shadcn or common libraries.” | Use good primitives where useful. Customize the token system, composition, density and states rather than blindly shipping defaults. |
| Data density | “Make everything spacious.” | Use density appropriate to task frequency, comparison work, user expertise and screen size. Dense UIs can be clear when hierarchically organized. |

**Review test:** If a new design is simply “the same template, but with another palette, font, rounded-corner value, or trendy effect,” the underlying problem has not been solved.

---

# 4. Establish product truth before choosing the style

## 4.1 Product modes

Classify each page or flow by its dominant job. A multi-page product can use more than one mode.

| Mode | Primary user goal | Design priority | Common appropriate patterns |
|---|---|---|---|
| **Persuade** | Understand a product or offer and decide whether to act | Clear value, credibility, proof, clear next step | Editorial narrative, product demo, relevant imagery, comparison, testimonials only when real |
| **Operate** | Monitor, manage or act on a system | Efficiency, status, precision, fast scanning | Tables, filters, queues, compact controls, clearly ranked metrics, stable layouts |
| **Create / Configure** | Set up, edit, design or author something | Control, preview, reversible changes, clear settings | Form sections, side panels, inline editing, previews, draft/save/publish states |
| **Read / Learn** | Understand complex material | Readability, navigation, findability and context | Reading column, explicit headings, table of contents, code blocks, diagrams where explanatory |
| **Explore / Discover** | Browse, compare or investigate | Orientation, filtering, useful previews and progressive disclosure | Search, categories, galleries, maps, comparison views, useful sorting |
| **Transact** | Purchase, book, submit or confirm a consequential action | Confidence, error prevention, clear totals and recovery | Focused step flow, transparent validation, clear summary, progress and confirmation |
| **Showcase / Portfolio** | Understand the creator's work and evaluate evidence | Strong narrative, authentic artefacts, distinctive art direction | Case studies, large project imagery, editorial structure, detailed outcomes |

Do not impose landing-page design onto an operational application. A dashboard should not become a collection of marketing tiles; a form should not become a portfolio composition; a documentation page should not be burdened with decorative interactions.

## 4.2 Product discovery template

Create or update `PRODUCT.md` when the repository or project would benefit from persistent context. In a tiny one-off task, record the answers in the implementation plan instead of adding unnecessary documentation.

```markdown
# PRODUCT.md

## Product definition
- Product / project:
- Category:
- What it does in one sentence:
- Primary user and secondary users:
- Primary job-to-be-done:
- Main user journeys:
- Success criteria:

## Usage context
- Typical frequency and time pressure:
- User expertise:
- Primary device/input methods:
- Accessibility / language / locale needs:
- Environmental constraints (e.g. bright room, low bandwidth, shared workstation):

## Truth and trust
- Verified capabilities:
- Verified claims and source of truth:
- Data sensitivity / security constraints:
- Claims or assets that must not be invented:
- Known domain terminology:

## Product surface
- Page / flow type: Persuade / Operate / Create / Read / Explore / Transact / Showcase
- Most important first-screen information:
- Primary action:
- Secondary action(s):
- High-risk or irreversible actions:
- Required states:

## Constraints
- Framework / runtime / existing architecture:
- Existing brand and design-system rules:
- Supported browsers / viewport range:
- Required integrations / APIs:
- Out of scope:

## Visual intent
- Desired personality (3–5 concrete traits):
- What it must NOT feel like:
- References and the specific principles to learn from:
- Anti-references and the actual reasons to avoid them:

## Open questions and assumptions
- Assumption:
- Reason:
- Risk if wrong:
- Resolution method:
```

### Discovery rules

- Read project documentation and existing content before asking for facts already present.
- Use a small number of meaningful reference sites. Extract principles—hierarchy, content sequence, visual density, typography, interaction models—not a clone of another brand.
- Never infer proof of a capability from a decorative screenshot. Confirm the feature in the implementation or product specification.
- Use assumptions for low-risk missing details and record them. If a missing fact changes security, data integrity, billing, irreversible actions, or a core user journey, do not silently invent it.

---

# 5. Create a design direction and system—not random styling

## 5.1 The design direction brief

Before extensive UI changes, specify:

1. **Visual thesis:** one or two sentences describing the page's character and why it fits the product.
2. **Hierarchy:** the first thing users should notice, the second, and the primary action.
3. **Composition:** the layout concept and why it supports the content.
4. **Typography:** family choices and the roles the type system must express.
5. **Color logic:** base palette, semantic colors and what the accent is allowed to mean.
6. **Surface logic:** where borders, backgrounds, shadows and radii indicate grouping or interaction.
7. **Imagery/art direction:** actual assets, screenshot treatment, illustration style, crop and aspect ratios.
8. **Motion:** what moves, why it moves, when it moves and how reduced motion changes it.
9. **Constraints:** accessibility, responsiveness, existing code, data density, performance and supported functionality.
10. **Anti-default review:** which choices are common AI defaults, whether any are justified here, and what was chosen deliberately instead.

The agent should assess whether the direction is specific to this product. A useful test is: **Could this same exact design description be reused for a completely different product without changing anything?** If yes, it is probably under-specified.

When there are several materially different directions and the user has not supplied a preference, the agent can compare up to three concise options. If operating autonomously, select the best supported direction, record the rationale, and proceed rather than waiting for unnecessary approval.

## 5.2 Design system template

Create or update `DESIGN.md` when a multi-page project needs durable decisions. This file should describe the system, not blindly enforce the example values below.

```markdown
# DESIGN.md

## Direction
- Design thesis:
- Desired personality:
- Core hierarchy rule:
- Core composition rule:
- What makes this product visually specific:

## Tokens
- Color tokens by semantic role:
- Typography tokens by role:
- Spacing scale:
- Content widths / grid:
- Radius tokens:
- Border / elevation tokens:
- Motion tokens:
- Focus / selected / error / success states:
- Light / dark themes, if supported:

## Component behavior
- Buttons and link hierarchy:
- Fields and validation:
- Cards / panels / tables:
- Navigation and active states:
- Dialog / popover behavior:
- Loading / empty / error / success states:

## Responsive rules
- Content-driven breakpoint rules:
- Mobile navigation:
- Data/table behavior:
- Touch-target policy:
- Long-content and text-zoom behavior:

## Accessibility / performance
- Target standard and exceptions:
- Reduced-motion behavior:
- Asset and font-loading policy:
- Tested browsers / viewport matrix:

## Explicit exceptions
- Token or component exception:
- Why needed:
- Which pages/components use it:
- How to verify consistency:
```

## 5.3 Semantic tokens

Use named tokens that explain purpose rather than unexplained literals scattered through the CSS. Common examples include:

- **Color:** `canvas`, `surface`, `surface-raised`, `text-primary`, `text-secondary`, `border-subtle`, `action-primary`, `action-primary-text`, `focus-ring`, `success`, `warning`, `danger`.
- **Typography:** `display`, `heading-1`, `heading-2`, `body`, `body-small`, `label`, `caption`, `code`, with explicit size/line-height/weight roles.
- **Spacing:** `space-1` through `space-n` from a bounded scale appropriate to the project.
- **Shape:** `radius-control`, `radius-surface`, `radius-overlay`, `radius-pill` only if each role is required.
- **Elevation:** `shadow-popover`, `shadow-dialog` or role-based equivalents; most sections do not need a shadow.
- **Motion:** named durations and easing curves based on interaction type, with a reduced-motion policy.

A 4px or 8px base spacing scale can be a useful starting point, not a law. A modular typography scale can help establish hierarchy, but no single ratio or font-size set is correct for every product. Define a compact system, inspect it in the real content and adjust based on legibility and composition. The USWDS explains the purpose of design tokens as a controlled set of values for typography, color, spacing and other style choices: [USWDS Design Tokens](https://designsystem.digital.gov/design-tokens/).

Use the CSS color representation that the stack supports and the project can maintain. OKLCH can be useful for perceptual color manipulation; it is not mandatory. Do not require all values to use one syntax if the current project or target browser compatibility argues otherwise.

## 5.4 Typography and content layout

- Assign typefaces roles intentionally. One well-used family can outperform a poorly matched pair.
- Define a visual type hierarchy using size, weight, line-height, width and spacing—not color alone.
- Prevent display type from causing awkward line breaks, overlap or mobile overflow.
- Keep long-form reading lines comfortable and preserve paragraph separation.
- Avoid fake hierarchy produced by all-caps labels, tiny metadata or arbitrary letter spacing.
- Keep consistent body text and labels across equivalent components.
- Test with the longest realistic headings, labels, localized strings, numeric values and error messages.
- Do not truncate important information without a disclosure or inspection path.
- Sentence case is a strong default for utility interfaces; follow established brand conventions where appropriate.

Nielsen Norman Group's visual-design guidance emphasizes hierarchy, typography, grid alignment and consistent spacing as components of attractive, usable interfaces: [Why Does a Design Look Good?](https://www.nngroup.com/articles/why-does-design-look-good/) and [Visual Hierarchy in UX](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/).

## 5.5 Color and surface rules

- Pick a dominant palette and a restrained accent system based on the brand and user context.
- Use semantic color roles. Error, warning, success, selected and disabled states must be distinguishable and must not rely on hue alone.
- Maintain sufficient text and non-text contrast for applicable WCAG criteria.
- Check the palette in all supported themes and behind every actual surface—especially tinted cards, gradients, translucent panels and data visualizations.
- Avoid mixing neutral palettes that produce accidental undertones unless the combination is deliberate.
- Use whitespace, borders and background contrast before defaulting to elevation.
- Treat radius, shadows, line rules and icon containers as hierarchy tools, not mandatory decoration.
- Ensure that visible boundaries for input controls and essential chart graphics remain identifiable.

## 5.6 Iconography and imagery

- Prefer one coherent icon family and consistent stroke/fill behavior.
- Use text labels where icons would be ambiguous. For icon-only controls, provide an appropriate accessible name and tooltip where useful.
- Do not use decorative symbols as the sole indication of status or meaning.
- Use real product images and real facts whenever available.
- Keep illustration composition, lighting, stroke, palette and texture consistent on the page.
- Include source/license/permission notes where required by the project; do not assume that an image found online is free to reuse.
- Use `width`/`height`, `aspect-ratio`, responsive images and appropriate formats to avoid avoidable shifting and oversized downloads.

## 5.7 Motion and interaction design

For every planned animation, record its purpose: **feedback, orientation, continuity, hierarchy, or brand expression**. If it serves none of those purposes, remove it.

- Use a short, coherent motion vocabulary rather than unrelated transitions.
- Prefer animation of `transform` and `opacity` where suitable; avoid expensive repeated animation of layout properties without a strong reason.
- Keep critical content visible and usable when animation fails, is delayed, or is disabled.
- Do not hide all content until a scroll-trigger animation fires.
- Respect `prefers-reduced-motion`; remove or replace nonessential movement in the reduced-motion mode.
- Hover cannot be the only way to discover or activate a function.
- Make the difference between interactive and static content perceptible.

See W3C's [Animation from Interactions guidance](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html) (WCAG 2.3.3 is Level AAA) and MDN's [`prefers-reduced-motion`](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion) documentation. Supporting reduced motion is a strong default; do not mislabel an AAA criterion as an AA requirement.

---

# 6. Requirements by product type

## 6.1 Marketing / landing pages

**Primary job:** Help a target visitor understand the offer, assess evidence, resolve concerns, and take a next step.

- Open with the most specific product proposition—not a universal slogan.
- Keep a visible hierarchy between core proposition, supporting proof and action.
- Put relevant evidence near the claim it supports. Evidence may be product screenshots, a verified demonstration, real customer quotations, documented results, or a concise explanation of how the service works.
- Structure sections in the order that answers likely user questions. Do not insert testimonial strips, pricing cards, logo bars, FAQs or statistics merely because templates include them.
- Keep primary and secondary conversion paths distinct.
- Avoid popups and overlays that interrupt the core task without a clear need.
- Use actual assets and factual product descriptions; do not simulate an established brand with fabricated logos or user counts.
- Test navigation, CTA destinations, form submission, mobile hero height, long copy, footer content and page depth.
- Use expressive motion only where it supports storytelling or interaction and does not impede content access.

## 6.2 Dashboards and analytics

**Primary job:** Help users understand current conditions, detect issues, compare values and act.

- Begin with the actual operational questions; do not manufacture a row of big-number cards if a queue, table or exception list is more useful.
- Distinguish observed data, derived metrics, estimates and empty/no-data states.
- Label units, time range, comparison baseline, data freshness and aggregation when they affect interpretation.
- Charts must faithfully represent supplied data. Do not invent a sparkline solely to make a metric tile look technical.
- Use tables for tasks such as finding, sorting, comparing, editing or acting on records. Use cards when grouped summary objects provide a real benefit.
- Make filter state, sort order, pagination, selected rows and bulk actions visible.
- Provide loading, no results, no data, stale data, permission-denied, partial-error and successful-refresh behavior where applicable.
- Use restrained motion. Numerical changes should not create distracting constant count-up effects.
- Design for repeated, efficient use: clear active navigation, predictable control placement, keyboard access and deliberate data density.

NN/g's research on [Data Tables](https://www.nngroup.com/articles/data-tables/) discusses user needs such as finding records, comparing data, editing row values and taking actions. The appropriate pattern should follow those tasks, not aesthetics alone.

## 6.3 CRUD / administrative / enterprise systems

**Primary job:** Complete operations accurately, prevent mistakes and make recovery possible.

- Use task-oriented forms, readable tables, clear status indicators and explicit primary actions.
- Put field labels outside placeholder text; placeholders are not a replacement for labels.
- Explain requirements before submission when the rule is not obvious. Associate field errors with the relevant fields.
- Preserve entered data after validation or recoverable server errors.
- Confirm destructive or irreversible actions and explain the scope of the action.
- Provide undo or a recovery path where appropriate.
- Make permissions and disabled states understandable without exposing sensitive implementation details.
- Avoid modal dialogs for every edit. Choose inline editing, a side panel, a dedicated form or a dialog based on task complexity, focus requirements and need for context.
- Keep tables scannable and usable; provide responsive alternatives when horizontal comparison cannot fit a phone screen.
- Treat database constraints, money, dates, identity, audit trails and concurrency as functional invariants—not decorative details.
- Use realistic sample data only when actual records are unavailable, and label it as sample data.

## 6.4 Documentation, blogs and content sites

- Optimize for reading, navigation, search and reference.
- Establish a predictable heading hierarchy, table of contents where valuable, visible links, citation/source conventions, code formatting and a comfortable reading column.
- Keep recurring article/page templates consistent while allowing different content types to use suitable structures.
- Avoid turning every paragraph, quote or resource into a large card.
- Preserve search, pagination, code copy, anchors, related links and metadata where they are part of existing behavior.
- Do not use animation that interrupts reading or obscures the content.

## 6.5 Portfolios, showcases and creative experiences

- Let real work be the primary evidence. Include project context, contribution, constraints, process, artifacts and outcomes where available.
- Use an intentional art direction to create personality, but keep navigation and case-study reading understandable.
- Make experiments legible and usable on touch devices and with reduced motion.
- Do not invent client details, project outcomes, authorship or private information.
- Add novel interactions only when the result is understandable and improves the experience.

## 6.6 E-commerce and transactions

- Present product details, price, availability, variant selection, shipping/fees, returns and other purchase-relevant information honestly.
- Keep the user's current choice and total visible where they are needed for the decision.
- Avoid fake urgency, invented reviews, false scarcity, confusing consent patterns or hidden costs.
- Make errors actionable and do not wipe form state after an error.
- Use trust signals only when genuine and relevant to the decision point.
- Make keyboard operation, focus behavior, privacy and secure handling of customer information part of the design.

---

# 7. Functional completeness: the interaction contract

## 7.1 State inventory

For each interactive component, determine which states are applicable and implement/test them. Not every component requires every state, but the agent must decide rather than omit them by default.

| Component | State(s) to consider |
|---|---|
| Button / action | Default, hover if pointer supports it, keyboard focus, pressed, disabled, loading, success or resulting state |
| Text field | Empty, focused, filled, valid, invalid, disabled/read-only where used, helper text, error text |
| Form | Pristine, editing, submitting, validation failure, server failure, success, retry/recovery |
| Data table | Loading, populated, sorted, filtered, no results, no data, error, pagination/end, row selected, bulk action, responsive overflow/alternative |
| Search | Empty, typing, results, no results, loading, error, clear, keyboard navigation if autocomplete is present |
| Dialog / drawer | Open, close/cancel, focus entry, focus containment where required, escape behavior where appropriate, return focus, validation/error |
| Tabs / navigation | Default, active, focus, selected route/panel, direct URL/deep-link behavior when applicable |
| Async operation | Start, pending, progress when known, success, failure, retry/cancel if supported, timeout behavior |
| Chart / data visualization | Loading, no data, unavailable data, populated, legend/series visibility, labels/units, accessible alternative where needed |
| Upload / import / export | Idle, selecting, validating, uploading/processing, success, partial success if supported, failure and recoverable retry |

Nielsen Norman Group's [Button States: Communicate Interaction](https://www.nngroup.com/articles/button-states-communicate-interaction/) describes how button states signal operability and feedback. Do not confuse a component's visual style with its interaction state.

## 7.2 Behavior contract

For each action, the code and interface must answer:

- What exactly happens when it is activated?
- What data or state changes?
- What happens if the input is invalid, permission is missing, or the operation fails?
- What feedback does the user receive, and where?
- Can the action be repeated safely?
- Is the action reversible? If not, how is risk handled?
- Does the same action behave consistently in other parts of the product?

Do not ship an attractive fake control. If a requested feature cannot be implemented because of missing API credentials, data contracts, infrastructure, or permissions, build only the truthful supported portion and clearly identify the blocker. Never fake a successful server operation.

---

# 8. Accessibility baseline and precise conformance language

Accessibility is an implementation requirement, not a decorative enhancement. Target WCAG 2.2 AA when that is the project requirement or stated target. The following is not a complete substitute for the full standard.

## 8.1 Important checks

| Area | Baseline / verification | Source |
|---|---|---|
| Text contrast | WCAG AA: at least 4.5:1 for normal text and 3:1 for large text, subject to specified exceptions | [WCAG 1.4.3 Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) |
| Non-text contrast | Check applicable controls, boundaries and graphical information for WCAG 1.4.11; do not judge from hue alone | [WCAG Non-text Contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) |
| Keyboard operation | Check that all required functionality is operable with keyboard and a logical focus order | [W3C Easy Checks](https://www.w3.org/WAI/test-evaluate/preliminary/) |
| Visible focus | WCAG AA 2.4.7 requires a visible keyboard focus indicator; WCAG 2.2 AA 2.4.11 requires focus not be entirely obscured by author-created content | [Focus Visible](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html), [Focus Not Obscured (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) |
| Target size | WCAG 2.2 AA 2.5.8 generally sets 24 × 24 CSS px or applicable spacing/other exceptions. 44 × 44 relates to the enhanced AAA criterion, not the general AA minimum | [Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Target Size (Enhanced)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html) |
| Reflow / zoom | Test reflow at 320 CSS px width and text resizing to 200% where applicable; content requiring two-dimensional layout has defined exceptions | [WCAG Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [Resize Text](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html) |
| Forms | Labels, instructions, errors, status messaging, and associated accessible names must be checked in rendered DOM and actual use | [WCAG 3.3.2 Labels or Instructions](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions.html), [Accessible Form Validation](https://www.smashingmagazine.com/2023/02/guide-accessible-form-validation/) |
| Images | Provide a text alternative when the image conveys information; decorative images should not create redundant announcements | [WCAG Non-text Content](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html) |
| Dialogs | Verify accessible naming, focus movement/containment where appropriate, keyboard operation, close path and return focus | [WAI-ARIA Authoring Practices: Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) |
| Motion | Respect reduced-motion preferences as a strong design default. WCAG 2.3.3 Animation from Interactions is Level AAA, not an AA criterion | [W3C Animation from Interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html), [MDN reduced motion](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion) |

## 8.2 Accessibility verification rules

- Run an available automated audit such as axe-core, Lighthouse or a project's existing equivalent. Record the tool and actual result.
- Manually navigate the main journeys with the keyboard. Test focus visibility, focus order, dialogs, menus, error recovery and sticky elements.
- Inspect names, roles, values, headings and landmarks in the DOM/accessibility tree where tooling permits.
- Measure contrast from actual computed colors or tokens rather than estimating solely from screenshots.
- Ensure status and errors are conveyed with more than color alone.
- Test zoom/reflow and long content. Verify meaningful image alternatives.
- Treat automated audit results as a useful subset of testing, not proof of full conformance. Never claim “WCAG certified” or “fully accessible” solely because a scanner reports no violations.

---

# 9. Performance, stability and implementation quality

## 9.1 Core Web Vitals baseline

The current web.dev guidance describes these “good” Core Web Vitals thresholds at the 75th percentile of page loads:

| Metric | Good threshold | What it reflects |
|---|---|---|
| Largest Contentful Paint (LCP) | ≤ 2.5 seconds | Loading performance |
| Interaction to Next Paint (INP) | ≤ 200 milliseconds | Interaction responsiveness |
| Cumulative Layout Shift (CLS) | ≤ 0.1 | Visual stability |

Source: [web.dev — Web Vitals](https://web.dev/articles/vitals). These thresholds are for field measurement and should not be inferred from a single screenshot or treated as guaranteed from one lab run. In development, use available lab diagnostics and performance traces to find problems; use real-user field data if the site has it.

## 9.2 Common avoidable problems

- Images without intrinsic dimensions or reserved aspect ratio causing content to jump.
- Large background videos, oversized images or multiple heavy animation libraries where static content would work.
- Fonts delaying visible text or causing large geometry changes when swapped.
- Unbounded polling, expensive renders, unnecessary client-side state, long synchronous work or event handlers that block interactions.
- Animations that trigger layout recalculation repeatedly when transform/opacity could suffice.
- Third-party resources added without a clear product need.
- Excessive dependencies, duplicated components or dead CSS introduced for cosmetic changes.
- Screenshots reviewed from a stale server/build or cached asset, leading the agent to “verify” old code.

## 9.3 Engineering quality rules

- Follow the existing framework, architecture, conventions, design system and testing practices unless there is a justified issue.
- Prefer small, coherent changes that solve identified problems. Do not rewrite working infrastructure to achieve a visual refresh.
- Avoid conflicting CSS overrides and specificity fights. Consolidate tokens and variants where appropriate.
- Use semantic HTML and native controls before custom interaction primitives when they can meet the requirement.
- Keep data and visualizations truthful. Values, labels and derived metrics should reconcile with the underlying sources.
- Do not compromise security, privacy, validation, error handling or data integrity to create smoother demos.
- Verify at least that relevant builds/tests work and inspect browser console/network failures where tooling allows.

---

# 10. Responsive design and content stress testing

## 10.1 Responsive behavior is content-driven

Do not assume that desktop + one phone preset proves responsive quality. Inspect the width where each layout begins to fail; breakpoints should occur where content or controls need a different composition, not simply because a device name appears in a CSS framework.

A practical initial viewport matrix is:

- Narrow mobile: 320–360 CSS px.
- Typical mobile: 375–430 CSS px.
- Tablet / narrow desktop: around 768 CSS px.
- Desktop: around 1024 CSS px.
- Wide desktop: 1280–1440 CSS px or the project's actual target.

These are **test samples, not universal breakpoints**. Include a gradual resize test when a toolbar, table, navigation or card grid can break between samples. Test real devices/browsers when the product's audience or risk warrants it.

## 10.2 Responsive requirements

- Main content should reflow without unintended horizontal scrolling, clipping or overlapping at required widths.
- Navigation must remain discoverable and usable by keyboard and touch.
- Touch users must not need hover to access key content or actions.
- Buttons and icon controls should have a comfortable target size; satisfy the applicable WCAG criteria and use a larger target where practical.
- Data tables should retain the user's ability to compare essential values. On narrow screens, choose an explicit pattern: responsive column reduction, row detail view, sticky key columns, or a justified horizontal scroll region with clear affordances.
- Text must tolerate long words, long names, localization, larger font settings, empty values and multiline errors.
- Dialogs and popovers must fit the viewport and remain operable when the on-screen keyboard appears.
- Account for safe areas when using true edge-to-edge layouts on supported devices.
- Images should crop intentionally and retain a meaningful focal point.

## 10.3 Stress content

Include at least some of these cases in manual or automated testing:

- Very long page title or button label.
- Long localized string or a name that cannot be conveniently broken.
- Large table with long identifiers and multiple actions.
- Empty list, filtered list with zero results, or no records at all.
- Error text that spans multiple lines.
- Loading delay, slow request, failed request and retry.
- Minimum and maximum numeric values; currency/date formatting.
- Long navigation label, many tabs or a large menu.
- Reduced motion, keyboard focus and zoom/reflow.

---

# 11. Reference analysis: learn principles, don't photocopy a website

When the agent is given reference URLs, screenshots or a visual sample, it should record an analysis before using it:

| Reference observation | What to extract | What not to copy blindly |
|---|---|---|
| Composition | Content order, alignment, dominant/subordinate regions, negative space | The exact layout even when the user's content needs something different |
| Typography | Contrast between text roles, scale, line length, density | Brand font/license assumptions or decorative styling without context |
| Color | Palette roles, accent frequency, light/dark balance, state semantics | The brand's exact palette when it belongs to another organization |
| Imagery | Art direction, crop, scale, context, relation to copy | Logos, proprietary artwork, screenshots or unlicensed assets |
| Components | Affordances, states, form layout, table behavior | Implementation details not visible or unsupported assumptions about code |
| Motion | Trigger, purpose, duration, easing, user control | Movement that was not understood or that harms accessibility/performance |
| Tone/content | Specificity, evidence, sentence style, information sequence | Copying proprietary text, claims or brand voice wholesale |

Prefer multiple references with distinct strengths rather than one “make it like X” instruction. Example: “Use reference A only for density and navigation; reference B for editorial hierarchy; do not inherit either brand's colors, logo, text or page structure.”

When fidelity to a provided design is the explicit requirement, matching the reference may be more important than inventing a new visual identity. In that situation, use reference screenshots as measurable targets and still check accessibility, content, responsiveness and functionality.

---

# 12. The implementation workflow: stage gates

Execute these stages in order unless the task is so small that a stage clearly does not apply. Do not use the workflow as ceremonial paperwork; produce only artifacts that materially improve consistency or verifiability.

## Stage 0 — Baseline and repository inspection

**Inspect:** repository instructions, branch/working tree if available, framework, routes, components, tokens, current assets, key user journeys, data/API contracts and test commands.

**Record:** current state, existing functionality that must be preserved, scope, test baseline, major risks and unverified assumptions.

**Gate:** Do not make broad design changes until the project surface and preservation requirements are understood.

## Stage 1 — Product and UX discovery

Identify the product mode, audience, user's job, primary journey, first-screen priority, main action, trust requirements, content source of truth and constraints.

If a missing detail is non-blocking, select a conservative default and document it. If a missing fact can cause data loss, security trouble or a material product error, treat it as a blocker rather than inventing an answer.

**Gate:** The intended user, primary task and success criteria are explicit.

## Stage 2 — Visual direction and anti-default review

Choose a visual thesis; define hierarchy and a layout idea; select type, color, surface, imagery and motion rules. If useful, compare up to three distinct directions. For each major choice, answer “why this fits this product.” Identify generic defaults that were considered and decide whether each is genuinely appropriate.

**Gate:** The direction is coherent and product-specific—not merely a list of banned colors or styles.

## Stage 3 — Design system and page/flow specification

Define semantic tokens and shared component rules. Map pages/routes and specify primary tasks and states. Identify where the same component must remain consistent and where a different composition is justified.

**Gate:** Repeated components and pages have a common system; necessary exceptions are explicit.

## Stage 4 — Implementation in coherent slices

Implement the most important user journey first. Preserve existing behavior, use verified content and data, complete functional states, and make design tokens the source of truth. Prefer focused changes over a high-risk rewrite.

**Gate:** Core features work at code/runtime level and no known major state is left as a visual placeholder.

## Stage 5 — Run and render the actual app

Use the existing development server/browser tooling when available. Confirm that the latest build is being served and the correct routes are loaded. Take screenshots at relevant viewport widths, scrolling through the top, middle and bottom of longer pages. Inspect important component states, not just the first screenshot.

Capture console/runtime/network errors if tools permit. Do not mistake screenshots from stale builds or cached assets for verification.

**Gate:** Actual rendered output—not source code alone—has been inspected.

## Stage 6 — Critique with evidence

Review every major route against the acceptance criteria. Record specific findings with a location, state, viewport and user impact. Examples:

- `[High] /members at 390px: action button overlaps the long member name; navigation to the edit action is obscured.`
- `[High] /checkout keyboard path: focus reaches the dialog, but the close/cancel path cannot be reached.`
- `[Medium] Dashboard overview: the same emphasis is applied to every metric, so the active incident is not distinguishable.`
- `[Low] Article footer: icon sizes differ between related links.`

Avoid ungrounded comments such as “doesn't feel premium.” Translate subjective impressions into observable hypotheses—weak hierarchy, inconsistent density, repetitive composition, generic imagery—and identify what would improve them. Keep genuinely subjective decisions marked as such.

**Gate:** Findings are severity-ranked, duplicates consolidated, and major root causes identified.

## Stage 7 — Fix and iterate

Fix blockers and high-severity defects first, then recurring pattern-level problems, then polish. After each meaningful fix, re-render affected pages and re-test the affected path. Run the relevant checks again.

Do not blindly add decorative detail as the “polish” pass. Remove noisy elements as often as you add or refine them.

**Gate:** No known release blocker introduced by the change remains. Remaining risks are explicitly identified.

## Stage 8 — Hardening and release verification

Run the relevant project build, tests, type checks, linting, accessibility scanner, browser checks and performance diagnostics that are available and appropriate. Check all main paths and responsive breakpoints. Re-run the checks that were initially failing.

If some tools or environments are unavailable, record them as `NOT EVALUATED` or `BLOCKED`; do not silently mark them as passes.

**Gate:** The final report has test evidence and honest caveats.

---

# 13. Screenshot-based design QA protocol

## 13.1 Capture matrix

For each important route or flow, capture enough output to expose the relevant defects:

- Desktop initial viewport.
- Mobile initial viewport.
- Desktop and mobile mid-scroll/bottom for long pages.
- Navigation open and closed where relevant.
- At least one active, loading, empty, error, success or selected state for key components as appropriate.
- Dialog, form-validation and destructive-action paths where applicable.
- Dark/light themes only when the product supports them.
- Reduced-motion behavior if the UI relies on meaningful motion.

For visual regression work, keep viewport, browser, font-loading, data and animation settings consistent with the baseline. A pixel diff can locate changes; it cannot decide whether a change is good or bad.

## 13.2 Visual review questions

1. Can a new visitor tell what the page is and what its most important action is?
2. Is the dominant visual weight consistent with the primary task?
3. Are heading, body, metadata and control labels clearly differentiated?
4. Is spacing consistent where elements share a role and varied where hierarchy requires it?
5. Does the composition have a useful rhythm, or does every section feel duplicated?
6. Do the chosen colors communicate hierarchy and state without harming contrast?
7. Is every border, background, card, shadow, icon, badge and animation earning its place?
8. Are images contextual, coherent, properly cropped and technically optimized?
9. Are controls visually recognizable and functionally complete?
10. Does the page remain usable with long text, no data, errors, keyboard focus, touch and narrower screens?
11. Does the site have product-specific character beyond a familiar template's styling?
12. Are there any obvious defects that a code review would not reveal?

## 13.3 Finding format and severity

Use a repeatable defect structure:

```markdown
- ID: UI-###
- Severity: P0 / P1 / P2 / P3
- Evidence: route, component, viewport, state, screenshot or measured output
- Problem: observable defect
- User impact: task or comprehension harm
- Root cause: the reusable rule or implementation issue, if known
- Fix: specific code/design change
- Verification: how the change will be checked
- Status: OPEN / FIXED / RECHECKED / BLOCKED
```

Suggested severity definitions:

- **P0 — Blocker:** Core journey cannot complete, serious data/security/correctness issue, or a severe release blocker.
- **P1 — High:** Major usability barrier, key feature broken, significant accessibility failure, or severe responsive/visual defect on a supported surface.
- **P2 — Medium:** Noticeable defect with a workable alternative; important inconsistency or state omission.
- **P3 — Low:** Minor visual or copy polish with little effect on task completion.

Use impact, frequency, user exposure and reversibility to assign severity. Do not escalate minor taste disagreements to blockers.

## 13.4 Stop conditions

The agent may stop after the agreed scope is complete when:

- All P0 and P1 defects introduced by the change are resolved, or unavoidable blockers are disclosed.
- Core user journeys have been verified at runtime where browser tools are available.
- Relevant build/tests are passing or failures are explained and accurately classified.
- Required responsive, accessibility and state checks are complete or marked unverified.
- Repeated AI-default patterns have been considered and either corrected or explicitly justified.
- Final screenshots/review have been revisited after fixes.

Do not claim “zero issues,” “perfect,” “fully accessible” or “production ready” if the evidence is incomplete.

---

# 14. Test strategy and acceptance matrix

The following is a starting checklist. Tailor it to the actual product; mark truly inapplicable items rather than forcing unrelated requirements onto the project.

| Area | Pass condition | Evidence |
|---|---|---|
| Scope | Required routes and user journeys are identified | Route/feature inventory |
| Product truth | Claims, sample data, product facts and assets are verified or identified as examples | Source-of-truth notes |
| Design direction | The choices fit this product and do not rely solely on generic defaults | Design brief + screenshots |
| Visual hierarchy | Primary content/action is distinguishable; supporting material is subordinate | Actual viewport screenshots |
| Typography | Roles are legible, consistent and responsive; long content does not clip | Screenshots + computed styles if needed |
| Tokens | Shared components use semantic tokens; exceptions are justified | Code review / token inspection |
| Content | No placeholder text, fake metrics or unsupported claims are presented as real | Content audit |
| Interaction | Key controls produce the advertised behavior and feedback | Browser run / automated test |
| State coverage | Applicable loading, empty, error, disabled, selected and success states work | State matrix + screenshots |
| Navigation | Links, active states, back/forward and direct routes work as required | Browser test |
| Responsive | Relevant pages remain usable at representative widths and through intermediate resize | Responsive screenshots/runtime check |
| Accessibility | Applicable WCAG criteria, keyboard behavior, contrast, labels and focus have been checked | axe/Lighthouse plus manual evidence |
| Motion | Motion is purposeful, performant and reduced-motion aware | Runtime review |
| Stability | No significant avoidable layout shifts or major render jumps | Performance trace / observation |
| Performance | No obvious oversized asset, blocking task or major user-facing delay; Core Web Vitals investigated when applicable | Lab/field report, if available |
| Console/network | No relevant runtime errors, unhandled failures or unexpected failed requests | Browser console/network output |
| Tests/build | Relevant project tests, build, type checks and linting pass or are explained | Actual command output |
| Regression | Existing key features still work after the UI change | Regression test / browser run |
| Final report | Claims match evidence and untested areas are disclosed | Final summary |

---

# 15. Prompting strategies: what to say and what to avoid

## 15.1 Vague prompts vs actionable prompts

| Weak instruction | Why it fails | Stronger instruction |
|---|---|---|
| “Make the site look better.” | No task, audience, evidence or defect is defined | “On `/overview`, the primary task is identifying overdue cases. Current metric cards all have equal weight. Use the actual overdue count and age distribution to create a clearer hierarchy; render desktop/mobile screenshots and verify the result.” |
| “Make it look premium.” | Premium has no single visual definition | “Use restrained editorial typography, fewer surface layers, explicit whitespace and real project imagery; avoid decorative gradients and nested card chrome unless a clear reason emerges from the brief.” |
| “Make it look like Apple/Linear/Stripe.” | Encourages surface imitation without extracting the relevant design logic | “Analyze how the reference uses hierarchy, spacing and motion. Apply those principles to our content, while preserving our own brand, task flow, assets and architecture.” |
| “Use unique colors and fonts.” | Novelty becomes an arbitrary palette/font swap | “Choose a palette and type system based on the intended audience, brand personality and product content. Explain how each role supports hierarchy and confirm contrast.” |
| “Add animations.” | Adds movement without purpose | “Animate the filter-to-results transition so users can understand what changed; avoid motion that delays content, and honor reduced-motion preferences.” |
| “Build the whole platform.” | Too much scope without contracts or review gates | “Inventory routes/features, then implement the highest-priority user journey in coherent slices. After each slice, test functionality and inspect the rendered UI.” |
| “Make everything consistent.” | Could suppress necessary differences between content and task types | “Use shared tokens/components for equivalent roles; vary composition only where the content, task or visual hierarchy calls for it. Document exceptions.” |
| “Run tests and say it is done.” | Encourages completion theater | “Run the available checks, record actual results, inspect the real browser output, fix findings, and list every important check that could not be run.” |

## 15.2 Anti-patterns in agent workflow

- **One-shot generation:** A single prompt rarely describes every page, state and visual exception. Use stage gates and iterations.
- **Design before discovery:** The agent invents requirements instead of learning from the repo.
- **Style without content:** Placeholder content changes line length, layout density and credibility; replace it before final visual QA.
- **Screenshots without code/runtime evidence:** A static image can miss broken controls, hidden focus states and data errors.
- **Automated checks only:** Tests can prove specified behavior but not that the overall hierarchy makes sense.
- **Visual opinion only:** Human/LLM critique can miss measurable contrast, keyboard, runtime and network failures.
- **Unbounded redesign:** The agent rewrites working architecture, adds unnecessary libraries and causes regressions while chasing novelty.
- **No exception policy:** A detector flags a valid brand choice and the agent blindly changes it. Every warning needs context.
- **No memory of decisions:** Every new route/session selects another palette or interaction pattern because the design system is not recorded.
- **No final evidence:** The response claims success based on intention rather than running code, commands, browser views or measurements.

---

# 16. Copy-paste execution prompts for phases

These can be used separately if the agent environment benefits from a staged workflow. The Master Execution Prompt below can run the full process autonomously; use these prompts to focus on one phase at a time or when the first pass uncovers major complexity.

## 16.1 Discovery prompt

```text
Read the AI Website Design & Engineering playbook supplied in the current context. Inspect the actual repository and current application before recommending changes. Identify the framework, routes, existing design system, content sources, core user journeys, working features that must be preserved, test commands and available browser tools.

Establish product truth: audience, product type, primary user tasks, most important information/action per page, trust/correctness constraints, and unverified assumptions. Do not invent facts. Read existing documentation before asking questions. Ask only for material information that cannot safely be inferred; otherwise record a reasonable assumption.

Return a concise inventory of current behavior, scope, risks and acceptance criteria. Do not write speculative UI code before understanding the current product. If the task is sufficiently clear, continue to the design phase without waiting for approval.
```

## 16.2 Design direction prompt

```text
Using the verified product context and supplied playbook, define a product-specific design direction before changing the interface. Specify the visual thesis, page hierarchy, layout/composition, typography roles, semantic color palette, spacing system, surface/radius/elevation logic, imagery direction, motion rules, reusable component behavior, responsive rules and accessibility constraints.

Explain why the major choices fit the audience and task. Review for generic AI-default combinations: repeated centered heroes, identical feature cards, arbitrary gradients, default font choices, nested cards, fake copy/social proof, decorative icons, unnecessary labels and blanket scroll animations. Do not blindly ban a style if it is justified, and do not replace it with another universal template.

Use reference sites only to extract principles unless exact visual replication was explicitly requested. If useful, compare up to three directions and choose the best supported option. Record the resulting rules in the project’s existing design documentation, or create a concise DESIGN.md if the project needs durable context.
```

## 16.3 Implementation prompt

```text
Implement the approved design direction in the real project. Preserve working architecture and existing behavior. Use the existing stack and design system where appropriate; avoid unrelated rewrites, fake features, unsupported product claims and decorative controls.

Build in coherent slices beginning with the most important user journey. Use semantic design tokens, meaningful content, and reusable components only where their roles are actually shared. Implement relevant hover/focus/pressed/disabled/loading/selected/error/empty/success states, validation, recovery and responsive behavior. Ensure controls perform their advertised actions.

Keep changes focused. Run relevant tests as you work. Do not claim browser verification unless the application was actually run and inspected. When implementation is complete, proceed to rendered QA rather than stopping at code completion.
```

## 16.4 Critique prompt

```text
Act as a rigorous design reviewer and QA engineer. Inspect the actual running website and screenshots, not just source code. Review the most important pages at desktop, mobile and relevant intermediate widths; inspect long-page sections and meaningful interaction states.

Evaluate product fit, information hierarchy, composition, typography, color semantics, spacing rhythm, card/surface use, imagery authenticity, copy specificity, interaction completeness, responsive integrity, keyboard/focus behavior, accessibility, content stability and performance. Identify repeated patterns that look templated, but avoid false positives based only on a font, color or component.

For every finding, record route/component, viewport/state, observable evidence, user impact, severity, likely root cause, precise fix, and verification method. Distinguish measurable defects from subjective impressions. Prioritize P0/P1 issues, then repeated system-level problems, then polish. Do not merely list problems; after critique, implement the fixes and recheck affected pages.
```

## 16.5 Release hardening prompt

```text
Perform release verification for the changes actually made. Run relevant build, type-check, lint, unit/integration/e2e tests, and available accessibility/performance checks. Test primary user journeys through the real browser. Inspect console/network failures, keyboard navigation, focus visibility, form errors, responsive behavior and important loading/empty/success/failure states.

Measure WCAG contrast from real colors where possible. Check WCAG 2.2 AA requirements applicable to the interface; do not represent a scanner as a full conformance assessment. Investigate Core Web Vitals when field or lab data is available, and distinguish field metrics from a single lab run.

Fix verified regressions and rerun relevant checks. Return an honest acceptance report with commands actually run, results, routes/viewports/states inspected, findings fixed, and anything not evaluated or blocked. Do not claim perfect, fully accessible, zero-issue or production-ready status without evidence.
```

---

# 17. Master Execution Prompt — full autonomous mode

> **This is the main prompt to use when you give this entire Markdown file to another AI.** The agent must treat the document as an instruction source and operating playbook, then apply it to the project in the current workspace.

```text
ROLE
Act as a principal product designer, senior frontend engineer, interaction designer and pragmatic QA engineer. Your task is to improve or build the actual website in the current repository—not merely describe how someone else could do it.

REFERENCE DOCUMENT
Read this complete “AI Website Design & Engineering: Iceberg Playbook + Agent Execution Specification”. Follow its operating contract, evidence discipline, product-specific design rules, accessibility requirements, implementation workflow and acceptance matrix. The document is both a knowledge reference and an execution instruction.

PRIMARY OBJECTIVE
Deliver a distinctive, coherent, product-specific, visually polished, usable, credible, accessible, responsive and functional web experience. Avoid the generic AI-generated look by fixing the underlying design decisions, content, interaction states and verification loop. Do not confuse originality with unnecessary novelty, and do not replace one generic template with another.

STAGE 0 — INSPECT AND PRESERVE
1. Inspect repository instructions, documentation, framework/runtime, routes, components, assets, design tokens, data/API contracts and relevant tests.
2. Inspect Git status/current changes if available. Preserve existing user work and working behavior.
3. Identify the scope, important user journeys, existing constraints and baseline issues.
4. Do not make broad rewrites, install unnecessary dependencies, change frameworks, run destructive commands or add paid services without necessity and authority.

STAGE 1 — ESTABLISH PRODUCT TRUTH
1. Identify the product, intended audience, primary tasks, context of use, success criteria, content source of truth, and any trust/security/data constraints.
2. Classify each page/flow as primarily Persuade, Operate, Create/Configure, Read/Learn, Explore, Transact or Showcase.
3. Determine the primary information and action on each important page.
4. Reuse verified project information. Never fabricate product features, testimonials, customer logos, metrics, awards, security claims or business outcomes.
5. If context is missing, make and document low-risk assumptions. Do not invent answers to material security, data-integrity or irreversible-action questions.
6. Record useful durable product facts in PRODUCT.md or existing project documentation when appropriate.

STAGE 2 — ART-DIRECT THE EXPERIENCE
1. Define a concrete visual thesis based on the product and audience.
2. Specify hierarchy, layout/composition, typography, semantic palette, spacing, surface/elevation/radius roles, imagery, motion and interaction rules.
3. Use specific reference analysis when references exist: extract principles rather than blindly copy another brand. Respect a request for exact fidelity when it is explicitly the goal.
4. Review the plan for automatic AI-default choices: centered SaaS hero, repeated three-card sections, arbitrary gradients, identical rounded cards/shadows, generic fonts without thought, fake social proof, emoji icon systems, unnecessary all-caps labels, arbitrary numbered markers and blanket scroll animations.
5. Do not treat any individual font, color, radius, card, layout or motion pattern as universally forbidden. Justify each major choice in the product context.
6. Define semantic design tokens and record them in the existing design system or DESIGN.md if useful. Avoid hard-coded visual exceptions unless their reason is documented.

STAGE 3 — IMPLEMENT THE REAL PRODUCT
1. Make focused, coherent changes in the current codebase.
2. Preserve working routes, architecture, backend contracts and data behavior unless a change is necessary and in scope.
3. Match the chosen design direction across the complete required scope, not just the hero or first viewport.
4. Implement the intended functionality. All actionable controls must work. Do not ship controls that only look interactive.
5. Implement applicable loading, empty, no-results, error, validation, disabled, selected, success and confirmation states.
6. Make labels and errors clear, actions explicit, and recovery paths available. Preserve entered form data where appropriate after recoverable failures.
7. Use semantic HTML, accessible names, keyboard operation and appropriate responsive behavior.
8. Use authentic content/assets when available; identify sample data honestly and make charts/metrics internally consistent.
9. Avoid unrelated code churn and unnecessary dependencies.

STAGE 4 — BUILD AND TEST IN SLICES
1. Implement the highest-priority user journey first, then proceed to remaining in-scope routes/features.
2. Run relevant existing tests, type checks, linting and build checks. Diagnose failures rather than assuming they are unrelated.
3. Do not claim a feature works until it has been verified to the extent possible in the environment.

STAGE 5 — INSPECT THE ACTUAL RENDER
1. Run the real application with available browser tooling. Confirm the correct, latest build and routes are being served.
2. Capture and inspect screenshots for key pages at narrow mobile, typical mobile, tablet/narrow desktop and desktop/wide desktop widths. Use the playbook's viewport samples as a starting matrix, not universal breakpoints.
3. Inspect the initial viewport, long-page sections, navigation, dialogs, forms, tables and key interaction states.
4. Stress-test long text, empty/no-result data, validation errors and responsive layouts.
5. Check console/network failures and visible focus/keyboard behavior where tools permit.
6. Do not treat source inspection, an LLM's imagination, or one desktop screenshot as browser verification.

STAGE 6 — CRITIQUE WITH EVIDENCE
1. Review the rendered result for product fit, hierarchy, composition, typography, spacing rhythm, color semantics, card/surface overuse, authentic imagery, copy specificity, component consistency, motion, interaction completeness, accessibility, responsive integrity, stability and performance.
2. For each defect, record the route/component, viewport/state, evidence, user impact, severity, root cause, precise fix and verification method.
3. Separate measured standards violations from visual estimates and subjective taste. Do not claim a contrast violation without measuring relevant colors; do not claim full WCAG conformance from a scanner.
4. Prioritize blockers and high-impact problems. Find and fix shared root causes rather than making disconnected one-off patches.

STAGE 7 — FIX AND RECHECK
1. Implement the fixes; do not stop after producing a critique report.
2. Re-render the affected pages and rerun relevant tests after each meaningful correction.
3. Complete at least two distinct passes: (a) structure, hierarchy, content and functionality; (b) visual refinement, states, responsiveness, accessibility and polish. Continue additional passes if serious issues remain and tooling/resources allow.
4. Remove decorative elements that do not help the task. Do not add novelty merely to prove the design is different.

STAGE 8 — ACCEPTANCE AND REPORTING
1. Run the applicable build/tests and accessibility/performance checks available in this project.
2. Verify key user journeys and the final rendered output.
3. Resolve all known P0/P1 defects introduced by the change, or state clearly why any remain blocked.
4. Report which routes and features changed, the primary design decisions, exact checks actually run, test results, browser/viewports/states inspected, defects fixed, and anything not evaluated.
5. Distinguish VERIFIED, INFERRED, NOT EVALUATED and BLOCKED items. Do not claim “perfect”, “zero issues”, “fully accessible” or “production ready” without appropriate evidence.

AUTONOMY
Proceed using the current repository and sensible low-risk assumptions. Do not stop after a plan, ask for approval of routine decisions, or repeat questions already answered by the project. Ask only when a missing decision materially affects correctness or safety. Do as much of the implementation and verification as the actual environment permits, then report limitations honestly.

FINAL ACCEPTANCE STANDARD
The result must not simply look different. It must be more specific to its product, clearer in hierarchy, consistent without being monotonous, truthful in content, complete in interactions, responsive in real layouts and verified through the actual available tools. If any of those dimensions cannot be verified, disclose the limitation instead of implying it passed.
```

---

# 18. Reusable compact launch prompt

If the AI environment can read this file and you need a shorter message, use the following:

```text
Read and follow the complete file “AI Website Design & Engineering: Iceberg Playbook + Agent Execution Specification.md” in this workspace. Apply it to the actual website and repository. Do not only produce a plan or critique: inspect the project, preserve working behavior, establish product-specific design rules, implement the changes, launch the app, inspect rendered mobile/desktop pages and important interaction states, fix the defects found, rerun relevant checks, and report verified results and remaining limitations. Do not blindly ban styles or invent content. Follow the playbook’s evidence discipline, accessibility baseline, responsive QA, state-completeness requirements and release gates.
```

---

# 19. Final reporting template for the agent

The receiving AI should finish with a concise report in this form:

```markdown
# Implementation and QA Report

## Scope completed
- Pages/routes changed:
- Features and interactions changed:
- Existing behavior preserved:

## Design decisions
- Product-specific visual direction:
- Tokens/components established or reused:
- Anti-default patterns removed or deliberately retained with reasons:

## Verification performed
| Check | Command/tool | Actual result | Evidence / scope |
|---|---|---|---|
| Build | | PASS / FAIL / NOT RUN | |
| Unit/integration tests | | PASS / FAIL / NOT RUN | |
| Browser user journeys | | PASS / FAIL / NOT EVALUATED | |
| Responsive inspection | | PASS / FAIL / NOT EVALUATED | |
| Accessibility | | Findings / NOT EVALUATED | |
| Performance | | Findings / NOT EVALUATED | |
| Console/network | | Findings / NOT EVALUATED | |

## Defects fixed
- [Severity] Problem → fix → how rechecked

## Remaining limitations
- BLOCKED:
- NOT EVALUATED:
- Known risks:

## Acceptance decision
- READY FOR REVIEW / READY WITH DISCLOSED LIMITATIONS / NOT READY
- Reason:
```

The report should be no more confident than its evidence. A test that was not run must be marked `NOT RUN`; a browser that could not open must be marked `NOT EVALUATED`; a failing external service must be identified as blocked. Avoid quietly omitting failed checks.

---

# 20. Research notes and source index

This playbook synthesizes current practitioner guidance, official standards, design-system documentation, academic/published research, and real-world reports of AI-assisted redesign workflows. These sources do **not** all provide the same kind of evidence. The anti-pattern taxonomy is largely professional heuristic; accessibility thresholds are standards-based; case-study workflows are self-reported practice; style preferences remain context-dependent.

## 20.1 Primary standards and technical references

1. **Anthropic — Frontend Design skill (maintained source file).** Guidance for grounding designs in product subject matter, deliberate type/layout/color choices, restrained motion, plan–review–build–critique, and warnings that anti-AI alternatives can become clichés. Practitioner guidance, not a design standard. [Source](https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md)
2. **Anthropic — Building Effective Agents.** General guidance on structured agent workflows and keeping orchestration as simple as possible. It is an agent-engineering source, not direct evidence for visual aesthetics. [Source](https://www.anthropic.com/research/building-effective-agents)
3. **Impeccable — project repository.** Open-source design guidance for coding agents, with commands for planning, critique, audit, implementation and polish. Its detector rules are useful heuristics and need project-specific review. [Source](https://github.com/pbakaus/impeccable)
4. **Impeccable — Critique.** Guidance for reviewing a page's clarity, hierarchy and design character. [Source](https://impeccable.style/docs/critique)
5. **Impeccable — Audit.** Checks related to accessibility, performance, themes, responsive behavior and implementation integrity. A score or automated report is not a substitute for full manual evaluation. [Source](https://impeccable.style/docs/audit)
6. **W3C WAI — WCAG 2.2 understanding documents.** Primary sources for the exact success criteria and conformance levels. [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
7. **W3C WAI — Easy Checks.** A preliminary accessibility review that includes keyboard access and visual focus. [Source](https://www.w3.org/WAI/test-evaluate/preliminary/)
8. **WAI-ARIA Authoring Practices Guide — Dialog (Modal) Pattern.** Implementation guidance for dialog semantics and keyboard interaction. [Source](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
9. **web.dev — Web Vitals.** Current Core Web Vitals definitions and recommended thresholds. Field results and lab diagnostics must be distinguished. [Source](https://web.dev/articles/vitals)
10. **Chrome for Developers — Layout shift culprits.** Technical explanation of common avoidable visual-instability causes. [Source](https://developer.chrome.com/docs/performance/insights/cls-culprit)
11. **MDN — `prefers-reduced-motion`.** Browser documentation for respecting the user's system motion preference. [Source](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion)
12. **US Web Design System — Design Tokens.** Government design-system rationale for controlled, semantic token values. [Source](https://designsystem.digital.gov/design-tokens/)
13. **GOV.UK Design System — Spacing.** A live example of a bounded and responsive spacing system. It is an example, not a universal spacing mandate. [Source](https://design-system.service.gov.uk/styles/spacing/)

## 20.2 UX research and design-system guidance

14. **Nielsen Norman Group — Why Does a Design Look Good?** Practitioner analysis of hierarchy, typography, spacing and alignment. [Source](https://www.nngroup.com/articles/why-does-design-look-good/)
15. **Nielsen Norman Group — Visual Hierarchy in UX.** Explanation of scale, contrast and grouping as hierarchy mechanisms. [Source](https://www.nngroup.com/articles/visual-hierarchy-ux-definition/)
16. **Nielsen Norman Group — Ten Usability Heuristics.** General usability heuristics such as system-status visibility, user control, consistency, error prevention and minimalist design. [Source](https://www.nngroup.com/articles/ten-usability-heuristics/)
17. **Nielsen Norman Group — Button States.** How enabled, disabled, hover, focus, pressed and related states communicate behavior. [Source](https://www.nngroup.com/articles/button-states-communicate-interaction/)
18. **Nielsen Norman Group — Data Tables.** User tasks and usability considerations for data tables. [Source](https://www.nngroup.com/articles/data-tables/)
19. **Nielsen Norman Group — Cognitive Load in Forms.** Structure, transparency, clarity and support for form completion. [Source](https://www.nngroup.com/articles/4-principles-reduce-cognitive-load/)
20. **Baymard Institute — UI Badges.** Guidance for using badges only when they provide meaningful scanning value and avoiding clutter. Primarily relevant to e-commerce/product discovery. [Source](https://baymard.com/blog/badge-ui)
21. **GoodWeb literature review (JMIR Formative Research, 2019).** Review of 69 website-evaluation studies; identifies recurring dimensions including usability, content, design, functionality, appearance and interactivity. This supports multi-dimensional evaluation, not one specific style. [Source](https://pmc.ncbi.nlm.nih.gov/articles/PMC6914275/)
22. **Fogg et al. — What Makes Web Sites Credible?** A published study of perceived credibility and website elements. Treat its specific findings in their study context and date; do not assume they provide a universal modern ranking of visual patterns. [PDF](https://credibility.stanford.edu/pdf/p61-fogg.pdf)

## 20.3 Practitioner case studies and community signals

23. **Sirui Tao — “what I learned redesigning my website with an AI coding agent” (May 23, 2026).** First-person account emphasizing a clear visitor goal, plan-first implementation, responsive screenshots, removal of nonessential elements, and a living design-heuristics file. Strongly relevant practitioner reflection; not a controlled experiment. [Source](https://dylantao.github.io/blog/2026/website-redesign-ai-agent/)
24. **“I rebuilt my personal site with Claude Code by making it build a replica first.”** First-person workflow with detailed component/motion specs, reference screenshots, Playwright capture/pixel-diff, content substitution and responsive checks. Useful implementation case study; results are self-reported and specific to the author's environment. [Source](https://aviaggarwal.hashnode.dev/i-rebuilt-my-personal-site-with-claude-code-by-making-it-build-a-replica-first)
25. **FABLE 25 — build guide.** A creative-workflow case study that describes an explicit design constitution, art-directed per-site briefs, actual browser screenshots, several critique iterations and production asset optimization. Useful as an example of a strong feedback loop, not proof that its exact visual style or iteration count suits every project. [Source](https://fable-25.netlify.app/guide/)
26. **Reddit: why AI-generated websites look similar.** Community discussion about repeated gradients, card patterns, vague prompting and the value of more intentional design briefs. Anecdotal; used to discover practitioner concerns, not to establish causation. [Source](https://www.reddit.com/r/vibecoding/comments/1ta6r5y/why_do_all_aigenerated_websites_look_exactly_the/)
27. **Reddit: making UI designs look less AI-generated.** Community reports on design references, audit workflows and repeated critique. Anecdotal, not a controlled assessment. [Source](https://www.reddit.com/r/ClaudeCode/comments/1rfjovy/how_do_you_create_ui_designs_that_dont_look/)

## 20.4 Proposed AI-look detector research

28. **Han Kim — “The Tells: A Measurable Taxonomy of the AI-Generated Design Look” (draft, June 2026).** Proposes a taxonomy of visual tells and a detector. It is useful for naming and discussing recurring patterns, but should be treated as a draft and not as a universal standard, validated beauty score or replacement for contextual review. [PDF](https://labs.iovstudio.kr/papers/ai-design-tells.pdf)
29. **Whetstone — banned AI patterns reference.** A community-maintained anti-pattern list with layout, type, color, decoration and content examples. Use as a diagnostic catalogue, not a universally binding set of bans. [Source](https://github.com/iliaal/whetstone/blob/master/plugins/whetstone/skills/ia-frontend-design/references/banned-ai-patterns.md)

## 20.5 How to use this source index

- Use **W3C** sources for exact WCAG requirements and conformance levels.
- Use **web.dev / Chrome** sources for browser performance behavior and measurement guidance.
- Use **government design systems** for concrete patterns and token examples; do not assume their brand style suits every product.
- Use **NN/g and Baymard** for usability findings and practitioner interpretation of user tasks. Check the article's context before generalizing an e-commerce finding to another domain.
- Use **Anthropic and Impeccable** to structure the AI agent's work. Treat style suggestions as professional guidance rather than standards.
- Use **case studies and Reddit** to identify workflow practices and recurrent frustrations; label them as self-reported or anecdotal.
- Treat **AI-look detectors and anti-pattern lists** as screening aids. Their false positives must be reviewed against the product brief, brand and functional context.

---

# 21. Bottom line

The goal is not to hide the involvement of AI. The goal is to prevent unsupported defaults and incomplete execution from becoming the final product.

**The operating formula is:**

**Verified product truth → explicit design direction → coherent tokens and patterns → real implementation → rendered browser inspection → evidence-based critique → targeted fixes → re-verification.**

A website is not good because its font is unusual, its palette is rare, it uses asymmetry or it passes a detector. It is good when its design choices fit the product, its information is clear and truthful, its controls work, its details are consistent, and its quality holds up in the actual environment where people use it.
