#include "hikeit_ble.h"

#include "./button/hikeit_button.h"
#include "./number/hikeit_step_number.h"
#include "./select/hikeit_speed_select.h"
#include "./switch/hikeit_locked_switch.h"
#include "./text_sensor/hikeit_status_sensor.h"

#include "esphome/components/select/select.h"
#include "esphome/components/switch/switch.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"

namespace esphome {
namespace hikeit_ble {

// Helper to convert hex to string for logging
std::string format_hex(const uint8_t* data, size_t len) {
  std::string result;
  result.reserve(len * 2);
  for (size_t i = 0; i < len; i++) {
    char buf[3];
    sprintf(buf, "%02X", data[i]);
    result += buf;
  }
  return result;
}

// Helper to convert speed model to string
const char* speed_model_to_string(SpeedModel model) {
  switch (model) {
    case SPEED_ECONOMY:
      return "Eco 4x4";
    case SPEED_NORMAL:
      return "Off";
    case SPEED_CRUISE:
      return "Cruise";
    case SPEED_SPORT:
      return "Sport";
    case SPEED_HIKE_IT:
      return "Hike IT";
    case SPEED_AUTO:
      return "Auto";
    case SPEED_LAUNCH:
      return "Launch";
    case SPEED_ANTI_SLIP:
      return "Anti-Slip";
    case SPEED_VALET:
      return "Valet";
    case SPEED_SL:
      return "SL";
    default:
      return "Unknown";
  }
}

// Helper to convert string to speed model
SpeedModel string_to_speed_model(const std::string& str) {
  if (str == "Eco 4x4") return SPEED_ECONOMY;
  if (str == "Off") return SPEED_NORMAL;
  if (str == "Cruise") return SPEED_CRUISE;
  if (str == "Sport") return SPEED_SPORT;
  if (str == "Hike IT") return SPEED_HIKE_IT;
  if (str == "Auto") return SPEED_AUTO;
  if (str == "Launch") return SPEED_LAUNCH;
  if (str == "Anti-Slip") return SPEED_ANTI_SLIP;
  if (str == "Valet") return SPEED_VALET;
  if (str == "SL") return SPEED_SL;
  return SPEED_NORMAL;
}

void HikeITBLEComponent::setup() {
  ESP_LOGCONFIG(TAG, "Setting up HIKE IT BLE...");
  this->set_state(STATE_DISCONNECTED);
}

void HikeITBLEComponent::loop() {
  // If switch is OFF, ensure we are disconnected and do nothing
  if (!this->connection_allowed_()) {
    if (this->state_ != STATE_DISCONNECTED) {
      ESP_LOGI(TAG, "Connect switch is OFF - disconnecting from HIKE IT device");

      // If we are in any active connection state, send a clean disconnect
      if (this->state_ == STATE_CONNECTED ||
          this->state_ == STATE_VERIFIED ||
          this->state_ == STATE_VERIFYING ||
          this->state_ == STATE_CONNECTING) {
        this->send_disconnect_command();  // calls parent_->disconnect() after timeout
      } else if (this->parent_ != nullptr) {
        this->parent_->disconnect();
      }

      // Local state cleanup
      this->handle_disconnection();
    }

    // Do not attempt new connections
    return;
  }

  // Normal reconnection logic when switch is ON
  if (this->state_ == STATE_DISCONNECTED || this->state_ == STATE_ERROR) {
    uint32_t now = millis();
    if (now - this->last_connection_attempt_ > this->reconnect_delay_) {
      this->last_connection_attempt_ = now;
      this->attempt_connection();
    }
  }
}


void HikeITBLEComponent::dump_config() {
  ESP_LOGCONFIG(TAG, "HIKE IT BLE:");
  ESP_LOGCONFIG(
      TAG, "  MAC Address: %02X:%02X:%02X:%02X:%02X:%02X",
      (uint8_t)(this->address_ >> 40), (uint8_t)(this->address_ >> 32),
      (uint8_t)(this->address_ >> 24), (uint8_t)(this->address_ >> 16),
      (uint8_t)(this->address_ >> 8), (uint8_t)(this->address_));
  ESP_LOGCONFIG(TAG, "  PIN: %s", this->pin_.c_str());
  ESP_LOGCONFIG(TAG, "  State: %d", this->state_);
}

void HikeITBLEComponent::set_address(uint64_t address) {
  this->address_ = address;
}

void HikeITBLEComponent::set_address(const uint8_t* address) {
  this->address_ = 0;
  for (uint8_t i = 0; i < 6; i++) {
    this->address_ |= ((uint64_t)address[i]) << (40 - i * 8);
  }
}

void HikeITBLEComponent::attempt_connection() {
  if (!this->connection_allowed_()) {
    ESP_LOGD(TAG, "Connect switch is OFF - skipping connection attempt");
    return;
  }

  if (this->state_ != STATE_DISCONNECTED && this->state_ != STATE_ERROR) {
    return;
  }

  ESP_LOGI(TAG, "Attempting connection to device...");
  this->set_state(STATE_CONNECTING);

  // BLEClient connection is initiated elsewhere (e.g. by esp32_ble_tracker),
  // this just updates our internal state and timing.
}


void HikeITBLEComponent::gattc_event_handler(esp_gattc_cb_event_t event,
                                             esp_gatt_if_t gattc_if,
                                             esp_ble_gattc_cb_param_t* param) {
  switch (event) {
    case ESP_GATTC_OPEN_EVT: {
      if (param->open.status == ESP_GATT_OK) {
        ESP_LOGI(TAG, "Connected to device");
        this->handle_connection();
      } else {
        ESP_LOGW(TAG, "Connection failed, status=%d", param->open.status);
        this->set_state(STATE_ERROR);
      }
      break;
    }

    case ESP_GATTC_DISCONNECT_EVT: {
      ESP_LOGW(TAG, "Disconnected from device");
      this->handle_disconnection();
      break;
    }

    case ESP_GATTC_SEARCH_CMPL_EVT: {
      // Service discovery complete, find our service
      auto* chr = this->parent_->get_characteristic(
          esp32_ble_tracker::ESPBTUUID::from_raw(SERVICE_UUID),
          esp32_ble_tracker::ESPBTUUID::from_raw(NOTIFY_UUID));

      if (chr == nullptr) {
        ESP_LOGW(TAG, "Service/Characteristic not found");
        this->set_state(STATE_ERROR);
        this->parent_->disconnect();
        return;
      }

      this->char_handle_ = chr->handle;
      this->notify_handle_ = chr->handle;

      ESP_LOGI(TAG, "Service and characteristic found");
      this->start_notify();
      break;
    }

    case ESP_GATTC_REG_FOR_NOTIFY_EVT: {
      if (param->reg_for_notify.status == ESP_GATT_OK) {
        ESP_LOGI(TAG, "Notifications enabled");
        this->set_state(STATE_CONNECTED);

        // Wait 500ms then send verification command
        this->set_timeout(500, [this]() { this->send_verify_command(); });
      }
      break;
    }

    case ESP_GATTC_NOTIFY_EVT: {
      if (param->notify.handle == this->notify_handle_) {
        this->handle_notification(param->notify.value, param->notify.value_len);
      }
      break;
    }

    default:
      break;
  }
}

void HikeITBLEComponent::handle_connection() {
  this->set_state(STATE_CONNECTED);
  this->connected_callbacks_.call();
  this->update_status_text();
}

void HikeITBLEComponent::handle_disconnection() {
  this->set_state(STATE_DISCONNECTED);
  this->disconnected_callbacks_.call();
  this->update_status_text();

  // Reset state
  this->device_id_ = 0;
  this->sequence_counter_ = 0;
  this->message_buffer_.clear();
}

void HikeITBLEComponent::set_state(ConnectionState state) {
  if (this->state_ != state) {
    this->state_ = state;
    ESP_LOGD(TAG, "State changed to: %d", state);
    this->update_status_text();
  }
}

void HikeITBLEComponent::update_status_text() {
  if (this->status_sensor_ == nullptr) return;

  std::string status;
  if (!this->connection_allowed_()) {
    status = "Offline";
  } else {
    switch (this->state_) {
      case STATE_DISCONNECTED:
        status = "Disconnected";
        break;
      case STATE_CONNECTING:
        status = "Connecting...";
        break;
      case STATE_CONNECTED:
        status = "Connected";
        break;
      case STATE_VERIFYING:
        status = "Verifying...";
        break;
      case STATE_VERIFIED:
        status = "Verified";
        break;
      case STATE_ERROR:
        status = "Error";
        break;
    }
  }

  this->status_sensor_->publish_state(status);
}

void HikeITBLEComponent::start_notify() {
  ESP_LOGI(TAG, "Enabling notifications...");

  auto status = esp_ble_gattc_register_for_notify(
      this->parent_->get_gattc_if(), this->parent_->get_remote_bda(),
      this->notify_handle_);

  if (status != ESP_OK) {
    ESP_LOGW(TAG, "Failed to register for notifications: %d", status);
    this->set_state(STATE_ERROR);
  }
}

uint8_t HikeITBLEComponent::get_sequence() {
  uint8_t seq = this->sequence_counter_;
  this->sequence_counter_ = (this->sequence_counter_ + 1) % 256;
  return seq;
}

uint8_t HikeITBLEComponent::calculate_checksum(const uint8_t* data,
                                               size_t len) {
  uint32_t sum = 0;
  for (size_t i = 0; i < len; i++) {
    sum += data[i];
  }
  return sum & 0xFF;
}

std::vector<uint8_t> HikeITBLEComponent::build_message(uint8_t type,
                                                       const uint8_t* content) {
  std::vector<uint8_t> message;
  message.reserve(MESSAGE_LENGTH);

  // Header
  message.push_back(HEADER_BYTE_1);
  message.push_back(HEADER_BYTE_2);

  // Sequence
  message.push_back(this->get_sequence());

  // Type
  message.push_back(type);

  // Content (10 bytes)
  for (int i = 0; i < 10; i++) {
    message.push_back(content[i]);
  }

  // Device ID (4 bytes)
  message.push_back((this->device_id_ >> 24) & 0xFF);
  message.push_back((this->device_id_ >> 16) & 0xFF);
  message.push_back((this->device_id_ >> 8) & 0xFF);
  message.push_back(this->device_id_ & 0xFF);

  // Checksum (skip header)
  uint8_t checksum = this->calculate_checksum(&message[2], message.size() - 2);
  message.push_back(checksum);

  return message;
}

void HikeITBLEComponent::send_command(const std::vector<uint8_t>& data) {
  if (!this->is_connected()) {
    ESP_LOGW(TAG, "Not connected, cannot send command");
    return;
  }

  ESP_LOGD(TAG, "Sending: %s", format_hex(data.data(), data.size()).c_str());

  auto status = esp_ble_gattc_write_char(
      this->parent_->get_gattc_if(), this->parent_->get_conn_id(),
      this->char_handle_, data.size(), const_cast<uint8_t*>(data.data()),
      ESP_GATT_WRITE_TYPE_NO_RSP, ESP_GATT_AUTH_REQ_NONE);

  if (status != ESP_OK) {
    ESP_LOGW(TAG, "Failed to send command: %d", status);
  }
}

void HikeITBLEComponent::send_verify_command() {
  ESP_LOGI(TAG, "Sending verification command");
  this->set_state(STATE_VERIFYING);

  uint8_t content[10] = {0x03, 0x00, 0x00, 0x00, 0x00,
                         0x00, 0x00, 0x00, 0x00, 0x00};
  auto cmd = this->build_message(0x09, content);
  this->send_command(cmd);
}

void HikeITBLEComponent::send_disconnect_command() {
  ESP_LOGI(TAG, "Sending disconnect command");

  uint8_t content[10] = {0x04, 0x00, 0x00, 0x00, 0x00,
                         0x00, 0x00, 0x00, 0x00, 0x00};
  auto cmd = this->build_message(0x09, content);
  this->send_command(cmd);

  // Disconnect after sending
  this->set_timeout(500, [this]() { this->parent_->disconnect(); });
}

void HikeITBLEComponent::send_screen_command() {
  ESP_LOGI(TAG, "Sending screen command");

  uint8_t content[10] = {0x24, 0x00, 0x00, 0x00, 0x00,
                         0x00, 0x00, 0x00, 0x00, 0x00};
  auto cmd = this->build_message(0x08, content);
  this->send_command(cmd);
}

void HikeITBLEComponent::send_speed_model_command(SpeedModel model,
                                                  uint8_t at_flag) {
  if (!this->has_cached_state_) {
    ESP_LOGW(TAG, "No cached state, cannot send speed model command");
    return;
  }

  ESP_LOGI(TAG, "Sending speed model command: %s (AT=%d)",
           speed_model_to_string(model), at_flag);

  // Copy current content
  uint8_t content[10];
  memcpy(content, this->last_message_.content, 10);

  // Modify based on model
  if (model <= SPEED_AUTO) {
    content[0] = model;
    content[3] = 0;
  } else if (model == SPEED_LAUNCH) {
    content[3] = 1;
  } else if (model == SPEED_ANTI_SLIP) {
    content[3] = 2;
  } else {
    content[3] = 4;
  }

  // Set AT flag
  content[3] = content[3] | (at_flag << 7);

  // Clear bytes 4-6
  content[4] = 0;
  content[5] = 0;
  content[6] = 0;

  auto cmd = this->build_message(0x02, content);
  this->send_command(cmd);
}

void HikeITBLEComponent::send_step_command(uint8_t step, SpeedModel model) {
  if (!this->has_cached_state_) {
    ESP_LOGW(TAG, "No cached state, cannot send step command");
    return;
  }

  ESP_LOGI(TAG, "Sending step command: %d for %s", step,
           speed_model_to_string(model));

  // Copy current content
  uint8_t content[10];
  memcpy(content, this->last_message_.content, 10);

  // Modify based on model
  if (model == SPEED_ECONOMY) {
    content[1] = (content[1] & 0xF0) | (step & 0x0F);
  } else if (model == SPEED_CRUISE) {
    content[1] = (content[1] & 0x0F) | ((step << 4) & 0xF0);
  } else if (model == SPEED_SPORT) {
    content[2] = (content[2] & 0xF0) | (step & 0x0F);
  } else if (model == SPEED_HIKE_IT) {
    content[2] = (content[2] & 0x0F) | ((step << 4) & 0xF0);
  }

  auto cmd = this->build_message(0x02, content);
  this->send_command(cmd);
}

void HikeITBLEComponent::send_auto_command(bool enable) {
  if (!this->has_cached_state_) {
    ESP_LOGW(TAG, "No cached state, cannot send auto command");
    return;
  }

  ESP_LOGI(TAG, "Sending auto command: %s", enable ? "ON" : "OFF");

  // Copy current content
  uint8_t content[10];
  memcpy(content, this->last_message_.content, 10);

  // Set/clear AT flag in byte 3, bit 7
  content[3] = (content[3] & 0x3F) | ((enable ? 1 : 0) << 7);

  // Clear bytes 4-6
  content[4] = 0;
  content[5] = 0;
  content[6] = 0;

  auto cmd = this->build_message(0x02, content);
  this->send_command(cmd);
}

void HikeITBLEComponent::send_safe_mode_command(const std::string& password,
                                                bool enable) {
  ESP_LOGI(TAG, "Sending safe mode command: %s with PIN: %s",
           enable ? "LOCK" : "UNLOCK", password.c_str());

  // Validate and pad password to 4 digits
  std::string pwd = "0000" + password;
  pwd = pwd.substr(pwd.length() - 4);

  // Convert to hex
  uint16_t pwd_value = std::stoi(pwd);

  // Byte swap (little-endian)
  uint8_t pwd_low = pwd_value & 0xFF;
  uint8_t pwd_high = (pwd_value >> 8) & 0xFF;

  // Build content: swapped password twice + zeros
  uint8_t content[10] = {pwd_low, pwd_high, pwd_low, pwd_high, 0x00,
                         0x00,    0x00,     0x00,    0x00,     0x00};

  uint8_t type = enable ? 0x05 : 0x06;
  auto cmd = this->build_message(type, content);
  this->send_command(cmd);
}

void HikeITBLEComponent::handle_notification(const uint8_t* data,
                                             uint16_t length) {
  ESP_LOGD(TAG, "Received notification: %s", format_hex(data, length).c_str());

  // Handle single (19 bytes) or double (38 bytes) messages
  if (length == MESSAGE_LENGTH) {
    this->process_message(data);
  } else if (length == MESSAGE_LENGTH * 2) {
    // Split into two messages
    this->process_message(data);
    this->process_message(data + MESSAGE_LENGTH);
  } else {
    ESP_LOGW(TAG, "Unexpected message length: %d", length);
  }
}

void HikeITBLEComponent::process_message(const uint8_t* data) {
  ParsedMessage msg;
  if (!this->parse_message(data, MESSAGE_LENGTH, msg)) {
    ESP_LOGW(TAG, "Failed to parse message");
    return;
  }

  ESP_LOGI(TAG, "Parsed message - Type: 0x%02X, Count: %d, ID: %08X", msg.type,
           msg.count, msg.device_id);

  // Extract device ID from first response
  if (this->device_id_ == 0 && msg.device_id != 0) {
    this->device_id_ = msg.device_id;
    ESP_LOGI(TAG, "Device ID captured: %08X", this->device_id_);
  }

  // Handle verification response (Type 09)
  if (msg.type == 0x09) {
    if (msg.content[0] != 0) {
      ESP_LOGI(TAG, "Device VERIFIED!");
      this->set_state(STATE_VERIFIED);
      this->verified_callbacks_.call();
    } else {
      ESP_LOGW(TAG, "Verification FAILED!");
      this->set_state(STATE_ERROR);
    }
  }

  // Cache state from Type 02 messages
  if (msg.type == 0x02) {
    this->last_message_ = msg;
    this->has_cached_state_ = true;

    // Update entities with received state
    if (this->speed_select_ != nullptr) {
      this->speed_select_->publish_state(
          speed_model_to_string(msg.speed_model));
    }

    if (this->locked_switch_ != nullptr) {
      this->locked_switch_->publish_state(msg.is_safe_model);
    }

    // Log detailed info
    ESP_LOGI(TAG, "  Speed Model: %s", speed_model_to_string(msg.speed_model));
    ESP_LOGI(TAG, "  Steps: Eco=%d, Cruise=%d, Sport=%d, Hike=%d",
             msg.step_economy, msg.step_cruise, msg.step_sport, msg.step_hike);
    ESP_LOGI(TAG, "  Deep: CX=%d, SC=%d", msg.deep_cx, msg.deep_sc);
    ESP_LOGI(TAG, "  Version: %.1f, Locked: %s, AT: %d", msg.version,
             msg.is_safe_model ? "YES" : "NO", msg.at_flag);
  }

  // Trigger message callback
  std::string hex_msg = format_hex(data, MESSAGE_LENGTH);
  this->message_callbacks_.call(hex_msg);
}

bool HikeITBLEComponent::parse_message(const uint8_t* data, size_t len,
                                       ParsedMessage& msg) {
  if (len != MESSAGE_LENGTH) {
    return false;
  }

  // Check header
  if (data[0] != HEADER_BYTE_1 || data[1] != HEADER_BYTE_2) {
    return false;
  }

  // Extract fields
  msg.count = data[2];
  msg.type = data[3];
  memcpy(msg.content, &data[4], 10);
  msg.device_id = ((uint32_t)data[14] << 24) | ((uint32_t)data[15] << 16) |
                  ((uint32_t)data[16] << 8) | data[17];
  msg.checksum = data[18];

  // Verify checksum
  uint8_t calc_checksum = this->calculate_checksum(&data[2], 16);
  if (calc_checksum != msg.checksum) {
    ESP_LOGW(TAG, "Checksum mismatch: expected %02X, got %02X", calc_checksum,
             msg.checksum);
    return false;
  }

  // Parse Type 02 specific data
  if (msg.type == 0x02) {
    this->parse_type02(data, msg);
  }

  return true;
}

void HikeITBLEComponent::parse_type02(const uint8_t* data, ParsedMessage& msg) {
  uint8_t b1 = data[5];  // content[1]
  uint8_t b2 = data[6];  // content[2]
  uint8_t b3 = data[7];  // content[3]

  uint8_t b3_val = b3 & 0xFF;
  msg.at_flag = b3_val >> 7;
  msg.support_sl = ((b3_val >> 4) & 1) == 1;

  // Determine speed model
  if ((b3 & 0x07) == 0) {
    uint8_t model_byte = data[4];  // content[0]

    if (model_byte == 0) {
      msg.speed_model = SPEED_ECONOMY;
      msg.step_economy = b1 & 0x0F;
    } else if (model_byte == 1) {
      msg.speed_model = SPEED_NORMAL;
    } else if (model_byte == 2) {
      msg.speed_model = SPEED_CRUISE;
      msg.step_cruise = ((b1 & 0xFF) >> 4) & 0x0F;
    } else if (model_byte == 3) {
      msg.speed_model = SPEED_SPORT;
      msg.step_sport = b2 & 0x0F;
    } else if (model_byte == 4) {
      msg.speed_model = SPEED_HIKE_IT;
      msg.step_hike = ((b2 & 0xFF) >> 4) & 0x0F;
    } else if (model_byte == 5) {
      msg.speed_model = SPEED_AUTO;
    }
  } else if ((b3 & 0x01) == 1) {
    msg.speed_model = SPEED_LAUNCH;
  } else if (((b3_val >> 1) & 1) == 1) {
    msg.speed_model = SPEED_ANTI_SLIP;
  } else if (((b3_val >> 2) & 1) == 1) {
    msg.speed_model = SPEED_VALET;
  } else if (((b3_val >> 3) & 1) == 1) {
    msg.speed_model = SPEED_SL;
  }

  // Parse additional data
  msg.deep_cx = data[8] & 0xFF;
  msg.deep_sc = data[9] & 0xFF;

  uint8_t b10 = data[10];
  uint8_t study_high = b10 >> 4;
  if (study_high == 1) {
    msg.study_state = 1;
    msg.study_time = b10 & 0x0F;
  } else if (study_high > 1) {
    msg.study_state = (b10 & 0x0F) == 0 ? 0 : 3;
  }

  msg.version = data[11] / 10.0f;
  msg.is_safe_model = data[12] == 0;

  uint8_t b13 = data[13];
  if (((b13 >> 2) & 1) == 1) {
    msg.notice = "C1";
  } else if (((b13 >> 3) & 1) == 1) {
    msg.notice = "C2";
  } else if (((b13 >> 4) & 1) == 1) {
    msg.notice = "C3";
  }
}

void HikeITBLEComponent::set_connect_switch(switch_::Switch* sw) {
  this->connect_switch_ = sw;
}

bool HikeITBLEComponent::connection_allowed_() const {
  // If no switch configured, always allow connection
  if (this->connect_switch_ == nullptr) return true;
  return this->connect_switch_->state;
}

}  // namespace hikeit_ble
}  // namespace esphome