# Zig tofu Architecture Analysis

This document provides a deep dive into the internal architecture of the original Zig **tofu** messaging system.

## 1. Core Component Breakdown

### 1.1 Reactor (`Reactor.zig`)
The Reactor is the heartbeat of the engine.
- **Dedicated Reactor Thread:** Runs a single event loop.
- **Poller Integration:** Uses OS-specific primitives (epoll, kqueue, poll) for non-blocking I/O.
- **Message Framing:** Handles the assembly of raw bytes into `BinaryHeader`, `TextHeaders`, and `Body`.
- **Mailbox System:** Uses `MSGMailBox` for inter-thread message delivery.

### 1.2 Pool (`Pool.zig`)
A thread-safe message allocation system.
- **Intrusive Linked List:** Minimizes allocation overhead by reusing message objects.
- **Strategies:** Supports `.poolOnly` (return null if empty) and `.always` (allocate new if empty).
- **Growth:** Manages initial and maximum message limits.

### 1.3 ChannelGroup (`channels.zig`, `MchnGroup.zig`)
The primary interface for applications.
- **`post()`:** Submits a message to the engine for transmission.
- **`waitReceive()`:** Blocks until a message is available on a specific channel group.
- **Channel Assignment:** Manages the lifecycle and routing of channel numbers (1-65534).

### 1.4 Notifier (`Notifier.zig`)
Handles cross-thread signaling, often waking up the reactor or application threads when events occur.

### 1.5 Mailbox (`mailbox.zig`)
A thread-safe, blocking queue implementation used for communication between the Reactor thread and application threads. It supports interrupts and timeouts.

## 2. Thread Model
Tofu employs a multi-threaded architecture:
1.  **Single Reactor Thread:** Handles all socket I/O and protocol state machines.
2.  **Multiple Application Threads:** Call engine APIs (`post`, `waitReceive`, `get`, `put`).
3.  **Synchronization:** Uses mutexes (`sndMtx`, `crtMtx`) and condition variables to manage shared state safely.

## 3. Message Flow

### 3.1 Outbound (App → Network)
1. Application calls `chnls.post(msg)`.
2. Message is enqueued into the Reactor's outbound mailbox.
3. Reactor thread wakes up, dequeues the message.
4. Reactor serializes the message and writes it to the appropriate non-blocking socket.

### 3.2 Inbound (Network → App)
1. Reactor detects data on a socket via the Poller.
2. Reactor parses the `BinaryHeader` to determine message length and routing.
3. Reactor allocates a message from the `Pool`.
4. Reactor reads the `TextHeaders` and `Body` into the allocated message.
5. Reactor routes the message to the correct `ChannelGroup` mailbox.
6. The application thread waiting in `waitReceive()` is woken up and returns the message.
