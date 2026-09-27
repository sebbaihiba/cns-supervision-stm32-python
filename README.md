## 🏗️ System Architecture

The prototype is based on communication between an STM32 embedded system and a Python supervision application.

The STM32 generates representative CNS equipment states and transmits them through UART using the **CNSP v1 binary protocol**.

The Python application receives and decodes the frames, updates the supervision interface and stores events in a local SQLite database.

![CNS Supervision System Architecture](architecture-cns.png)

---

## 🖥️ Supervision Dashboard

The Python application provides:

- real-time visualization of CNS equipment states;
- UART communication monitoring;
- CNSP frame decoding;
- protocol integrity verification;
- alarm and warning visualization;
- event history;
- local SQLite data storage.

> The screenshot below was taken without the STM32 board connected, which explains the communication loss indicator displayed by the application.

![CNS Supervision Dashboard](supervision-dashboard.png)

---
