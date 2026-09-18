# Hitos semanales — Starforge × ERC-8004 (deadline 13 oct 2026)

## Semana 1 · 18–24 sep — Port y verificación
- [x] Compilar contratos (solc 0.8.28 vía py-solc-x) — build limpio.
      ⚠️ Hallazgo: `_drawSymbol` usaba `(uint16(_nextByte(c))<<8)|uint16(_nextByte(c))`
      en una sola expresión. El orden de evaluación de operandos con efectos
      laterales NO está garantizado en Solidity: solc 0.8.28 evalúa de derecha
      a izquierda y el par de bytes salía invertido vs el simulador de referencia
      (el original con 0.8.30 evaluaba izq→der y pasaba 15/15 por suerte).
      Corregido con temporales explícitos `b0`/`b1` en el port.
- [x] Paridad re-verificada: port `StarforgeGame.spin/applyPicks/applyGamble`
      vs `~/workspace/chain-jam/starforge/simulator/parity.py` —
      **15 semillas × artifacts {0x00, 0x07}, 250 checks, 0 fallos**
      (`tests/parity_port.py`: stage, gridWinBps, stepCount, stepWins,
      stepPats, grids byte-a-byte, prizes, picksBps, totalBps, gambleWin).
- [x] Tests del ciclo Arena: open → spin → picks → gamble → settle; forfeit —
      **34/34 pass** (`tests/test_arena.py`, py-evm local): settle automático
      sin supernova, supernova collect, supernova gamble (coin verificada),
      forfeit devuelve wager, guards (ZeroWager/NotPlayer/BadPicks/BadStage/
      OnlyOwner/ReputationAlreadySet), cap payoutFor 1000x, expectedPayout 97.60%.
- [x] Tests de `AgentReputation` con mocks ERC-8004: linkAgent (owner y
      agentWallet), feedback = RTP de sesión en bps con tags
      keccak("starforge")/keccak("session"), lifetimeRtpBps, agentSessions;
      jugador no linkeado no genera feedback. **Nota de diseño:** un
      AgentReputation solo puede servir a un Arena (setArena one-time).
- [ ] Resolver preguntas abiertas de `docs/ERC8004_NOTES.md` (deployment
      oficial en Monad testnet, firma exacta de `giveFeedback`).
- [x] `agent/play-agent.py` completado (web3.py): register → linkAgent →
      loop openSession/fulfillSpin/submitPicks/fulfillGamble con espera de
      randomness; verificado end-to-end contra cadena local
      (`tests/test_agent_local.py`: sesión supernova real, payout y feedback
      on-chain correctos). Sin deploys reales aún.
- [x] Proyecto ya creado en hackathon.monad.xyz (18 sep): "Starforge × ERC-8004",
      track **Trust, Identity & AI Infrastructure** seleccionado.

## Semana 2 · 25 sep–1 oct — Integración ERC-8004 + testnet
- [ ] Desplegar (o reutilizar) Identity + Reputation Registry en Monad testnet.
- [ ] Desplegar Game → BlockhashRandomness → Arena → AgentReputation; wiring
      `setReputation` / `setArena`.
- [ ] Registrar agente ERC-8004 (data-URI) y `linkAgent`.
- [ ] Completar `agent/play-agent.py` (web3.py): loop de sesiones end-to-end
      en testnet; verificar feedback en el Reputation Registry.
- [ ] Indexer mínimo de eventos → JSON para el leaderboard.

## Semana 3 · 2–8 oct — Demo y pulido
- [ ] Frontend: leaderboard de agentes por RTP lifetime (lee indexer).
- [ ] Página del juego (reutilizar `frontend/` de Chain Jam) apuntando al Arena.
- [ ] Video demo (60–90s): agente se registra, juega, reputación on-chain.
- [ ] (Opcional) entrada en el Validation Registry con evidencia Monte Carlo.
- [ ] Crear el proyecto en hackathon.monad.xyz (nombre + descripción) y
      elegir el track **Trust, Identity & AI Infrastructure**.
      ✅ HECHO el 18 sep (browser): proyecto "Starforge × ERC-8004" creado,
      track seleccionado. Solo falta la submission formal (abre 22 sep).

## Semana 4 · 9–13 oct — Submission
- [ ] Repo público en GitHub (requiere `gh auth login` en la VM).
- [ ] Write-up: problema, solución, arquitectura, demo, links.
- [ ] Submit final en la plataforma antes del 13 oct 23:59.
- [ ] Post-mortem y lecciones → NueveStudio.

## Dependencias externas (no-code, solo Mannuel o navegador)
- `gh auth login` en la VM → repo público (bloquea semanas 3–4).
- Crear proyecto en hackathon.monad.xyz (browser task, semana 3).
