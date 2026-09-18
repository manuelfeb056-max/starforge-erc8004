# Arquitectura — Starforge × ERC-8004

Track: **Monad Metropolis → Trust, Identity & AI Infrastructure**
($30K). Deadline: **13 oct 2026**.

## Idea en una línea

Agentes de IA con identidad on-chain **ERC-8004** juegan STARFORGE
(arcade slot con RNG verificable y RTP publicado del 97.60%) de forma
autónoma; cada partida liquidada se publica como **feedback de reputación
on-chain firmado por el propio contrato del juego** — un track record
imposible de falsificar. Leaderboard de agentes por RTP real.

## Por qué calza con el track

La página del track menciona explícitamente **"agent identity ERC-8004"**
y primitives para "internet AI-native". Entregamos exactamente eso:
identidad de agente + reputación verificable por juego, no promesas.

## Componentes

```
┌──────────────┐     register()      ┌─────────────────────┐
│  play-agent  │ ─────────────────▶  │ ERC-8004 Identity   │
│  (bot python)│     agent NFT       │ Registry (testnet)  │
└──────┬───────┘                     └─────────────────────┘
       │ linkAgent(agentId)                  ▲
       ▼                                     │ ownerOf / getAgentWallet
┌──────────────────┐   recordSession   ┌──────────────┐
│ StarforgeArena   │ ───────────────▶  │AgentReputation│──▶ Reputation Registry
│ (sesiones+escrow)│   wager, payout   │(link+feedback)│    giveFeedback(rtpBps,
└──────┬───────────┘                   └──────────────┘    tag1=starforge,
       │ spin/picks/gamble                        tag2=session)
       ▼
┌──────────────────┐     ┌──────────────────┐
│  StarforgeGame   │     │ IRandomness      │
│  (matemática     │     │ BlockhashRandom. │ (testnet)
│   pura, 1:1 con  │     └──────────────────┘
│   math-spec.json)│
└──────────────────┘

Off-chain: indexer de eventos NewFeedback/SessionRecorded → leaderboard web.
```

## Contratos (MVP)

| Contrato | Rol | Estado |
|---|---|---|
| `StarforgeGame.sol` | Matemática pura del juego (pesos, paytables, patrones, supernova, gamble). Port 1:1 de Chain Jam; API pura `spin`/`applyPicks`/`applyGamble` en vez de ICasinoGameV2 | ✅ portado |
| `StarforgeArena.sol` | Ciclo de sesión, escrow del wager (MON testnet), paga premios (cap 1000x), llama al hook de reputación | ✅ scaffold |
| `AgentReputation.sol` | `linkAgent` (verifica ownership ERC-8004), `recordSession` → `giveFeedback` con RTP de la sesión en bps | ✅ scaffold |
| `IRandomness.sol` + `BlockhashRandomness.sol` | Randomness por blockhash futuro (SOLO testnet; documentado) | ✅ scaffold |
| `interfaces/IERC8004.sol` | Subset documentado de Identity + Reputation Registry | ✅ scaffold |

## Flujo de una sesión (agente)

1. `AgentReputation.linkAgent(agentId)` — una vez por wallet.
2. `Arena.openSession(artifacts)` con `msg.value = wager` → pide randomness.
3. Tras ~3 bloques: `fulfillSpin(sessionId)` → `StarforgeGame.spin(seed)`.
   - Sin supernova (menos de 4 estrellas): settle inmediato, payout, feedback.
4. Con supernova: `submitPicks(sessionId, [5 índices], gamble=false)` →
   `applyPicks` → settle, payout, feedback.
5. (Opcional) `gamble=true` → `fulfillGamble` → coin flip → settle.
6. `AgentReputation.recordSession` publica `giveFeedback(agentId,
   rtpBps, 0, keccak("starforge"), keccak("session"), "", "", "")`.

## Reputación y leaderboard

- **Por sesión**: un feedback = RTP de esa sesión en bps (ej. 12500 = la
  sesión pagó 1.25x). Imposible de inflar: solo el Arena puede llamar
  `recordSession`, y el Arena solo liquida sesiones reales.
- **Agregado**: `getSummary(agentId, [arena], tag1, tag2)` o indexer de
  eventos `SessionRecorded` → RTP lifetime, sesiones, mejor sesión.
- **Descubrimiento**: metadata `starforge_player=0x01` + 8004scan.io.

## Decisiones clave

- **Matemática intacta**: el port conserva pesos, paytables, patrones y
  premios 1:1 (RTP declarado 97.60%). La paridad contrato/simulador se
  re-verifica en semana 1 con el simulador Python existente.
- **Sin VRF en testnet**: `BlockhashRandomness` es transparente y suficiente
  para el demo; el README documenta el camino a VRF real.
- **Reputación opt-in**: jugadores sin `linkAgent` juegan normal, sin
  feedback. Cero fricción para humanos.
- **Forfeit**: devuelve el wager (semántica testnet amable; documentada).

## Fuera del MVP (si da tiempo)
- Validator en el Validation Registry con la evidencia de Monte Carlo.
- Estrategias de picks del agente (hoy: random uniforme).
- Frontend leaderboard en vivo.
