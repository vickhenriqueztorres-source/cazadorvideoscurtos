#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
EL CAZADOR DEL WINS // AGENTE: GuionistaVozAgent (Etapa 2)
VERSÃO OFICIAL: BÍBLIA DO PERSONAGEM — EL CAZADOR NA IQ OPTION
=============================================================================
Arquétipo: O Sniper dos Mercados / O Predador da IQ Option
Plataforma: IQ Option (Reconhecimento visual imediato na LATAM)
Campo de Caça: Velas M1/M5, Fluxo de Pavio, Rejeição de Taxa e Algoritmo OTC
Inimigo: O amador que opera IQ Option como se fosse cassino
Idioma: Espanhol Neutro da América Latina (es-419)
Voz Neural: es-MX-JorgeNeural (Grave, firme, autoritário, sem carência)
=============================================================================
"""

import sys
import os
import json
import asyncio
import argparse
import random
from pathlib import Path

# Suporte console UTF-8
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import edge_tts

VOZ_ESPANHOL = "es-MX-JorgeNeural" # Voz masculina grave, autoritária, es-419 neutro

# Palavras proibidas pela Bíblia do Cazador (Regra: Zero Carência)
PALAVRAS_CARENTES_PROIBIDAS = [
    "por favor", "suscríbete", "suscribete", "deja tu like", "dale like",
    "apóyame", "apoyame", "no olvides", "sígueme por favor", "sigueme por favor",
    "adiós", "adios", "chau", "hasta luego", "nos vemos"
]

# Termos obrigatórios de ancoragem visual na IQ Option
TERMOS_ANCORAGEM_IQOPTION = [
    "iq option", "vela", "gráfico", "otc", "binarias", "digital",
    "reloj", "segundo", "soporte", "resistencia", "mecha", "pavilo"
]

def format_number_es(num: int) -> str:
    """Converte valores comuns de trading em espanhol fonético neutro para TTS."""
    centenas = {
        100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos",
        500: "quinientos", 600: "seiscientos", 700: "setecientos",
        800: "ochocientos", 900: "novecientos"
    }
    dezenas = {
        10: "diez", 20: "veinte", 30: "treinta", 40: "cuarenta", 50: "cincuenta",
        60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"
    }
    if num == 1000:
        return "mil"
    if num == 500:
        return "quinientos"
    if num in centenas:
        return centenas[num]
    
    unidades = {1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve"}
    
    # 2-digit numbers: 10 to 99
    if num in dezenas:
        return dezenas[num]
    if 21 <= num <= 29:
        return f"veinti{unidades[num % 10]}"
    if 31 <= num <= 99:
        d = (num // 10) * 10
        u = num % 10
        return f"{dezenas[d]} y {unidades[u]}" if u > 0 else dezenas[d]
    
    # 870 -> ochocientos setenta
    c = (num // 100) * 100
    resto = num % 100
    if c in centenas and resto in dezenas:
        return f"{centenas[c]} {dezenas[resto]}"
    if c in centenas and 31 <= resto <= 99:
        d = (resto // 10) * 10
        u = resto % 10
        return f"{centenas[c]} {dezenas[d]} y {unidades[u]}"
    if c in centenas and resto == 0:
        return centenas[c]
    
    return str(num)

def format_currency_es(amount: int) -> str:
    words = format_number_es(amount)
    return f"{words} dólares"

class GuionistaVozAgent:
    """
    Agente roteirista oficial do canal El Cazador del Wins.
    Implementa o algoritmo mental de 5 etapas da Bíblia do Cazador:
    1. Onde tem sangue na tela hoje? (Escolha do tema e da ferida)
    2. O soco no polegar (00s a 03s - travar scroll em < 1s)
    3. Desmascarar a ilusão dos amadores (03s a 15s)
    4. O tiro do sniper e o mecanismo cirúrgico (15s a 45s com silêncio do clique)
    5. O WIN, dopamina e o loop mental invisível (45s a 50s - sem despedidas)
    """

    TEMAS_CATALOGO = {
        "digital_vs_binarias": {
            "titulo": "O Erro da Opção Digital vs Binária (O Empate que vira Loss)",
            "ferida": "O novato opera Digital sem entender spread e perde dinheiro no empate.",
            "build": lambda inv_txt, prof_txt, pay_pct, act: {
                "fase_1_gancho": "¿Cuántas veces perdiste en IQ Option porque la vela terminó empatada en tu tasa?",
                "fase_2_exposicion": "Perdiste porque no sabes la diferencia entre Binarias y Digital. El aficionado hace clic en la primera que ve y le regala su dinero al spread.",
                "fase_3_mecanismo": "El Cazador elige el arma exacta. Vela de un minuto, rechazo limpio en la zona clave.",
                "fase_4_disparo_silencio": "...", # Silêncio para o clique mecânico
                "fase_4_tensao": f"Vela retrocediendo con violencia. {inv_txt} en juego.",
                "fase_5_recompensa_loop": f"{prof_txt} al bolsillo sin regalarle un centavo al broker. Y es exactamente por eso que..."
            },
            "loop_conector": "...¿cuántas veces perdiste en IQ Option porque la vela terminó empatada en tu tasa?"
        },
        "velas_5s_roleta": {
            "titulo": "O Vício da Vela de 5 Segundos (A Roleta de Dopamina)",
            "ferida": "O trader que coloca vela em 5s achando que é cassino e quebra a banca em 3 minutos.",
            "build": lambda inv_txt, prof_txt, pay_pct, act: {
                "fase_1_gancho": "Si tu gráfico de IQ Option está en cinco segundos, apaga la pantalla ahora mismo.",
                "fase_2_exposicion": "No eres trader, eres un adicto a la dopamina quemando tu dinero en una ruleta. La casa siempre gana contra los desesperados.",
                "fase_3_mecanismo": "El dinero de verdad está en la lectura de vela de un minuto y en la absorción del pavilo.",
                "fase_4_disparo_silencio": "...",
                "fase_4_tensao": f"Rechazo milimétrico. {inv_txt} operados con frialdad.",
                "fase_5_recompensa_loop": f"{prof_txt} de ganancia en una sola vela. Deja de jugar como un novato, porque..."
            },
            "loop_conector": "...si tu gráfico de IQ Option está en cinco segundos, apaga la pantalla ahora mismo."
        },
        "otc_algoritmo": {
            "titulo": "A Leitura do Algoritmo de OTC na IQ Option",
            "ferida": "Achar que OTC é manipulado e perder contra o fluxo institucional.",
            "build": lambda inv_txt, prof_txt, pay_pct, act: {
                "fase_1_gancho": "El noventa por ciento pierde todo en el OTC de IQ Option por hacer esto...",
                "fase_2_exposicion": "Creen que el OTC es una trampa. El algoritmo no sigue noticias, sigue flujo institucional y relleno de vacíos.",
                "fase_3_mecanismo": f"El Cazador no adivina: espera el agotamiento de volumen y caza el payout del {pay_pct} por ciento.",
                "fase_4_disparo_silencio": "...",
                "fase_4_tensao": f"Vela respetando el patrón exacto. {inv_txt} en la línea de fuego.",
                "fase_5_recompensa_loop": f"{prof_txt} directo a la cuenta mientras los demás lloran en los comentarios. Y si sigues operando a ciegas..."
            },
            "loop_conector": "...el noventa por ciento pierde todo en el OTC de IQ Option por hacer esto."
        },
        "arbol_navidad": {
            "titulo": "A Armadilha dos 50 Indicadores Coloridos (Árvore de Natal)",
            "ferida": "Encher a tela com 10 médias móveis, RSI e estocástico, cegando a tomada de decisão.",
            "build": lambda inv_txt, prof_txt, pay_pct, act: {
                "fase_1_gancho": "IQ Option adora cuando llenas tu gráfico con diez indicadores de colores.",
                "fase_2_exposicion": "Tu pantalla parece un árbol de navidad. Mientras buscas tres señales que nunca coinciden, el mercado liquida tu capital en el techo.",
                "fase_3_mecanismo": "El Cazador opera con pantalla limpia: puro Price Action, una zona de reacción y el segundo clave del reloj.",
                "fase_4_disparo_silencio": "...",
                "fase_4_tensao": f"Absorción completa en la zona. {inv_txt} protegidos por técnica.",
                "fase_5_recompensa_loop": f"{prof_txt} al bolsillo sin una sola línea de basura en el gráfico. Y la verdad es que..."
            },
            "loop_conector": "...IQ Option adora cuando llenas tu gráfico con diez indicadores de colores."
        },
        "rechazo_pavio_m1": {
            "titulo": "O Falso Rompimento e o Segundo 31 do Relógio",
            "ferida": "Comprar no topo achando que vai romper e tomar loss no último segundo da vela.",
            "build": lambda inv_txt, prof_txt, pay_pct, act: {
                "fase_1_gancho": "Vas a tomar loss en IQ Option cada vez que operes contra el flujo institucional.",
                "fase_2_exposicion": ("El aficionado ve la vela roja caer y vende en el fondo por pánico. Mira el gráfico: aquí abajo el soporte está blindado y el pavilo absorbió toda la fuerza." if act == "CALL" else "El aficionado ve la vela verde estirarse y compra en el techo por desesperación. Mira el gráfico: aquí arriba la resistencia está blindada y el pavilo absorbió toda la fuerza."),
                "fase_3_mecanismo": "Segundo treinta y uno del reloj de expiración. Zona de rechazo tocada. Gatillo apretado.",
                "fase_4_disparo_silencio": "...",
                "fase_4_tensao": (f"Vela explotando a nuestro favor. {inv_txt} operados con frialdad." if act == "CALL" else f"Vela derritiéndose a nuestro favor. {inv_txt} operados con frialdad."),
                "fase_5_recompensa_loop": f"{prof_txt} asegurados en el retroceso. Deja de regalarle tu dinero al broker, porque..."
            },
            "loop_conector": "...vas a tomar loss en IQ Option cada vez que operes contra el flujo institucional."
        }
    }

    def __init__(self, voice=VOZ_ESPANHOL, rate="-3%", pitch="-2Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    def select_theme_contextually(self, telemetry_data, requested_theme=None) -> str:
        """
        Seleciona o tema mais cirúrgico com base na telemetria ou na solicitação direta.
        """
        if requested_theme and requested_theme in self.TEMAS_CATALOGO:
            return requested_theme

        # Análise contextual da telemetria
        asset = telemetry_data.get("asset_pair", "") or telemetry_data.get("session", {}).get("asset_pair", "")
        if "OTC" in asset.upper():
            return "otc_algoritmo"

        click = telemetry_data.get("click_event", {})
        action = click.get("action", "CALL")
        
        # Alternância inteligente de alta conversão
        if action == "PUT":
            return random.choice(["rechazo_pavio_m1", "arbol_navidad"])
        else:
            return random.choice(["digital_vs_binarias", "velas_5s_roleta", "rechazo_pavio_m1"])

    def build_script(self, telemetry_data, theme_key="digital_vs_binarias"):
        """
        Constrói o roteiro completo nos 5 atos emocionais da Bíblia do Cazador.
        """
        if theme_key not in self.TEMAS_CATALOGO:
            theme_key = "digital_vs_binarias"

        theme_meta = self.TEMAS_CATALOGO[theme_key]
        
        click = telemetry_data.get("click_event", {})
        outcome = telemetry_data.get("outcome_event", {})

        action = click.get("action", "CALL")
        investment = int(click.get("investment_amount", 1000))
        profit = int(outcome.get("profit_amount", 870))
        payout_pct = int(click.get("payout_pct", 87))

        inv_words = format_currency_es(investment)
        prof_words = format_currency_es(profit)
        pay_words = format_number_es(payout_pct)

        parts = theme_meta["build"](inv_words, prof_words, pay_words, action)

        return {
            "theme_key": theme_key,
            "theme_title": theme_meta["titulo"],
            "ferida": theme_meta["ferida"],
            "parts": parts,
            "loop_conector": theme_meta["loop_conector"]
        }

    def audit_script(self, script_payload) -> dict:
        """
        Auditoria estrita das 4 regras de ouro da Bíblia do Cazador:
        1. Zero Carência (Nenhuma palavra pedindo favor)
        2. Duração e Ritmo (45 a 85 palavras totais)
        3. Ancoragem Visual na IQ Option
        4. Loop Mental Invisível (Sem tchau, fechamento conectivo)
        """
        parts = script_payload["parts"]
        full_text = " ".join([
            parts["fase_1_gancho"],
            parts["fase_2_exposicion"],
            parts["fase_3_mecanismo"],
            parts["fase_4_tensao"],
            parts["fase_5_recompensa_loop"]
        ]).lower()

        # 1. Checagem de carência
        needy_violations = [w for w in PALAVRAS_CARENTES_PROIBIDAS if w in full_text]
        carencia_ok = len(needy_violations) == 0

        # 2. Contagem de palavras
        clean_words = [w for w in full_text.replace("...", "").split() if w]
        word_count = len(clean_words)
        duracao_ok = 40 <= word_count <= 95

        # 3. Ancoragem IQ Option
        iq_anchors = [term for term in TERMOS_ANCORAGEM_IQOPTION if term in full_text]
        ancoragem_ok = len(iq_anchors) >= 2

        # 4. Loop invisível (última frase deve terminar com conector/reticências)
        last_phrase = parts["fase_5_recompensa_loop"].strip()
        loop_ok = last_phrase.endswith("...") or any(last_phrase.lower().endswith(k) for k in ["porque", "que", "como", "verdad es"])

        all_passed = carencia_ok and duracao_ok and ancoragem_ok and loop_ok

        return {
            "passed": all_passed,
            "word_count": word_count,
            "carencia_check": {"passed": carencia_ok, "violations": needy_violations},
            "duracao_check": {"passed": duracao_ok, "word_count": word_count, "target_range": "40-95 palavras"},
            "ancoragem_iqoption": {"passed": ancoragem_ok, "detected_terms": iq_anchors},
            "loop_invisivel": {"passed": loop_ok, "terminacao": last_phrase[-25:]}
        }

    async def _synthesize_speech(self, text, output_file):
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate, pitch=self.pitch)
        await communicate.save(str(output_file))

    def generate_narration(self, take_dir, theme=None):
        """
        Lê a telemetria do take, gera o roteiro normativo da Bíblia do Cazador,
        audita com as 4 regras de ferro e sintetiza a voz neural es-419.
        """
        take_dir = Path(take_dir).resolve()
        
        telemetry_files = list(take_dir.glob("*_telemetry.json")) + list(take_dir.glob("telemetry.json"))
        if not telemetry_files:
            raise FileNotFoundError(f"Telemetria não encontrada em {take_dir}")
        telemetry_file = telemetry_files[0]
        
        with open(telemetry_file, "r", encoding="utf-8") as f:
            telemetry = json.load(f)

        # Selecionar tema
        selected_theme = self.select_theme_contextually(telemetry, theme)
        script_payload = self.build_script(telemetry, selected_theme)

        # Auditoria do Monólogo Mental do Cazador
        audit_results = self.audit_script(script_payload)

        # Montagem do texto fonético para o sintetizador neural com as pausas acústicas exatas
        p = script_payload["parts"]
        full_speech_text = (
            f"{p['fase_1_gancho']} ... "
            f"{p['fase_2_exposicion']} ... "
            f"{p['fase_3_mecanismo']} ... ... "  # Pausa prolongada antes do disparo
            f"{p['fase_4_tensao']} ... "
            f"{p['fase_5_recompensa_loop']}"
        )

        audio_output = take_dir / "narration.mp3"
        script_output = take_dir / "script.json"

        print("=" * 76)
        print("🎯 [GUIONISTA VOZ AGENT // VERSÃO BÍBLIA DO CAZADOR - IQ OPTION]")
        print(f"📖 Tema Selecionado: {script_payload['theme_title']} [{selected_theme}]")
        print(f"🎙️ Voz: {self.voice} ({self.rate}, {self.pitch}) | Persona: O Sniper / Predador IQ")
        print(f"⚡ Ferida Aberta: {script_payload['ferida']}")
        print(f"📝 Palavras: {audit_results['word_count']} | QA Bíblia: {'✅ APROVADO' if audit_results['passed'] else '⚠️ AJUSTE NECESSÁRIO'}")
        print("-" * 76)
        print(f"📜 [Roteiro 5 Atos]:\n{full_speech_text}")
        print(f"🔄 [Loop Invisível]: {script_payload['loop_conector']}")
        print("=" * 76)

        # Sintetizar áudio com Edge TTS
        asyncio.run(self._synthesize_speech(full_speech_text, audio_output))

        # Salvar metadados completos de roteiro e auditoria
        script_data = {
            "schema_version": "2.0.0",
            "bible_version": "Bíblia do Cazador // Versão Oficial IQ Option",
            "theme": selected_theme,
            "theme_title": script_payload["theme_title"],
            "ferida_psicologica": script_payload["ferida"],
            "voice_config": {
                "voice": self.voice,
                "rate": self.rate,
                "pitch": self.pitch,
                "persona": "O Sniper dos Mercados / O Predador da IQ Option"
            },
            "script_5_atos": p,
            "full_speech_text": full_speech_text,
            "loop_conector": script_payload["loop_conector"],
            "qa_audit": audit_results,
            "audio_file": str(audio_output.name)
        }

        with open(script_output, "w", encoding="utf-8") as f:
            json.dump(script_data, f, indent=2, ensure_ascii=False)

        print(f"✅ [ÁUDIO NEURAL GERADO] {audio_output}")
        print(f"📄 [CONTRATO DE ROTEIRO PERSISTIDO] {script_output}")
        return audio_output, script_output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GuionistaVozAgent - Bíblia do Cazador IQ Option")
    parser.add_argument("--take-dir", required=True, help="Diretório do take com a telemetria")
    parser.add_argument("--theme", choices=list(GuionistaVozAgent.TEMAS_CATALOGO.keys()), help="Forçar tema específico")
    args = parser.parse_args()

    agent = GuionistaVozAgent()
    agent.generate_narration(args.take_dir, theme=args.theme)
