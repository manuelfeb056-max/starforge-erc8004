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

## Deployments conocidos (2026-09-18)

- Direcciones canónicas (CREATE2, mismas en varias redes):
  - Identity: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (XLayer mainnet)
  - Identity (testnets): `0x8004A818BFB912233c491871b3d84c89A494BD9e`
  - Reputation (testnets): `0x8004B663056A597Dffe9eCcC1965A193B7388713`
  - Repo sekmet: `0x7177...Dd09A` (Identity)
- **Monad: sin deployment listado** ("More chains coming soon").
  → Plan: desplegar la implementación de referencia
  (BillionsNetwork/erc-8004-contracts) en Monad testnet nosotros mismos,
  o usar las direcciones canónicas si aparecen antes del deadline.
- Explorador: `https://8004scan.io`.

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

## Preguntas abiertas (resolver semana 1-2)
- [ ] ¿Aparece deployment oficial de ERC-8004 en Monad testnet? Revisar
      8004scan.io y el repo de BillionsNetwork antes de desplegar el nuestro.
- [ ] Confirmar firma exacta de `giveFeedback` contra el ABI desplegado
      (nuestra interfaz es el subset documentado; verificar orden de params).
- [ ] Decidir data-URI vs JSON hospedado para `agentURI` (default: data-URI).
