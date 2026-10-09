# Target selection

O painel arma `target-selector.js` via CDP em cada contexto de página/frame. O script aplica cursor e
overlay temporários, captura um único clique, impede apenas esse clique e envia coordenadas, DPR,
scroll, URL e `elementsFromPoint`. Depois remove listeners, overlay e restaura o cursor.

