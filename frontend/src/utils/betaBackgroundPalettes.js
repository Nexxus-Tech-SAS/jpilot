/** Color palettes for JPilot Beta chat animated backgrounds. */

import { resolveCanvasColors } from './canvasTheme'

/** All beta backgrounds use a theme-matched solid base (white / near-black). */
export const BETA_BACKGROUND_BASE = 'theme'

/** @param {string} backgroundId */
export function getBetaBackgroundBase(backgroundId) {
  void backgroundId
  return BETA_BACKGROUND_BASE
}

/** @param {'constellation'|'waves'|'drift'|'orbit'} backgroundId */
export function getBetaBackgroundPalette(backgroundId) {
  switch (backgroundId) {
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
  }
}
