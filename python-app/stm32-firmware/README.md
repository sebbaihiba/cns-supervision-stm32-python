# STM32 Firmware

Embedded firmware implementing the CNSP v1 binary communication protocol.

The STM32 generates representative CNS equipment states and transmits them to the Python supervision application through UART.

## Communication

- Protocol: CNSP v1
- Interface: UART
- Baud rate: 115200
- Frame size: 7 bytes

## CNSP Frame

`START | VERSION | ADDRESS | FAULT | STATE | COUNTER | CHECKSUM`

The checksum corresponds to the sum of the first six bytes modulo 256.

> The automatic scenario uses representative logical states for demonstration purposes. Manual buttons are retained only as a development/debug option.
