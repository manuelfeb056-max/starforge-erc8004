# Starforge × ERC-8004

**Monad Metropolis Hackathon** · Track: Trust, Identity & AI Infrastructure ($30K) · Deadline: 13 oct 2026

Agentes de IA con identidad on-chain **ERC-8004** que juegan **STARFORGE**
— arcade slot con RNG verificable y RTP publicado del 97.60% — de forma
autónoma. Cada partida liquidada se publica como **feedback de reputación
on-chain firmado por el propio contrato del juego**: un track record de
agente imposible de falsificar, con leaderboard por RTP real.

## Estado

Semana 2 en curso (2026-09-18). Registros ERC-8004 oficiales **verificados
on-chain en Monad testnet** (ver `docs/ERC8004_NOTES.md`); ABI oficial
reconciliada (tags = strings); tests 34/34 + integración del agente verdes;
`scripts/deploy.py` e `indexer/index.py` listos. **Bloqueado por faucet:**
la wallet throwaway necesita MON de testnet (ver `docs/MILESTONES.md`).
$0 gastados, sin wallets reales, sin mainnet.

## Direcciones — Monad testnet (chainId 10143)

Desplegado 2026-09-18. Agente ERC-8004 **id 1880** (`0xFC4d1DF0a3199A21dBE3ee9FD2D367A198744b03`):
sesiones jugadas por el bot demo en testnet, cada liquidación publicada como
feedback en el ReputationRegistry oficial (tag `starforge/session`). Demo: `frontend/index.html`.

> **Rotación 2026-09-18:** el agente anterior (id 1879, `0xeA682f1970bb3377498a4910BC237CE849Da64Fd`)
> quedó comprometido porque su clave privada se publicó por accidente en el commit
> `b287e98`. El historial Git se purgó (filter-repo + force-push) y se registró un
> agente nuevo. La wallet vieja se considera quemada: no usarla más.

| Contrato | Dirección |
|---|---|
| ERC-8004 IdentityRegistry (oficial) | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| ERC-8004 ReputationRegistry (oficial) | `0x8004B663056A597Dffe9eCcC1965A193B7388713` |
| StarforgeGame | `0x0f553b6388Ca7833fcc7e30c1cA200b79B99adA8` |
| BlockhashRandomness | `0xD0574682B0c8D46c5423dd59cb1e55579CAba3c8` |
| AgentReputation | `0x210D64fb460322fe90c1E7025b1700864a811577` |
| StarforgeArena | `0xcA53e0a7B6D85b4e84dCB1993a2780349BB4149d` |

RPC: `https://rpc.ankr.com/monad_testnet` (el oficial `testnet-rpc.monad.xyz`
no respondía el 2026-09-18).

## Estructura

```
contracts/
  StarforgeGame.sol        # matemática pura del juego (port 1:1 de Chain Jam)
  StarforgeArena.sol       # sesiones, escrow, payouts, hook de reputación
  AgentReputation.sol      # link wallet→agentId + feedback ERC-8004
  interfaces/IERC8004.sol  # subset Identity + Reputation Registry
  randomness/              # IRandomness + BlockhashRandomness (solo testnet)
agent/
  registration.json        # plantilla del archivo de registración ERC-8004
  play-agent.py            # bot demo (esqueleto; wiring web3.py en semana 2)
docs/
  ARCHITECTURE.md          # diseño completo + diagrama + flujos
  ERC8004_NOTES.md         # investigación ERC-8004 + preguntas abiertas
  MILESTONES.md            # plan semanal hasta el 13 oct
scripts/
  deploy-testnet.md        # pasos de deploy (manual, sin claves en repo)
```

## Quickstart (cuando llegue semana 2)

```bash
# 1. compilar
npx solc --bin --abi contracts/StarforgeGame.sol -o build/
# 2. desplegar en Monad testnet (ver scripts/deploy-testnet.md)
# 3. registrar agente + linkAgent + correr el bot
export AGENT_PRIVATE_KEY=<throwaway-testnet-key>
python3 agent/play-agent.py
```

## Origen

Port de [STARFORGE — La Forja Estelar](../chain-jam/starforge/) (Chain Jam
Vol. 1): misma matemática (`math-spec.json`), verificado con Monte Carlo
10M (RTP 97.60% con todos los artefactos) y paridad contrato/simulador
15/15. Solo cambió la interfaz de host: de ICasinoGameV2 a `StarforgeArena`
nativo de Monad.
