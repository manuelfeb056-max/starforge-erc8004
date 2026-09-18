# Hitos semanales — Starforge × ERC-8004 (deadline 13 oct 2026)

## Semana 1 · 18–24 sep — Port y verificación
- [ ] Compilar contratos (`npx solc` / hardhat) y corregir hasta build limpio.
- [ ] Re-verificar paridad: port `StarforgeGame.spin` vs simulador Python
      (`~/workspace/chain-jam/starforge/simulator/`) — 15/15 semillas.
- [ ] Tests del ciclo Arena: open → spin → picks → gamble → settle; forfeit.
- [ ] Tests de `AgentReputation` con mocks de los registros ERC-8004.
- [ ] Resolver preguntas abiertas de `docs/ERC8004_NOTES.md` (deployment
      oficial en Monad testnet, firma exacta de `giveFeedback`).

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

## Semana 4 · 9–13 oct — Submission
- [ ] Repo público en GitHub (requiere `gh auth login` en la VM).
- [ ] Write-up: problema, solución, arquitectura, demo, links.
- [ ] Submit final en la plataforma antes del 13 oct 23:59.
- [ ] Post-mortem y lecciones → NueveStudio.

## Dependencias externas (no-code, solo Mannuel o navegador)
- `gh auth login` en la VM → repo público (bloquea semanas 3–4).
- Crear proyecto en hackathon.monad.xyz (browser task, semana 3).
