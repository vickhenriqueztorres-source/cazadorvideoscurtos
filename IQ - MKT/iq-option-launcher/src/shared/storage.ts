import { DEFAULT_SETTINGS, EMPTY_DIAGNOSTICS, STORAGE_KEYS } from './constants';
import type { DiagnosticsSnapshot, ExtensionSettings } from './types';

export async function getSettings(): Promise<ExtensionSettings> {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.settings);
  return { ...DEFAULT_SETTINGS, ...(stored[STORAGE_KEYS.settings] as Partial<ExtensionSettings> | undefined) };
}

export async function setSettings(settings: ExtensionSettings): Promise<void> {
  await chrome.storage.local.set({ [STORAGE_KEYS.settings]: settings });
}

export async function getStoredDiagnostics(): Promise<DiagnosticsSnapshot> {
  const stored = await chrome.storage.local.get(STORAGE_KEYS.diagnostics);
  return { ...EMPTY_DIAGNOSTICS, ...(stored[STORAGE_KEYS.diagnostics] as Partial<DiagnosticsSnapshot> | undefined) };
}

export async function setStoredDiagnostics(diagnostics: DiagnosticsSnapshot): Promise<void> {
  await chrome.storage.local.set({ [STORAGE_KEYS.diagnostics]: diagnostics });
}
