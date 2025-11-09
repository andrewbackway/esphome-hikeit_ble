# Pedal Controller BLE Protocol Specification

Version: 1.0  
Transport: Bluetooth Low Energy (BLE)

---

## 1. Roles

- **Host**: The mobile / client application.
- **Device**: The pedal controller.

The host connects to the device over BLE, exchanges fixed‑size frames, and performs a one‑time verification and binding procedure using a dedicated command type.

---

## 2. Transport Layer

### 2.1 BLE Service and Characteristics

- **Service UUID**: `0000FFE0-0000-1000-8000-00805F9B34FB`
- **Data Characteristic UUID**: `0000FFE1-0000-1000-8000-00805F9B34FB`

Both write and notification operations use the same characteristic:

- Host writes frames to the characteristic.
- Device sends asynchronous notifications from the characteristic.

### 2.2 Frame Size and Concatenation

All application‑level data is carried in fixed‑size frames:

- Each **frame** is **19 bytes**.
- When represented in hexadecimal, each frame is **38 hex characters**.
- A single BLE notification may contain:
  - 1 frame (38 hex characters), or
  - 2 frames back‑to‑back (76 hex characters).

The host must:

- Split incoming notifications into 38‑character segments.
- Process each segment as an independent frame.

---

## 3. Frame Structure

Each frame has the following layout (byte indices are zero‑based):

| Byte index | Length | Description                             |
|-----------:|--------|-----------------------------------------|
| 0–1        | 2      | Header (`0xAA`, `0x55`)                |
| 2          | 1      | Sequence number                        |
| 3          | 1      | Command type                           |
| 4–13       | 10     | Content (command‑specific payload)     |
| 14–17      | 4      | Device identifier (ID)                 |
| 18         | 1      | Checksum                               |

Total: 19 bytes.

### 3.1 Header

- Fixed value: `0xAA 0x55`
- Used to detect frame boundaries.

### 3.2 Sequence Number

- 8‑bit unsigned integer (0–255).
- Increments by 1 for each frame the host sends.
- Wraps from 255 back to 0.
- During the initial registration phase, the host synchronises its internal sequence counter to the value observed in frames received from the device.

### 3.3 Command Type

- 1‑byte value indicating the logical command type.
- See [Section 4](#4-command-types) for defined types.

### 3.4 Content (Payload)

- 10‑byte command‑specific payload.
- Encodes parameters such as mode, steps, study state, lock password, verify state, etc.
- Exact layouts are defined per command type.

### 3.5 Device Identifier (ID)

- 4‑byte identifier.
- The device includes this ID in its outgoing frames.
- The host copies this ID into host‑originated frames directed at that device.

### 3.6 Checksum (Verify Byte)

- 1‑byte checksum over the “body” of the frame:
  - **Input bytes**: sequence number, command type, content (10 bytes), and ID (4 bytes).  
    (Header and checksum byte are excluded.)
- **Computation**:
  1. Interpret each body byte as an unsigned integer (0–255).
  2. Sum all byte values.
  3. Take the result modulo 256 (keep only the least‑significant 8 bits).
  4. Use this as the checksum byte.

When constructing a frame, the host:

1. Builds the 16‑byte body (`sequence + type + content + id`).
2. Computes the checksum.
3. Emits:

   ```text
   0xAA 0x55 <body[0..15]> <checksum>
   ```

---

## 4. Command Types

### 4.1 Type `0x01` – Study (Pedal Learning)

Purpose: control the pedal “learning” or “study” process.

- **Type**: `0x01`
- **Content**:
  - Byte 0: `0x16`
  - Bytes 1–9: reserved, set to `0x00`
- **Direction**: host → device.

Semantics (at protocol level):

- Triggers or manages a pedal calibration / study procedure on the device.

### 4.2 Type `0x02` – Status and Configuration

Purpose: report or adjust operational configuration and mode.

- **Type**: `0x02`
- **Direction**:
  - device → host: used to report current status/configuration.
  - host → device: used to apply new configuration.

#### 4.2.1 Inbound (device → host) semantics

The device sends frames of type `0x02` to report:

- Current speed mode (economy / normal / cruise / sport / HIKE‑style, etc.).
- Step values (intensity levels) for each mode.
- Flags such as:
  - Automatic / transmission mode.
  - Support for extended features (e.g., special launch/limit modes).
- Deep/intensity parameters.
- Study (learning) state and timing.
- Notice / warning codes (e.g., `C1`, `C2`, `C3`).

These values are encoded in the 10‑byte content as a set of bitfields and nibbles. The exact mapping can vary by firmware, but key points are:

- Certain bytes hold multiple 4‑bit step values packed into high/low nibbles.
- A specific byte contains the mode selection in the lower bits plus flags in the upper bits.
- One byte’s upper nibble encodes study state; its lower nibble encodes a small timer or state code.
- One byte’s individual bits map to notice codes.

The device’s ID field is also populated in these frames; the host learns and then reuses this ID.

#### 4.2.2 Outbound (host → device) semantics

The host sends type `0x02` frames with content derived from the last known configuration, adjusting specific fields to:

- Change the active mode.
- Change the step/intensity for the current mode.
- Toggle automatic behaviour or related flags.

The overall pattern is:

1. The host receives a status frame from the device and interprets its fields.
2. When the user changes a setting, the host modifies the corresponding bits/nibbles in the 10‑byte content.
3. The host sends a new type `0x02` frame with updated content and the same device ID.

### 4.3 Types `0x05` and `0x06` – Safe / Lock Control

Purpose: enable or disable a lock / safe mode using a numeric password.

- **Types**:
  - `0x05` – enable lock/safe mode.
  - `0x06` – disable lock/safe mode.
- **Content** (10 bytes):

  | Byte index | Description                                           |
  |-----------:|-------------------------------------------------------|
  | 0–1        | Password (16‑bit), in little‑endian form              |
  | 2–3        | Password repeated (same 16‑bit value, little‑endian)  |
  | 4–9        | Reserved, all `0x00`                                 |

The password is represented as a 16‑bit value. When encoded:

1. Represent the password as two bytes (`low`, `high`).
2. Place bytes in order: `low`, `high` (little‑endian).
3. Repeat this 2‑byte sequence once more in bytes 2–3.

The device validates the password when processing these commands.

### 4.4 Type `0x08` – Screen / Display Control

Purpose: trigger a display‑related action (such as waking a screen or changing a simple display state).

- **Type**: `0x08`
- **Content**:

  - Byte 0: `0x24`
  - Bytes 1–9: reserved, `0x00`.

- **Direction**: host → device.

Exact display behaviour is implementation‑defined, but the protocol view is a single non‑parameterised command.

### 4.5 Type `0x09` – Verify / Registration Control

Purpose: perform and control verification/registration between host and device.

- **Type**: `0x09`
- **Direction**:
  - host → device: initiate or cancel verification.
  - device → host: report verification result.

#### 4.5.1 Host → Device: Verify Request

**Verify request**:

- Content:

  | Byte index | Value   |
  |-----------:|---------|
  | 0          | `0x03`  |
  | 1–9        | `0x00`  |

- Semantics:
  - Instructs the device to perform a verification / pairing check against the host.
  - Identifies the target device via the ID field in the frame.

**Cancel verify**:

- Content:

  | Byte index | Value   |
  |-----------:|---------|
  | 0          | `0x04`  |
  | 1–9        | `0x00`  |

- Semantics:
  - Instructs the device to cancel any pending verification attempt and return to an unverified state.

#### 4.5.2 Device → Host: Verify Response

The device responds to a verify request with a type `0x09` frame:

- Command type: `0x09`
- Content:

  - Byte 0: result code.
  - Bytes 1–9: reserved / implementation‑specific.

- Result code semantics:

  | Byte 0 value | Meaning                     |
  |-------------:|-----------------------------|
  | `0x00`       | Verification failed         |
  | Non‑zero     | Verification successful     |

Result handling on the host:

- If the host receives a type `0x09` frame while still in the pre‑verified state:
  - If result code is `0x00`, the host treats verification as failed.
  - If result code is non‑zero, the host treats verification as successful and may proceed to binding logic (see Section 5).

The sequence number in the response is also used to resynchronise the host’s internal sequence counter during the verification phase.

### 4.6 Types `0x0A` and `0x0B` – Sound / Beep Control

Purpose: configure or clear device sound behaviour.

- **Types**:
  - `0x0A` – configure sound (pattern, volume, etc.).
  - `0x0B` – reset/clear sound configuration.

- **Typical content layouts**:

  - `0x0A`:
    - Bytes 0–3: sound parameters (pattern, tone, volume, duration).
    - Bytes 4–9: reserved, `0x00`.

  - `0x0B`:
    - All content bytes set to `0x00` (clear/reset).

Exact meaning of each parameter byte is implementation‑specific but follows the same 10‑byte content structure.

---

## 5. Verification and Binding Process

This section describes the full end‑to‑end verification flow between host and device, placing particular emphasis on the verification stages.

### 5.1 States

From the host’s perspective there are two high‑level states:

1. **Pre‑verified (unbound)**:
   - The host has not yet verified this device or bound it to the user.
   - All frames are treated as part of a verification/registration workflow.

2. **Verified (bound)**:
   - The host has completed verification and any required back‑end binding.
   - The device is considered trusted and is associated with a stored identifier (e.g., MAC address).
   - Subsequent connections can skip the verification handshake.

### 5.2 Initial Contact and ID Learning

1. The host connects to a device over BLE and enables notifications on the data characteristic.
2. The device sends one or more type `0x02` status/config frames:
   - The host reads the device ID from these frames.
   - The host may also synchronise its sequence counter to the sequence value in these frames.

At this stage the device is still considered **unverified**.

### 5.3 Host‑Initiated Verification Request

When the user elects to bind/verify the device:

1. The host uses the most recently observed device ID.
2. The host constructs a type `0x09` verify request command:

   - Command type: `0x09`
   - Content: `0x03` followed by nine bytes of `0x00`.
   - ID: 4‑byte device ID.

3. The host sends this frame to the device.

The host typically also starts a verification timeout timer at this point. If no valid verify response is received within the timeout window, the host aborts the process.

### 5.4 Device Verify Response

Upon receiving a verify request, the device replies with a type `0x09` frame:

- Command type: `0x09`
- Content:
  - Byte 0: verification result code.
  - Bytes 1–9: reserved / implementation‑specific.
- ID: same device ID.

The host interprets the response:

- If the result code is `0x00`:
  - Verification has failed.
  - The host may notify the user and terminate the connection.

- If the result code is non‑zero:
  - Verification has succeeded at the BLE protocol level.
  - The host can proceed with higher‑level binding (e.g., associating the device with a user account via a separate network request).

During this phase, the host also synchronises its sequence number with the sequence value received in this frame, ensuring further commands use the correct sequence.

### 5.5 Binding and Transition to Verified State

After a successful verify response:

1. The host completes any required application‑level binding (e.g., send the device ID and MAC address to a back‑end service and wait for confirmation).
2. Upon successful binding, the host:
   - Persists the device’s MAC address and associated metadata locally.
   - Transitions into the **verified** state for this device.

In the verified state:

- All incoming frames are treated as normal operational data (status, configuration, events).
- No special verify/registration handling is applied.

### 5.6 Cancel / Failure Handling

If the user cancels verification or a timeout occurs before a positive verify response:

1. The host may optionally send a type `0x09` cancel command:

   - Command type: `0x09`
   - Content: `0x04` followed by nine bytes of `0x00`.
   - ID: device ID.

2. The host terminates the BLE connection.
3. No device MAC or ID is persisted, and the device remains unverified.

### 5.7 Subsequent Connections (Auto‑Verify)

On future connections:

1. The host scans for BLE devices.
2. When a device is discovered, the host compares its MAC address to stored entries:
   - If the MAC matches a previously bound device:
     - The host immediately treats the device as **verified**.
     - Verification commands (type `0x09`) are not required.
     - Incoming frames are processed as operational status/configuration.
   - If the MAC is unknown:
     - The device is treated as **unverified**.
     - The verification procedure described above must be performed again.

This allows verification to be performed once per device and then reused automatically on subsequent connections.

---

## 6. Example Hex Frame (Verify Request)

Below is an illustrative example of a verify request from host to device. The actual byte values will depend on the current sequence number and device ID.

Assume:

- Sequence number: `0x1A`
- Command type: `0x09`
- Content: `03 00 00 00 00 00 00 00 00 00`
- Device ID: `11 22 33 44`
- Checksum (example): `0x5F`

Frame:

```text
AA 55    // header
1A       // sequence
09       // type = verify control
03 00 00 00 00 00 00 00 00 00  // content: verify request
11 22 33 44                    // device ID
5F       // checksum
```

The device’s verify response frame has the same structure, with type `0x09` and a result code in the first content byte.

---

## 7. Summary

- All communication uses a fixed 19‑byte frame format with a simple 8‑bit checksum.
- A single BLE characteristic is used for both write and notify.
- Command types define behaviour for study, configuration, lock, display, verification, and sound.
- The verification process is centred around type `0x09`:
  - The host initiates with content `0x03`.
  - The device responds with a result code in the first content byte.
  - A non‑zero result code indicates success.
- Once verification and higher‑level binding are complete, the device is associated with a stored MAC address and treated as trusted on future connections, without repeating the verify handshake.
