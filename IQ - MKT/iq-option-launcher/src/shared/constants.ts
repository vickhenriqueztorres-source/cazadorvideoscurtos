import type { DiagnosticsSnapshot, ExtensionSettings } from './types';

export const STORAGE_KEYS = {
  settings: 'settings',
  diagnostics: 'diagnostics'
} as const;

export const DEFAULT_SETTINGS: ExtensionSettings = {
  enabled: true,
  themeId: 'default'
};

export const EMPTY_DIAGNOSTICS: DiagnosticsSnapshot = {
  status: 'disabled',
  domainAuthorized: false,
  routeSupported: false,
  themeId: 'default',
  themeName: 'Tema Azul',
  validRules: 0,
  totalRules: 0,
  elementsChanged: 0,
  openShadowRoots: 0,
  warnings: [],
  updatedAt: new Date(0).toISOString()
};

export const STYLE_MARKER = 'data-visual-theme-assistant';
export const ROUTE_SETTLE_MS = 350;
export const OBSERVER_DEBOUNCE_MS = 180;
