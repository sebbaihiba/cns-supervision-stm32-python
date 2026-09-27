# ✈️ Centralized CNS Systems Supervision

Prototype of a centralized supervision system for CNS equipment, developed during an internship at **ONDA – Fès-Saïss Airport**.

The project combines an **STM32 microcontroller**, a custom binary communication protocol and a **Python supervision application**.

> This repository presents an academic prototype based on representative logical equipment states.  
> It does not contain operational airport data.

---

## 🏗️ System Architecture

The prototype is based on communication between an STM32 embedded system and a Python supervision application.

The STM32 generates representative CNS equipment states and transmits them through UART using the **CNSP v1 binary protocol**.

The Python application receives and decodes the frames, updates the supervision interface and stores events in a local SQLite database.

![Architecture du système de supervision CNS](architecture-cns.png)

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

## 🎯 Project Objective

The objective was to develop a prototype capable of:

- supervising several CNS-related systems from a centralized interface;
- transmitting equipment states and faults from an STM32 to a computer;
- structuring communication using binary frames;
- decoding and validating received frames;
- displaying system states in real time;
- identifying warnings, alarms and equipment faults;
- recording events in a local database.

---

## 📡 Supervised Systems

The prototype includes representative states for:

| System | Category |
|---|---|
| DME | Navigation |
| ILS Localizer | Navigation |
| Glide Slope | Navigation |
| VHF | Communication |
| ADS-B | Surveillance |
| UPS | Power support |

The possible system states are:

- 🟢 **NORMAL**
- 🟠 **WARNING**
- 🔴 **ALARM**
- ⚫ **OUT OF SERVICE**

For standard CNS faults, the embedded logic can first report a **WARNING** state and switch to **ALARM** if the fault persists for 5 seconds.

A power loss can lead directly to an **OUT OF SERVICE** state.

---

## 🔐 CNSP v1 Communication Protocol

A custom binary protocol called **CNSP v1** was implemented to structure communication between the STM32 and the PC application.

Each frame contains **7 bytes**:

```text
START | VERSION | ADDRESS | FAULT | STATE | COUNTER | CHECKSUM
