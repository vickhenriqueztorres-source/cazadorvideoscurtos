import cv2
import numpy as np

def draw_tier3_hud(frame, current_balance="$100.00", action="PUT", amount=100, payout_pct=82, profit_amount=82, stage="ACTIVE"):
    """
    Desenha o HUD Operacional e de Saldo no Tier 3 (lado esquerdo inferior).
    Preenche perfeitamente de x=10 até x=575, y=1210 até y=1560.
    Cobre completamente qualquer recorte e exibe Saldo e Momento CALL/PUT com máxima legibilidade.
    """
    hud_x1, hud_y1, hud_x2, hud_y2 = 15, 1210, 570, 1545
    
    # 1. Background sólido oficial IQ Option Dark Navy
    bg_color = (25, 20, 15)
    cv2.rectangle(frame, (hud_x1, hud_y1), (hud_x2, hud_y2), bg_color, -1)
    
    # Borda em ouro/ciano
    border_color = (0, 215, 255) if stage != "WIN" else (0, 255, 136)
    cv2.rectangle(frame, (hud_x1, hud_y1), (hud_x2, hud_y2), border_color, 2, cv2.LINE_AA)
    
    # Topo do HUD: Cabeçalho do Card
    cv2.rectangle(frame, (hud_x1, hud_y1), (hud_x2, hud_y1 + 155), (32, 25, 20), -1)
    cv2.line(frame, (hud_x1, hud_y1 + 155), (hud_x2, hud_y1 + 155), (60, 50, 42), 1, cv2.LINE_AA)
    
    # Status Saldo
    dot_color = (0, 255, 136) if stage in ["INIT", "WIN"] else (0, 140, 255)
    cv2.circle(frame, (hud_x1 + 25, hud_y1 + 35), 7, dot_color, -1, cv2.LINE_AA)
    cv2.putText(frame, "SALDO EN CUENTA", (hud_x1 + 45, hud_y1 + 42), cv2.FONT_HERSHEY_DUPLEX, 0.65, (180, 200, 220), 1, cv2.LINE_AA)
    
    # Saldo Valor (Gigante e sem cortes)
    bal_color = (0, 255, 136) if stage == "WIN" else (255, 255, 255)
    cv2.putText(frame, current_balance, (hud_x1 + 25, hud_y1 + 105), cv2.FONT_HERSHEY_DUPLEX, 1.30, bal_color, 3, cv2.LINE_AA)
    cv2.putText(frame, "USD", (hud_x1 + 280, hud_y1 + 105), cv2.FONT_HERSHEY_DUPLEX, 0.70, (0, 215, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "ACTIVO: PEN/USD (OTC) DIGITAL", (hud_x1 + 25, hud_y1 + 138), cv2.FONT_HERSHEY_DUPLEX, 0.50, (150, 165, 185), 1, cv2.LINE_AA)
    
    # 2. Seção do Momento de Operação (CALL / PUT)
    btn_color = (0, 60, 220) if action == "PUT" else (0, 180, 70)
    cv2.rectangle(frame, (hud_x1 + 15, hud_y1 + 175), (hud_x2 - 15, hud_y1 + 230), btn_color, -1)
    cv2.rectangle(frame, (hud_x1 + 15, hud_y1 + 175), (hud_x2 - 15, hud_y1 + 230), (255, 255, 255), 1, cv2.LINE_AA)
    
    label_action = f"MOMENTO: {action} (LOWER)" if action == "PUT" else f"MOMENTO: {action} (HIGHER)"
    cv2.putText(frame, label_action, (hud_x1 + 30, hud_y1 + 212), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    
    # Detalhes da Ordem
    cv2.putText(frame, f"INVERSION: ${amount}", (hud_x1 + 25, hud_y1 + 270), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, f"PAYOUT: +{payout_pct}%  |  LUCRO: +${profit_amount}.00", (hud_x1 + 25, hud_y1 + 310), cv2.FONT_HERSHEY_DUPLEX, 0.58, (0, 230, 118), 1, cv2.LINE_AA)
    
    return frame

if __name__ == "__main__":
    frame = cv2.imread("win_take_26s.png")
    out = draw_tier3_hud(frame, current_balance="$0.00", action="PUT", amount=100, payout_pct=82, profit_amount=82, stage="ACTIVE")
    cv2.imwrite("scratch_tier3_hud_real.png", out)
    print("Sucesso! scratch_tier3_hud_real.png gerado.")
