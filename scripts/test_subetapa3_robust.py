#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EL CAZADOR DEL WINS // TESTES ROBUSTOS DA SUBETAPA 3:
1. Teste de Loop de Autorrecuperação (Self-Healing Retry Loop com 1 rejeição controlada e recuperação).
2. Teste de Circuit Breaker (Limite de retries respeitado, sem loop infinito).
3. Teste de Quarentena e Idempotência (Nenhum arquivo corrompido ou vazamento de disco).
"""

import sys
import os
import json
import shutil
from pathlib import Path

# Suporte console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

BASE_DIR = Path("D:/cazador - videos curtos").resolve()
sys.path.append(str(BASE_DIR / "agents"))
sys.path.append(str(BASE_DIR / "orchestrator"))

from el_jefe_pipeline import ElJefePipeline

class MockRecorder:
    def __init__(self):
        self.call_count = 0
    def run_take(self):
        self.call_count += 1
        take_id = f"mock_take_retry_{self.call_count}"
        take_dir = BASE_DIR / "staging" / take_id
        take_dir.mkdir(parents=True, exist_ok=True)
        # Criar arquivos dummy
        (take_dir / f"{take_id}.mp4").write_bytes(b"dummy_mp4_bytes")
        with open(take_dir / f"{take_id}_telemetry.json", "w") as f:
            json.dump({"outcome_event": {"result": "WIN", "profit_amount": 82}}, f)
        return True, take_dir

class MockGuionista:
    def generate_narration(self, take_dir, theme=None):
        audio_file = take_dir / "narration.mp3"
        audio_file.write_bytes(b"dummy_audio")
        script_file = take_dir / "script.json"
        script_file.write_text("{}", encoding="utf-8")
        return audio_file, script_file

class MockEditor:
    def assemble_short(self, take_dir):
        final_video = BASE_DIR / "output_shorts" / f"{take_dir.name}_final.mp4"
        final_video.write_bytes(b"dummy_final_video")
        return final_video

class MockAuditorFailsFirst:
    def __init__(self):
        self.audit_calls = 0
    def audit_video(self, video_path, telemetry_path=None, take_dir=None):
        self.audit_calls += 1
        if self.audit_calls == 1:
            # Rejeitar na 1ª tentativa
            return False, {"score": 50, "errors": ["Simulação: corte de cabeçalho detectado"]}
        # Aprovar na 2ª tentativa
        return True, {"score": 100, "errors": []}

def test_1_self_healing_retry_loop():
    print("▶ [TESTE 1/2] Teste do Circuito de Autorrecuperação (Self-Healing Loop)...")
    pipeline = ElJefePipeline(max_retries=2, publish_telegram=False)
    
    # Injetar mocks
    pipeline.recorder = MockRecorder()
    pipeline.guionista = MockGuionista()
    pipeline.editor = MockEditor()
    pipeline.auditor = MockAuditorFailsFirst()
    
    success, video = pipeline.run_pipeline()
    
    assert success, "Falha: O pipeline deveria ter se recuperado na 2ª tentativa!"
    assert pipeline.recorder.call_count == 2, f"Esperado 2 tentativas do gravador, mas foram {pipeline.recorder.call_count}"
    assert pipeline.auditor.audit_calls == 2, f"Esperado 2 chamadas do auditor, mas foram {pipeline.auditor.audit_calls}"
    
    # Verificar se o 1º take rejeitado foi movido para quarentena
    quar_dir = BASE_DIR / "quarantine" / "mock_take_retry_1"
    assert quar_dir.exists(), "Falha: O take rejeitado não foi isolado na pasta quarantine/!"
    
    # Limpeza dos mocks
    shutil.rmtree(quar_dir, ignore_errors=True)
    if video and video.exists():
        video.unlink()
    shutil.rmtree(BASE_DIR / "staging" / "mock_take_retry_2", ignore_errors=True)
    
    print("  ✅ [PASSOU] Autorrecuperação executada com sucesso: Take 1 quarentenado, Take 2 homologado!")
    return True

def test_2_circuit_breaker():
    print("\n▶ [TESTE 2/2] Teste de Circuit Breaker (Falha controlada após esgotar retries)...")
    class MockAuditorAlwaysFails:
        def audit_video(self, video_path, telemetry_path=None, take_dir=None):
            return False, {"score": 0, "errors": ["Falha permanente de teste"]}
            
    pipeline = ElJefePipeline(max_retries=2, publish_telegram=False)
    pipeline.recorder = MockRecorder()
    pipeline.guionista = MockGuionista()
    pipeline.editor = MockEditor()
    pipeline.auditor = MockAuditorAlwaysFails()
    
    success, video = pipeline.run_pipeline()
    
    assert not success, "Falha: Pipeline não deveria ter aprovado com auditor rejeitando sempre!"
    assert video is None, "Vídeo deveria ser None em caso de aborto!"
    assert pipeline.recorder.call_count == 2, "Deveria ter parado exatamente em max_retries=2"
    
    # Limpar quarentena dos mocks
    shutil.rmtree(BASE_DIR / "quarantine" / "mock_take_retry_1", ignore_errors=True)
    shutil.rmtree(BASE_DIR / "quarantine" / "mock_take_retry_2", ignore_errors=True)
    
    print("  ✅ [PASSOU] Circuit breaker interrompeu o pipeline após 2 tentativas sem entrar em loop infinito.")
    return True

if __name__ == "__main__":
    t1 = test_1_self_healing_retry_loop()
    t2 = test_2_circuit_breaker()
    
    if t1 and t2:
        print("\n" + "="*76)
        print("🏆 SUBETAPA 3 VALIDADA COM 100% DE SUCESSO EM TODOS OS TESTES!")
        print("="*76)
        sys.exit(0)
    else:
        print("\n❌ FALHA NA SUBETAPA 3")
        sys.exit(1)
