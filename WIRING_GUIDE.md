# Wiring Guide: Raspberry Pi + Arduino + LED Matrix

> [!WARNING]
> **Voltage Mismatch Risk**: Raspberry Pi GPIOs are **3.3V**. Most Arduinos (Uno, Nano) are **5V**.
> Connecting Arduino `Tx` (5V) directly to Raspberry Pi `Rx` (3.3V) **CAN DAMAGE YOUR PI**.
> - **Safe:** Pi `Tx` -> Arduino `Rx` (Pi sends 3.3V, Arduino sees it as High. Safe.)
> - **Risky:** Arduino `Tx` -> Pi `Rx` (Arduino sends 5V, Pi hates 5V.) -> **Use a Voltage Divider or Level Shifter.**

## 1. Raspberry Pi ↔ Arduino (Communication)
This connection allows the Pi to send commands ('s', 'p') to the Arduino.

| Connection Type | Raspberry Pi Pin (Physical) | Arduino Pin | Note |
| :--- | :--- | :--- | :--- |
| **Data (Pi to Arduino)** | **GPIO 14 (Tx)** - Pin 8 | **Rx** - Pin 0 | sends commands |
| **Data (Arduino to Pi)** | **GPIO 15 (Rx)** - Pin 10 | **Tx** - Pin 1 | *Optional* - Only needed if Pi reads data back |
| **Ground (Common)** | **GND** - Pin 6 | **GND** | **CRITICAL:** Must be connected! |

*Note: You must unplug the Arduino `Rx` pin (Pin 0) when uploading code from your computer, or the upload will fail.*

## 2. Arduino ↔ LED Matrix (Control)
This drives the LEDs.

| Connection Type | Arduino Pin | LED Matrix Wire | Note |
| :--- | :--- | :--- | :--- |
| **Data Signal** | **Digital Pin 3** | **DIN** (Data In) | Check arrow on back of matrix! |
| **Power (+)** | **5V Pin** | **+5V** / VCC | See Power note below. |
| **Ground (-)** | **GND** | **GND** | Shared with Pi GND too. |

> [!CAUTION]
> **Powering 64 LEDs**
> A 8x8 Matrix (64 LEDs) at full white can draw **~3.8 Amps**, which will fry an Arduino regulator.
> - **Safe Mode:** We set brightness to `32` (approx 10%). This draws ~400mA, which is safe for USB/Arduino 5V pin.
> - **Full Power:** If you want full brightness, you MUST use an external 5V Power Supply connected directly to the LED Matrix power wires.

## 3. Full Diagram

```
[ Raspberry Pi ]             [ Arduino Uno ]             [ LED Matrix ]
  Pin 8 (Tx) -------------------> Pin 0 (Rx)
  Pin 6 (GND) ------------------> GND
                                  Pin 3 --------------------> DIN (Data In)
                                  5V -----------------------> +5V
                                  GND ----------------------> GND
```

## Checklist before Powering On
1.  [ ] **GND** between Pi and Arduino is connected.
2.  [ ] **GND** between Arduino and LED Matrix is connected.
3.  [ ] **Pi Tx** goes to **Arduino Rx**.
4.  [ ] **Arduino Pin 3** goes to **Matrix DIN**.
5.  [ ] **Arduino Rx (Pin 0)** is DISCONNECTED while uploading code.
