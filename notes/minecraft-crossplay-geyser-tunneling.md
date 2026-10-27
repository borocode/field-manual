# Cross-Play Minecraft Architecture: Geyser, Bedrock UDP & Reverse Tunneling

## Problem
Self-hosting a unified Minecraft server that bridges Java Edition players (PC / Mac) and Bedrock Edition players (Nintendo Switch, mobile, consoles) from residential internet connections presents several technical challenges:
1. **Transport Protocol Asymmetry:** Java Edition uses persistent TCP streaming (`25565/tcp`), while Bedrock Edition relies on RakNet and NetherNet UDP packet streams (`19132/udp` and `19133/udp`).
2. **Residential Ingress Barriers:** Carrier-Grade NAT (CGNAT) and residential ISP port blocking prevent direct inbound connections without exposing the home public IP.
3. **Console Client Constraints:** Consoles (especially Nintendo Switch) restrict users from entering arbitrary server IP addresses or non-standard ports unless using DNS redirection proxies or local subnet LAN broadcasting.

## Environment
* **Platform:** Docker container (`itzg/minecraft-server:latest`, Java 25 runtime).
* **Server Software:** PaperMC (high-performance Spigot fork).
* **Bridge Plugins:** Geyser-Spigot (Bedrock translation proxy), Floodgate (hybrid authentication), ViaVersion / ViaBackwards (multi-version compatibility).
* **Networking:** Reverse TCP tunnel (`bore`), Cloudflare DNS SRV records.

## What Was Observed

### 1. UDP Packet Fragmentation Over Virtual Tunnels
Standard HTTP/TCP tunneling tools (such as basic Cloudflare Tunnels) only proxy TCP traffic, completely failing to forward Bedrock's RakNet UDP handshake packets.

### 2. Bedrock Switch Discovery Constraints
The Nintendo Switch Bedrock client will not display external servers unless they appear under the native **Friends / LAN Games** discovery tab or through a DNS trick. For home network co-op, Bedrock broadcast packets (`19132/udp`) must be explicitly forwarded through the host's physical network adapter.

## What Helped

### 1. Containerized PaperMC & JVM Memory Management
The server is containerized with explicit memory constraints and Aikar's Garbage Collection optimization flags to eliminate tick spikes during Bedrock chunk translation:

```yaml
# docker-compose.yml
services:
  minecraft:
    image: itzg/minecraft-server:latest
    container_name: minecraft-server
    restart: unless-stopped
    ports:
      - "25565:25565/tcp"   # Java Edition
      - "19132:19132/udp"   # Bedrock RakNet
      - "19133:19133/udp"   # Bedrock NetherNet
    environment:
      TYPE: "PAPER"
      VERSION: "latest"
      MEMORY: "3G"
      JVM_OPTS: "-XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch"
      ONLINE_MODE: "true"   # Enforce Mojang authentication for public ingress
    volumes:
      - ./data:/data
```

### 2. Dual-Transport Geyser Configuration
In `plugins/Geyser-Spigot/config.yml`, configure Geyser to support both legacy RakNet and modern WebRTC/NetherNet transports, binding directly to all available network interfaces:

```yaml
bedrock:
  address: 0.0.0.0
  port: 19132
  transport: both
  webrtc-port: 19133
  clone-remote-port: false
  auth-type: floodgate    # Secure hybrid Bedrock-Java authentication via Floodgate
```

> **Security Note:** If running an offline testing server (`online-mode: false` / `auth-type: offline`), strictly isolate the ports to a private LAN. Exposing offline authentication to the public internet allows arbitrary players to connect under an operator's username.

### 3. Public Java Ingress via Reverse TCP Tunnel & DNS SRV
To allow public Java players to connect from the internet without port forwarding or exposing residential WAN IPs:
1. Establish a lightweight reverse TCP tunnel using `bore`:
   ```bash
   bore local 25565 --to bore.pub
   # Yields public endpoint: bore.pub:<assigned-port>
   ```
2. Create an RFC 2782 DNS **SRV record** at your domain registrar/DNS provider to hide the non-standard port from human players:

| Service | Protocol | Name | Priority | Weight | Port | Target |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `_minecraft` | `_tcp` | `play` | `0` | `5` | `<assigned-port>` | `bore.pub` |

Java Edition players simply type `play.example.com` into their client. The Minecraft client automatically queries DNS for `_minecraft._tcp.play.example.com`, resolves the assigned tunnel port, and establishes the TCP handshake seamlessly.

### 4. Automated Visitor Sandboxing (Adventure Gatekeeper)
To permit open public visits while protecting the world from griefing without heavy permission plugins:
* Default world game mode is set to `adventure` (`server.properties: gamemode=adventure`).
* Players spawn in an isolated obstacle vault.
* Stepping on a verified checkpoint pressure plate triggers command logic to grant `survival` mode and teleport the player to the open surface world.

## Limits
* **Bedrock Public Tunneling:** While Java TCP traffic routes cleanly through DNS SRV records and reverse tunnels, Bedrock UDP tunneling requires high-performance UDP reverse proxies (such as `frp` or dedicated VPS WireGuard relays) to avoid MTU packet drop issues.
* **Redstone & Entity Desync:** Geyser translates packets on the fly; complex redstone machinery operating at 20 ticks/sec or custom Java particle effects can occasionally render with visual jitter on Bedrock clients.

## Related Field Notes
* [Headless 24/7 Unattended Disk Unlock (LUKS2 + TPM 2.0)](headless-unattended-disk-unlock-tpm2.md) — Unattended host reboot and automated container recovery.
* [Lightning Network Peer Discovery & Gossip Storm Prevention](lightning-network-peer-gossip-management.md) — Rate-limiting P2P handshakes and socket churn.

## Sources & Credit
* [GeyserMC Documentation](https://geysermc.org/) and the [Floodgate project](https://github.com/GeyserMC/Floodgate).
* [PaperMC High-Performance Minecraft Server](https://papermc.io/).
* [bore CLI reverse tunneling tool](https://github.com/ekzhang/bore).
* [RFC 2782 DNS SRV Specification](https://datatracker.ietf.org/doc/html/rfc2782).
