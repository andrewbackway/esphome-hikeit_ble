#pragma once
#include "esphome/components/button/button.h"
#include "hikeit_ble.h"

namespace esphome {
namespace hikeit_ble {

class HikeITButton : public button::Button, public Component {
 public:
  void set_parent(HikeITBLEComponent *parent) { this->parent_ = parent; }
  void set_command_type(uint8_t type) { this->command_type_ = type; }
  
 protected:
  void press_action() override {
    if (this->parent_ != nullptr) {
      if (this->command_type_ == 0) {
        // Screen command
        this->parent_->send_screen_command();
      } else if (this->command_type_ == 1) {
        // Auto command - toggle AT flag
        bool current_at = this->parent_->get_last_message().at_flag != 0;
        this->parent_->send_auto_command(!current_at);
      }
    }
  }
  
  HikeITBLEComponent *parent_{nullptr};
  uint8_t command_type_{0};
};

}  // namespace hikeit_ble
}  // namespace esphome