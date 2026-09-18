# ERC-8004 — notas de investigación (2026-09-18)

Fuente: EIP-8004 "Trustless Agents", implementaciones de referencia
(BillionsNetwork/erc-8004-contracts, sekmet/trustless-agents-erc-8004),
SDKs (optangle/erc8004 Rust, trustless-ai/agent-sdk Go).

## Qué es

Estándar de Ethereum para **identidad y confianza de agentes de IA**:
identificadores duraderos on-chain + señales de reputación portables,
sin gatekeepers. Pagos explícitamente fuera de alcance.

## Los tres registros

### 1. Identity Registry (ERC-721)
- Cada agente = un NFT. `agentId` = `tokenId` (entero; el agentId on-chain
  es el id con padding a 32 bytes, **no** un hash — recomputable).
- `register(string agentURI)` / `register(string agentURI, MetadataEntry[])`
  → mintea y emite `Registered(agentId, agentURI, owner)`.
- `agentURI` (tokenURI) → JSON de registración off-chain:
  `type`, `name`, `description`, `image`, `services[]` (endpoints A2A/MCP),
  `registrations[]` (`{agentRegistry, agentId}`), `supportedTrust[]`
  (ej. `reputation`, `tee-attestation`).
- Identificador canónico del agente:
  `agentRegistry = "{namespace}:{chainId}:{identityRegistry}"`
  ej. `eip155:10143:0x...` en Monad testnet.
- Metadata on-chain opcional: `setMetadata(agentId, key, value)` /
  `getMetadata(agentId, key)`. Clave reservada **`agentWallet`**:
  se fija al registrar (owner), solo se cambia probando control vía
  EIP-712 (`setAgentWallet`), se limpia al transferir.
- Lecturas: `ownerOf`, `tokenURI`, `getAgentWallet`, `getMetadata`.

### 2. Reputation Registry
- `giveFeedback(agentId, value:int128, valueDecimals:uint8 (0-18), tag1, tag2,
  endpoint, fileUri, fileHash)` — solo value/decimals obligatorios.
- `value` es fixed-point con signo: ej. `value=9977, decimals=2` = 97.77.
- Tags libres (bytes32) para filtrado on-chain: nosotros usamos
  `tag1 = keccak256("starforge")`, `tag2 = keccak256("session")`.
- `getSummary(agentId, clientAddresses[], tag1, tag2)` → agregado.
- `readFeedback(agentId, clientAddress, index)`, `revokeFeedback(agentId, index)`.
- **Patrón intencional**: señales crudas on-chain, scoring off-chain
  (indexers, 8004scan.io). No rankea por sí solo.

### 3. Validation Registry
- Hooks para que validadores publiquen verificaciones del trabajo de un
  agente (evidencia por URI + tags). Para nosotros: la certificación de
  matemática (Monte Carlo 10M, paridad contrato/simulador) como evidencia
  de validación del juego — opcional en semana 3.

## Deployments conocidos (2026-09-18, verificado on-chain 2026-09-18)

- Direcciones canónicas (CREATE2, mismas en varias redes):
  - Identity: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (mainnets, incl. Monad mainnet 143)
  - Identity (testnets): `0x8004A818BFB912233c491871b3d84c89A494BD9e`
  - Reputation (testnets): `0x8004B663056A597Dffe9eCcC1965A193B7388713`
- **Monad testnet (10143): DEPLOYMENT OFICIAL CONFIRMADO on-chain.**
  Ambos son proxies ERC1967 con implementaciones distintas:
  - IdentityRegistry: `0x8004A818BFB912233c491871b3d84c89A494BD9e`
    (impl `0x7274E874CA62410a93bd8Bf61c69D8045e399c02`)
  - ReputationRegistry: `0x8004B663056A597Dffe9eCcC1965A193B7388713`
    (impl `0x16e0Fa7f7C56b9a767e34B192b51F921BE31dA34`)
  → NO hace falta desplegar registros propios. Usar estas direcciones.
- Explorador: `https://8004scan.io`.
- RPC funcional desde nuestra VM: `https://rpc.ankr.com/monad_testnet`
  (chainId 10143 verificado; el oficial `testnet-rpc.monad.xyz` no responde).

## Decisiones de diseño para Starforge × ERC-8004

1. **El Arena es el cliente de feedback.** El feedback lo firma el contrato
   del juego, no el agente: imposible falsificar sesiones.
2. **Feedback por sesión** (`tag2="session"`, `value` = RTP de la sesión en
   bps enteros). El leaderboard agrega con `getSummary` / eventos.
3. **Link wallet→agentId** en `AgentReputation.linkAgent`: acepta
   `ownerOf(agentId) == msg.sender` o `getAgentWallet(agentId) == msg.sender`.
   Sin link no hay reputación (el juego funciona igual).
4. **Registro del agente**: `agentURI` puede ser data-URI base64 on-chain
   (recomendado por la spec si se quiere todo on-chain) o JSON hospedado.
   Usamos data-URI para el demo → cero infraestructura.
5. Metadata de descubrimiento: `setMetadata(agentId, "starforge_player", 0x01)`
   para filtrar agentes-jugadores (patrón `swarm_ai_capable`).

## Preguntas abiertas (resueltas semana 2)
- [x] ¿Aparece deployment oficial de ERC-8004 en Monad testnet? **SÍ —
      verificado on-chain** (proxies ERC1967 en las direcciones canónicas;
      ver "Deployments conocidos" arriba). No desplegamos registros propios.
- [x] Confirmar firma exacta de `giveFeedback` contra el ABI oficial
      (erc-8004-contracts, ReputationRegistryUpgradeable.sol). **HALLAZGO:
      los tags son `string`, no `bytes32`.** Nuestra interfaz asumía
      bytes32 (el selector habría sido distinto y la llamada habría
      revertido en testnet). Corregido en `contracts/interfaces/IERC8004.sol`
      + `AgentReputation.sol` (tags `"starforge"`/`"session"` como strings)
      + mocks de tests. También corregidas: `readFeedback` devuelve
      `(int128,uint8,string,string,bool)` con índice `uint64` 1-indexed;
      `getSummary` devuelve `(uint64,int128,uint8)`; `revokeFeedback`
      toma `uint64`. Evento `NewFeedback` con firma oficial exacta.
- [x] Decidir data-URI vs JSON hospedado para `agentURI`: **data-URI**
      (cero infraestructura). `agent/registration.json` es la plantilla.
- [x] Nota de compilación: el call de 8 args con strings dinámicos
      desborda el codegen legacy ("stack too deep"). Solución: compilar
      todo con **via-IR** (`tests/solcx_build.py` + `scripts/deploy.py`);
      además `recordSession` delega el post en `_postFeedback` interno.
      Tests: 34/34 + integración del agente, todo verde.
