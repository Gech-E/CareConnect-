---
name: Clinical Clarity
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#414754'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#727785'
  outline-variant: '#c1c6d6'
  surface-tint: '#005bc0'
  primary: '#005bbf'
  on-primary: '#ffffff'
  primary-container: '#1a73e8'
  on-primary-container: '#ffffff'
  inverse-primary: '#adc7ff'
  secondary: '#006a61'
  on-secondary: '#ffffff'
  secondary-container: '#86f2e4'
  on-secondary-container: '#006f66'
  tertiary: '#515f74'
  on-tertiary: '#ffffff'
  tertiary-container: '#6a788d'
  on-tertiary-container: '#000510'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc7ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#89f5e7'
  secondary-fixed-dim: '#6bd8cb'
  on-secondary-fixed: '#00201d'
  on-secondary-fixed-variant: '#005049'
  tertiary-fixed: '#d5e3fc'
  tertiary-fixed-dim: '#b9c7df'
  on-tertiary-fixed: '#0d1c2e'
  on-tertiary-fixed-variant: '#3a485b'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  headline-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 16px
  md: 24px
  lg: 40px
  xl: 64px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style

The design system is centered on a "Human-Centric Clinical" aesthetic. It prioritizes trust, accessibility, and immediate clarity to reduce patient anxiety during remote consultations. 

The style is **Minimalist** with a focus on high-quality typography and spacious layouts. It avoids unnecessary decoration, opting instead for functional clarity. While the environment is "clinical" (utilizing white space and structured grids), it remains "friendly" through the use of soft edges and a calming color palette. The goal is to evoke a sense of professional reliability and effortless navigation for users of all technical abilities.

## Colors

The color palette is anchored by **Trust-Building Blue** (#1A73E8), used for primary actions and key brand touchpoints. 

- **Primary Blue**: High-visibility color for primary buttons and active states.
- **Success Teal**: Used for positive health outcomes, appointment confirmations, and success notifications.
- **Professional Slate**: The primary color for text and iconography, providing high contrast against white backgrounds without the harshness of pure black.
- **Surface Grey**: A subtle, cool-toned grey used for secondary containers and background layering to differentiate content zones.
- **Background**: Pure white is used for the main canvas to maintain a clean, sterile, and professional feel.

## Typography

This design system utilizes **Inter** for its exceptional legibility and neutral, professional character. To support accessibility, the base body size is set to 16px/18px, ensuring patients can read medical information without strain.

- **Headlines**: Use Semi-Bold and Bold weights with slight negative letter-spacing for a modern, authoritative feel.
- **Body Text**: Maintain generous line heights (1.5x minimum) to improve readability for long-form medical descriptions.
- **Labels**: Used for badges and status indicators, employing medium weights to ensure they stand out even at smaller sizes.

## Layout & Spacing

The layout follows a **Fluid Grid** model with a focus on generous white space to prevent cognitive overload.

- **Desktop**: 12-column grid with 24px gutters. Content is often centered in a max-width container (1200px) to keep line lengths readable.
- **Mobile**: 4-column grid with 16px margins. 
- **Rhythm**: All spacing follows a 4px/8px baseline shift. Use 40px (lg) or 64px (xl) between major sections to emphasize the minimalist aesthetic.
- **Touch Targets**: All interactive elements (buttons, inputs) must maintain a minimum height of 48px to accommodate users with varying motor skills.

## Elevation & Depth

This design system uses **Tonal Layers** supplemented by **Ambient Shadows** to create a clear hierarchy of information.

- **Level 0 (Background)**: White (#FFFFFF) or Neutral Grey (#F8FAFC).
- **Level 1 (Cards)**: White surfaces with a soft, diffused shadow (0px 4px 20px rgba(0, 0, 0, 0.05)). This elevation is used for doctor profiles and appointment summaries.
- **Level 2 (Modals/Pop-overs)**: White surfaces with a more pronounced shadow (0px 10px 30px rgba(0, 0, 0, 0.10)) to draw immediate focus.
- **Interactions**: On hover, cards should subtly lift by increasing shadow spread or adding a 1px border in the Primary Blue color.

## Shapes

The design system employs **Rounded** geometry to soften the clinical feel and make the interface feel more approachable and modern.

- **Standard Elements**: Buttons and Input fields use `rounded-md` (0.5rem / 8px).
- **Containers**: Doctor cards and informational modules use `rounded-lg` (1rem / 16px) to create a friendly, distinct "pocket" for information.
- **Badges/Chips**: Status badges use a full pill-shape (999px) to differentiate them from interactive buttons.

## Components

### Buttons
- **Primary**: Solid Primary Blue with white text. Height: 48px. Rounded: 8px.
- **Secondary**: Ghost style with Primary Blue border and text. 
- **Critical**: Soft red background with dark red text for "Cancel" or "End Visit" actions.

### Cards (Doctor/Appointment)
Card-based layouts are the primary way information is presented. Each card should feature:
- 16px internal padding.
- 16px corner radius.
- Level 1 elevation.
- A clear, high-contrast primary action button (e.g., "Book Now").

### Status Badges
Used for appointment status (Upcoming, Completed, Canceled). 
- **Style**: Subtle background tint (e.g., Success Teal at 10% opacity) with high-contrast text of the same hue.

### Input Fields
- **Style**: 1px Slate-200 border, 48px height, 8px radius.
- **States**: On focus, the border transitions to Primary Blue with a 2px width. Labels are always visible above the field (no floating labels) for maximum accessibility.

### Touch Targets
All links and icons must have a minimum hit area of 44x44px. Iconography should be simple, using 2px stroke weights for consistent visibility.