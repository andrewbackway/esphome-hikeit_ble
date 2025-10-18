#pragma once
#include "esphome/components/switch/switch.h"
#include "../hikeit_ble.h"

namespace esphome {
namespace hikeit_ble {

class HikeITLockedSwitch : public switch_::Switch, public Component {
 public:
  void set_parent(HikeITBLEComponent *parent) { this->parent_ = parent; }
  
 protected:
  void write_state(bool state) override {
    if (this->parent_ != nullptr) {
      // Get PIN from parent component
      this->parent_->send_safe_mode_command(this->parent_->get_pin(), state);
      this->publish_state(state);
    }
  }
  
  HikeITBLEComponent *parent_{nullptr};
};

}  // namespace hikeit_ble
}  // namespace esphome