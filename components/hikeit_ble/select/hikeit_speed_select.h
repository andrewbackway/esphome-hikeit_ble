#pragma once
#include "esphome/components/select/select.h"
#include "hikeit_ble.h"

namespace esphome {
namespace hikeit_ble {

class HikeITSpeedSelect : public select::Select, public Component {
 public:
  void set_parent(HikeITBLEComponent *parent) { this->parent_ = parent; }
  
 protected:
  void control(const std::string &value) override {
    if (this->parent_ != nullptr) {
      SpeedModel model = string_to_speed_model(value);
      uint8_t at_flag = this->parent_->get_last_message().at_flag;
      this->parent_->send_speed_model_command(model, at_flag);
    }
  }
  
  HikeITBLEComponent *parent_{nullptr};
};

}  // namespace hikeit_ble
}  // namespace esphome