# Technical plan

1. Establish direct CDP lifecycle, owned profile, local server, explicit state and SQLite session.
2. Install transparent bindings/hooks before navigation and before worker scripts.
3. Capture visual selection and inspect DOM/SVG/Shadow before graphics layers.
4. Correlate Canvas2D by geometry and expose WebGL draw/state candidates without false certainty.
5. Validate each layer in real Chromium, persist evidence/hashes, then add differential and active
   experiments only after the passive detector is stable.

