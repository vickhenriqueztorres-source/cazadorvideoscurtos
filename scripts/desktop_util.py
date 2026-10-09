#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitário de Conexão com o Desktop Interativo (WinSta0\default) no Windows.
Garante que threads em subprocessos ou sandboxes tenham acesso direto ao display do usuário.
"""
import ctypes

user32 = ctypes.windll.user32

def attach_to_default_desktop():
    """Garante que a thread atual esteja anexada ao desktop interativo padrão."""
    try:
        hdesk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if hdesk:
            res = user32.SetThreadDesktop(hdesk)
            return bool(res)
    except Exception as e:
        print(f"[AVISO] Não foi possível anexar ao desktop padrão: {e}")
    return False

if __name__ == "__main__":
    success = attach_to_default_desktop()
    print("Desktop anexado com sucesso:", success)
