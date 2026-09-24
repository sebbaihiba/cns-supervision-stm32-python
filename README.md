# ✈️ Centralized CNS Systems Supervision

Prototype of a centralized supervision system for CNS equipment, developed during an internship at **ONDA – Fès-Saïs Airport**.

The project combines an **STM32 microcontroller**, a custom binary communication protocol and a **Python supervision application**.

> This repository presents an academic prototype based on representative logical equipment states. It does not contain operational airport data.

---
## 🖥️ Supervision Dashboard

The Python application provides real-time visualization of CNS equipment states, UART communication status, CNSP protocol integrity and event history.

> The screenshot below was taken without the STM32 board connected, which explains the communication loss indicator displayed by the application.

![CNS Supervision Dashboard](tableau%20de%20bord%20de%20supervision.png)

## 🎯 Project Objective

The objective of this project was to design a prototype capable of:

- monitoring several CNS-related systems from a centralized interface;
- transmitting equipment states and faults from an STM32 to a computer;
- decoding structured binary frames;
- displaying equipment status in real time;
- recording events and faults in a database.

---

## 🏗️ System Architecture

The general communication chain is:

STM32 → UART → PC → Python application → SQLite database

The STM32 generates and transmits structured status frames.

The Python application receives the frames through the serial connection, verifies and decodes them, then updates the supervision interface and stores the information in the database.

---

## 📡 Monitored Systems

The prototype includes representative states for systems such as:

- DME
- ILS Localizer
- Glide Slope
- VHF
- ADS-B
- UPS / Power Supply

Possible operating states include:

- 🟢 NORMAL
- 🟠 WARNING
- 🔴 ALARM
- ⚫ OUT OF SERVICE

---

## 🔐 CNSP Communication Protocol

A custom binary protocol named **CNSP v1** was implemented to structure communication between the STM32 and the supervision application.

The frame contains information such as:

- Start byte
- Protocol version
- System identifier
- Fault identifier
- Equipment state
- Counter
- Integrity verification field

This structure makes it possible to identify the equipment concerned, its current state and the associated fault while detecting transmission errors.

---

## 💻 Technologies

### Embedded system

- STM32
- C
- UART
- STM32CubeIDE

### PC Application

- Python
- Tkinter
- PySerial
- SQLite

### Communication

- Serial communication
- Custom binary protocol
- Frame integrity verification

---

## 🖥️ Supervision Application

The Python application provides:

- real-time equipment visualization;
- state indication;
- fault identification;
- received/transmitted frame monitoring;
- event history;
- SQLite data storage.

---

## 📁 Repository Structure

```text
cns-supervision-stm32-python/
│
├── stm32-firmware/
│
│   └── STM32 embedded code
│
├── python-app/
│
│   ├── interface.py
│   ├── cnsp_parser.py
│   ├── database.py
│   └── show_history.py
│
├── docs/
│
│   └── project documentation
│
├── images/
│
│   └── supervision interface and architecture
│
└── README.md
