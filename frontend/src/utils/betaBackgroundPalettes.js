/** Color palettes for JPilot Beta chat animated backgrounds. */

import { resolveCanvasColors } from './canvasTheme'

/** All beta backgrounds use a theme-matched solid base (white / near-black). */
export const BETA_BACKGROUND_BASE = 'theme'

/** @param {string} backgroundId */
export function getBetaBackgroundBase(backgroundId) {
  void backgroundId
  return BETA_BACKGROUND_BASE
}

const AURORA_BASE = {
  speed: 0.4,
  scale: 0.1,
  noiseFrequency: 2.5,
  noiseAmplitude: 3.5,
  bandHeight: 0.5,
  bandSpread: 0.8,
  octaveDecay: 0.41,
  layerOffset: 1,
  colorSpeed: 1.0,
  enableMouseInteraction: false,
  mouseInfluence: 0.1
}

/** SoftAurora props tuned per theme for JPilot chat backgrounds. */
export function getBetaAuroraSettings() {
  return resolveCanvasColors(
    {
      ...AURORA_BASE,
      color1: '#7184df',
      color2: '#10B981',
      brightness: 0.62,
      noiseAmplitude: 2.8,
      bandSpread: 0.72
    },
    {
      ...AURORA_BASE,
      color1: '#7184df',
      color2: '#10B981',
      brightness: 1.1
    }
  )
}

const LINE_WAVES_BASE = {
  speed: 0.1,
  innerLineCount: 21,
  outerLineCount: 25,
  warpIntensity: 1.0,
  rotation: -132,
  edgeFadeWidth: 0.0,
  colorCycleSpeed: 0.6,
  color1: '#3B82F6',
  color2: '#3B82F6',
  color3: '#06B6D4',
  enableMouseInteraction: false,
  mouseInfluence: 1.1
}

/** LineWaves props tuned per theme for JPilot chat backgrounds. */
export function getBetaLineWavesSettings() {
  return resolveCanvasColors(
    {
      ...LINE_WAVES_BASE,
      brightness: 0.32
    },
    {
      ...LINE_WAVES_BASE,
      brightness: 0.2
    }
  )
}

const GALAXY_BASE = {
  focal: [0.5, 0.5],
  rotation: [1.0, 0.0],
  starSpeed: 0.5,
  density: 1.4,
  speed: 1.0,
  mouseInteraction: false,
  mouseRepulsion: false,
  glowIntensity: 0.4,
  saturation: 0.3,
  twinkleIntensity: 0.6,
  rotationSpeed: 0.05,
  repulsionStrength: 2,
  autoCenterRepulsion: 0,
  transparent: true,
  disableAnimation: false
}

/** Galaxy props tuned per theme for JPilot chat backgrounds. */
export function getBetaGalaxySettings() {
  return resolveCanvasColors(
    {
      ...GALAXY_BASE,
      hueShift: 195,
      glowIntensity: 0.52,
      saturation: 0.42,
      density: 1.25
    },
    {
      ...GALAXY_BASE,
      hueShift: 170
    }
  )
}

const DOT_FIELD_BASE = {
  dotRadius: 1.5,
  dotSpacing: 10,
  cursorRadius: 100,
  cursorForce: 0,
  bulgeOnly: false,
  bulgeStrength: 67,
  glowRadius: 50,
  sparkle: true,
  waveAmplitude: 0,
  enableMouseInteraction: false
}

/** DotField props tuned per theme for JPilot chat backgrounds. */
export function getBetaDotFieldSettings() {
  return resolveCanvasColors(
    {
      ...DOT_FIELD_BASE,
      gradientFrom: 'rgba(16, 185, 129, 0.52)',
      gradientTo: 'rgba(59, 130, 246, 0.4)',
      glowColor: '#cbd5e1'
    },
    {
      ...DOT_FIELD_BASE,
      gradientFrom: '#10B981',
      gradientTo: '#3B82F6',
      glowColor: '#120F17'
    }
  )
}

const THREADS_BASE = {
  amplitude: 2,
  distance: 1.2,
  enableMouseInteraction: false
}

/** Threads props tuned per theme for JPilot chat backgrounds. */
export function getBetaThreadsSettings() {
  return resolveCanvasColors(
    {
      ...THREADS_BASE,
      color: [0.1, 0.24, 0.38],
      amplitude: 1.65,
      distance: 1.1
    },
    {
      ...THREADS_BASE,
      color: [0.92, 0.94, 0.98]
    }
  )
}

const ORB_BASE = {
  hoverIntensity: 0,
  rotateOnHover: false,
  forceHoverState: false,
  enableMouseInteraction: false
}

/** Orb props tuned per theme for JPilot chat backgrounds. */
export function getBetaOrbSettings() {
  return resolveCanvasColors(
    {
      ...ORB_BASE,
      hue: 165,
      backgroundColor: '#ffffff'
    },
    {
      ...ORB_BASE,
      hue: 0,
      backgroundColor: '#000000'
    }
  )
}

const SHAPE_GRID_BASE = {
  speed: 0.5,
  squareSize: 40,
  direction: 'diagonal',
  shape: 'square',
  hoverTrailAmount: 0,
  enableMouseInteraction: false
}

/** ShapeGrid props tuned per theme for JPilot chat backgrounds. */
export function getBetaShapeGridSettings() {
  return resolveCanvasColors(
    {
      ...SHAPE_GRID_BASE,
      borderColor: 'rgba(15, 23, 42, 0.14)',
      hoverFillColor: '#1e293b'
    },
    {
      ...SHAPE_GRID_BASE,
      borderColor: 'rgba(255, 255, 255, 0.22)',
      hoverFillColor: '#222222'
    }
  )
}

const FLOATING_LINES_BASE = {
  enabledWaves: ['top', 'middle', 'bottom'],
  lineCount: 4,
  lineDistance: [8, 6, 4],
  bendRadius: 11.5,
  bendStrength: 1.5,
  interactive: false,
  parallax: false,
  animationSpeed: 0.3,
  mixBlendMode: 'screen'
}

/** FloatingLines props tuned per theme for JPilot chat backgrounds. */
export function getBetaFloatingLinesSettings() {
  return resolveCanvasColors(
    {
      ...FLOATING_LINES_BASE,
      linesGradient: ['#06B6D4', '#7184df']
    },
    {
      ...FLOATING_LINES_BASE,
      linesGradient: ['#06B6D4', '#000000']
    }
  )
}

/** @param {'constellation'|'waves'|'drift'|'orbit'|'aurora'|'line-waves'|'galaxy'|'dot-field'|'threads'|'orb'|'shape-grid'|'floating-lines'} backgroundId */
export function getBetaBackgroundPalette(backgroundId) {
  switch (backgroundId) {
    case 'aurora':
      return getBetaAuroraSettings()
    case 'line-waves':
      return getBetaLineWavesSettings()
    case 'galaxy':
      return getBetaGalaxySettings()
    case 'dot-field':
      return getBetaDotFieldSettings()
    case 'threads':
      return getBetaThreadsSettings()
    case 'orb':
      return getBetaOrbSettings()
    case 'shape-grid':
      return getBetaShapeGridSettings()
    case 'floating-lines':
      return getBetaFloatingLinesSettings()
    case 'constellation':
      return resolveCanvasColors(
        { line: '0,58,108', dot: '0,82,150', lineOpacity: 0.48, dotOpacity: 0.92 },
        { line: '100,180,210', dot: '120,200,230', lineOpacity: 0.38, dotOpacity: 0.78 }
      )
    case 'waves':
      return resolveCanvasColors(
        { line: '0,72,128', opacity: 0.42 },
        { line: '100,180,210', opacity: 0.34 }
      )
    case 'drift':
      return resolveCanvasColors(
        { dot: '168,174,184', opacity: 0.72 },
        { dot: '58,64,74', opacity: 0.68 }
      )
    case 'orbit':
      return resolveCanvasColors(
        { ring: '176,182,192', dot: '156,162,172', ringOpacity: 0.52, dotOpacity: 0.68 },
        { ring: '52,58,68', dot: '72,78,88', ringOpacity: 0.56, dotOpacity: 0.72 }
      )
    default:
      return {}
  }
}

/** @deprecated Use getBetaBackgroundPalette() for theme-aware colors. */
export const BETA_BACKGROUND_PALETTES = {
  get constellation() {
    return getBetaBackgroundPalette('constellation')
  },
  get waves() {
    return getBetaBackgroundPalette('waves')
  },
  get drift() {
    return getBetaBackgroundPalette('drift')
  },
  get orbit() {
    return getBetaBackgroundPalette('orbit')
  },
  get aurora() {
    return getBetaBackgroundPalette('aurora')
  },
  get lineWaves() {
    return getBetaBackgroundPalette('line-waves')
  },
  get galaxy() {
    return getBetaBackgroundPalette('galaxy')
  },
  get dotField() {
    return getBetaBackgroundPalette('dot-field')
  },
  get threads() {
    return getBetaBackgroundPalette('threads')
  },
  get orb() {
    return getBetaBackgroundPalette('orb')
  },
  get shapeGrid() {
    return getBetaBackgroundPalette('shape-grid')
  },
  get floatingLines() {
    return getBetaBackgroundPalette('floating-lines')
  }
}
