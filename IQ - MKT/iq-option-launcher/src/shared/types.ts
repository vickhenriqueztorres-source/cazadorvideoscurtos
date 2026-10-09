export type AllowedCssProperty =
  | 'color'
  | 'background-color'
  | 'border-color'
  | 'outline-color'
  | 'fill'
  | 'stroke';

export interface ThemeRule {
  selector: string;
  properties: Partial<Record<AllowedCssProperty, string>>;
}

export interface Theme {
  id: string;
  name: string;
  rules: ThemeRule[];
}

export interface PlatformProfile {
  id: string;
  version: string;
  matchPatterns: string[];
  supportedRoutes: string[];
  allowedSelectors: string[];
  blockedSelectorPatterns: string[];
}

export interface Policy {
  allowedCssProperties: AllowedCssProperty[];
  blockedSelectors: string[];
  blockedTokens: string[];
  allowFrames: boolean;
  allowShadowDomOpen: boolean;
  allowShadowDomClosed: boolean;
}

export type ThemeStatus = 'active' | 'disabled' | 'incompatible' | 'error';

export interface DiagnosticWarning {
  code: string;
  message: string;
  selector?: string;
}

export interface DiagnosticsSnapshot {
  status: ThemeStatus;
  domainAuthorized: boolean;
  routeSupported: boolean;
  themeId: string;
  themeName: string;
  validRules: number;
  totalRules: number;
  elementsChanged: number;
  openShadowRoots: number;
  warnings: DiagnosticWarning[];
  updatedAt: string;
}

export interface ExtensionSettings {
  enabled: boolean;
  themeId: string;
}

export type RuntimeMessage =
  | { type: 'GET_DIAGNOSTICS' }
  | { type: 'SET_ENABLED'; enabled: boolean }
  | { type: 'SET_THEME'; themeId: string }
  | { type: 'RESTORE_ORIGINAL' }
  | { type: 'REFRESH_THEME' };

export interface ValidationIssue {
  code: string;
  message: string;
}

export interface ValidatedRule {
  selector: string;
  declarations: Array<[AllowedCssProperty, string]>;
}
