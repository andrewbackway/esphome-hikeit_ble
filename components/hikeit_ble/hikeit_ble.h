#pragma once

#include "esphome/core/component.h"
#include "esphome/core/log.h"
#include "esphome/core/automation.h"
#include "esphome/components/ble_client/ble_client.h"
#include <vector>
#include <string>

#include "esphome/components/switch/switch.h"

namespace esphome {
namespace hikeit_ble {

static const char *const TAG = "hikeit_ble";

// BLE Service and Characteristic UUIDs
static const char *SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb";
static const char *NOTIFY_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb";

// Protocol constants
static const uint8_t HEADER_BYTE_1 = 0xAA;
static const uint8_t HEADER_BYTE_2 = 0x55;
static const uint8_t MESSAGE_LENGTH = 19;

// Forward declarations for Entity classes (defined elsewhere, e.g., in their own component files or core)
// NOTE: These are only needed because they are used as pointers in HikeITBLEComponent below.
class HikeITSpeedSelect;
class HikeITStepNumber;
class HikeITLockedSwitch;
class HikeITButton;
class HikeITStatusSensor;

// Speed model enumeration
enum SpeedModel : uint8_t {
  SPEED_ECONOMY = 0,
  SPEED_NORMAL = 1,
  SPEED_CRUISE = 2,
  SPEED_SPORT = 3,
  SPEED_HIKE_IT = 4,
  SPEED_AUTO = 5,
  SPEED_LAUNCH = 6,
  SPEED_ANTI_SLIP = 7,
  SPEED_VALET = 8,
  SPEED_SL = 9
};

SpeedModel string_to_speed_model(const std::string &value);

// Parsed message structure
struct ParsedMessage {
  uint8_t count;
  uint8_t type;
  uint8_t content[10];
  uint32_t device_id;
  uint8_t checksum;
  
  // Type 02 specific data
  SpeedModel speed_model;
  uint8_t step_economy;
  uint8_t step_cruise;
  uint8_t step_sport;
  uint8_t step_hike;
  uint8_t deep_cx;
  uint8_t deep_sc;
  float version;
  bool is_safe_model;
  std::string notice;
  uint8_t study_state;
  uint8_t study_time;
  uint8_t at_flag;
  bool support_sl;
  
  ParsedMessage() : count(0), type(0), device_id(0), checksum(0),
                    speed_model(SPEED_ECONOMY), step_economy(0), step_cruise(0),
                    step_sport(0), step_hike(0), deep_cx(0), deep_sc(0),
                    version(0.0f), is_safe_model(false), study_state(0),
                    study_time(0), at_flag(0), support_sl(true) {
    memset(content, 0, sizeof(content));
  }
};

// Connection states
enum ConnectionState {
  STATE_DISCONNECTED,
  STATE_CONNECTING,
  STATE_CONNECTED,
  STATE_VERIFYING,
  STATE_VERIFIED,
  STATE_ERROR
};


// ------------------------------------------------------------------
// Main component class - DEFINED FIRST
// ------------------------------------------------------------------
class HikeITBLEComponent : public Component, public ble_client::BLEClientNode {
 public:
  HikeITBLEComponent() = default;
  
  // Component lifecycle
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }
  
  // BLE callbacks
  void gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if,
                          esp_ble_gattc_cb_param_t *param) override;
  
  // Configuration
  void set_address(uint64_t address);
  void set_address(const uint8_t *address);
  void set_pin(const std::string &pin) { this->pin_ = pin; }
  
  // Entity setters (using forward declared types)
  void set_speed_select(HikeITSpeedSelect *select) { this->speed_select_ = select; }
  void set_step_number(HikeITStepNumber *number) { this->step_number_ = number; }
  void set_locked_switch(HikeITLockedSwitch *sw) { this->locked_switch_ = sw; }
  void set_screen_button(HikeITButton *btn) { this->screen_button_ = btn; }
  void set_auto_button(HikeITButton *btn) { this->auto_button_ = btn; }
  void set_status_sensor(HikeITStatusSensor *sensor) { this->status_sensor_ = sensor; }
  
  void set_connect_switch(switch_::Switch *sw) { this->connect_switch_ = sw; }

  // Command methods
  void send_verify_command();
  void send_disconnect_command();
  void send_screen_command();
  void send_speed_model_command(SpeedModel model, uint8_t at_flag);
  void send_step_command(uint8_t step, SpeedModel model);
  void send_auto_command(bool enable);
  void send_safe_mode_command(const std::string &password, bool enable);
  
  // State getters
  ConnectionState get_state() const { return this->state_; }
  bool is_connected() const { return this->state_ >= STATE_CONNECTED; }
  bool is_verified() const { return this->state_ == STATE_VERIFIED; }
  const ParsedMessage& get_last_message() const { return this->last_message_; }
  const std::string& get_pin() const { return this->pin_; }
  
  // Automation callbacks (These are now fully visible)
  void add_on_connected_callback(std::function<void()> &&callback) {
    this->connected_callbacks_.add(std::move(callback));
  }
  void add_on_disconnected_callback(std::function<void()> &&callback) {
    this->disconnected_callbacks_.add(std::move(callback));
  }
  void add_on_verified_callback(std::function<void()> &&callback) {
    this->verified_callbacks_.add(std::move(callback));
  }
  void add_on_message_callback(std::function<void(const std::string &)> &&callback) {
    this->message_callbacks_.add(std::move(callback));
  }
  
 protected:
  // Protocol implementation
  uint8_t get_sequence();
  uint8_t calculate_checksum(const uint8_t *data, size_t len);
  std::vector<uint8_t> build_message(uint8_t type, const uint8_t *content);
  bool parse_message(const uint8_t *data, size_t len, ParsedMessage &msg);
  void parse_type02(const uint8_t *data, ParsedMessage &msg);
  
  // BLE operations
  void start_notify();
  void send_command(const std::vector<uint8_t> &data);
  void handle_notification(const uint8_t *data, uint16_t length);
  void process_message(const uint8_t *data);
  
  // Connection management
  void attempt_connection();
  void handle_connection();
  void handle_disconnection();
  void set_state(ConnectionState state);
  void update_status_text();
  
  // Configuration
  uint64_t address_{0};
  std::string pin_{"123"};
  
  // State
  ConnectionState state_{STATE_DISCONNECTED};
  uint8_t sequence_counter_{0};
  uint32_t device_id_{0};
  ParsedMessage last_message_;
  bool has_cached_state_{false};
  uint32_t last_connection_attempt_{0};
  uint32_t reconnect_delay_{5000};
  
  // BLE handles
  uint16_t service_handle_{0};
  uint16_t char_handle_{0};
  uint16_t notify_handle_{0};
  uint16_t notify_descr_handle_{0};
  
  // Message buffer for handling split messages
  std::vector<uint8_t> message_buffer_;
  
  // Entities
  HikeITSpeedSelect *speed_select_{nullptr};
  HikeITStepNumber *step_number_{nullptr};
  HikeITLockedSwitch *locked_switch_{nullptr};
  HikeITButton *screen_button_{nullptr};
  HikeITButton *auto_button_{nullptr};
  HikeITStatusSensor *status_sensor_{nullptr};

  switch_::Switch *connect_switch_{nullptr};
  bool connection_allowed_() const;
  
  // Automation callbacks
  CallbackManager<void()> connected_callbacks_;
  CallbackManager<void()> disconnected_callbacks_;
  CallbackManager<void()> verified_callbacks_;
  CallbackManager<void(const std::string &)> message_callbacks_;
};

// ------------------------------------------------------------------
// Automation triggers - DEFINED SECOND
// ------------------------------------------------------------------

class ConnectedTrigger : public Trigger<> {
 public:
  // HikeITBLEComponent is now fully defined, resolving the error
  explicit ConnectedTrigger(HikeITBLEComponent *parent) { parent->add_on_connected_callback([this]() { this->trigger(); }); }
};

class DisconnectedTrigger : public Trigger<> {
 public:
  explicit DisconnectedTrigger(HikeITBLEComponent *parent) { parent->add_on_disconnected_callback([this]() { this->trigger(); }); }
};

class VerifiedTrigger : public Trigger<> {
 public:
  explicit VerifiedTrigger(HikeITBLEComponent *parent) { parent->add_on_verified_callback([this]() { this->trigger(); }); }
};

class MessageReceivedTrigger : public Trigger<std::string> {
 public:
  explicit MessageReceivedTrigger(HikeITBLEComponent *parent) {
    parent->add_on_message_callback([this](const std::string &msg) { this->trigger(msg); });
  }
};


}  // namespace hikeit_ble
}  // namespace esphome